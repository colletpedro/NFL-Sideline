"""Opt-in local orchestration; accepted adapter/writer remain the trust boundary."""
from __future__ import annotations

import os
from pathlib import Path
import uuid

from .ingestion_runs import sanitize_error_message
from .metrics_persistence import connection, writer
from .metrics_persistence.archive import digest, publish, safe_root
from .metrics_persistence.plan import prepare
from .offline_metrics.artifact import VERSIONS, calculate, ensure_destination, json_bytes, write_artifact
from .offline_metrics.inputs import load_json, read_inputs
from .seasons import normalize_seasons

REPORT_VERSION = 'metrics-pipeline-attempt-v1'


def add_arguments(parser):
    parser.add_argument('--game-metrics', choices=('off', 'plan', 'local'), default='off')
    for name in ('metrics-inputs', 'metrics-output', 'legacy-local-config',
                 'metrics-local-config', 'metrics-archive'):
        parser.add_argument('--' + name, type=Path)


def _regular(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Source must be a regular non-symlink file')
    return path.read_bytes()


def _spec(path, seasons):
    value = load_json(_regular(path))
    if (not isinstance(value, dict) or set(value) != {'inputsVersion', 'seasons'} or
            type(value['inputsVersion']) is not int or value['inputsVersion'] != 1 or
            not isinstance(value['seasons'], dict) or
            set(value['seasons']) != {str(s) for s in seasons}):
        raise ValueError('inputsVersion 1 requires the exact selected seasons')
    result = {}
    for season in seasons:
        entry = value['seasons'][str(season)]
        if not isinstance(entry, dict) or set(entry) != {'calendar', 'pbp', 'metadata'}:
            raise ValueError('Each season requires calendar, pbp and metadata')
        for kind in ('calendar', 'pbp'):
            paths = entry[kind]
            if (not isinstance(paths, list) or (kind == 'calendar' and not paths) or
                    not all(isinstance(p, str) and Path(p).is_absolute() for p in paths)):
                raise ValueError('Explicit absolute source paths required')
        if entry['metadata'] is not None and (
                not isinstance(entry['metadata'], str) or not Path(entry['metadata']).is_absolute()):
            raise ValueError('Explicit absolute metadata path required')
        result[season] = {k: [Path(p) for p in entry[k]] for k in ('calendar', 'pbp')}
        result[season]['metadata'] = Path(entry['metadata']) if entry['metadata'] else None
    return result


def _identity_check(conn, config):
    """Check actual endpoint, marker and inherited administrative capabilities."""
    with conn.cursor() as cur:
        cur.execute('select current_database(), host(inet_server_addr()), inet_server_port()')
        endpoint = cur.fetchone()
        if endpoint != (config['database'], config['host'], config['port']):
            raise ValueError('Actual local endpoint mismatch')
        cur.execute('select instance_id::text, purpose from e5b2_instance.identity')
        if cur.fetchall() != [(config['instance_id'], 'metrics-persistence-e5b2-disposable')]:
            raise ValueError('Instance marker mismatch')
        cur.execute("select exists(select 1 from pg_roles where "
                    "(rolsuper or rolbypassrls or rolcreatedb or rolcreaterole or rolreplication "
                    "or rolname in ('pg_read_server_files','pg_write_server_files','pg_execute_server_program','pg_signal_backend')) "
                    "and pg_has_role(current_user, oid, 'MEMBER'))")
        if cur.fetchone()[0]:
            raise ValueError('Privileged local login refused')
    conn.rollback()
    return (*endpoint, config['instance_id'])


def connect_legacy(config):
    if (not isinstance(config, dict) or
            set(config) != {'host', 'port', 'database', 'user', 'password', 'instance_id'} or
            config['host'] not in ('127.0.0.1', '::1') or
            type(config['port']) is not int or not 1 <= config['port'] <= 65535 or
            not all(isinstance(config[k], str) and config[k] for k in ('user', 'password'))):
        raise ValueError('Explicit literal loopback configuration required')
    instance = str(uuid.UUID(config['instance_id']))
    if config['database'] != 'nfl_e5b2_' + instance.replace('-', '')[:12]:
        raise ValueError('Unidentified local database')
    if any(k.startswith('PG') for k in os.environ):
        raise ValueError('Ambient PG* configuration forbidden')
    import psycopg2
    conn = psycopg2.connect(host=config['host'], hostaddr=config['host'], port=config['port'],
                           dbname=config['database'], user=config['user'], password=config['password'],
                           connect_timeout=5, sslmode='disable', gssencmode='disable', passfile='/dev/null',
                           options='-c search_path=public,pg_catalog -c timezone=UTC',
                           application_name='metrics-pipeline-e5b5-legacy')
    try:
        _identity_check(conn, config)
        with conn.cursor() as cur:
            cur.execute("select pg_has_role(current_user, 'metric_persistence_writer', 'MEMBER')")
            if cur.fetchone()[0]:
                raise ValueError('Separate domain and writer logins required')
            for table in ('teams', 'games', 'market_implied', 'team_week_metrics', 'ingestion_runs'):
                for privilege in ('SELECT', 'INSERT', 'UPDATE'):
                    cur.execute('select has_table_privilege(current_user, %s, %s)',
                                ('public.' + table, privilege))
                    if not cur.fetchone()[0]:
                        raise ValueError('Domain login lacks required privilege: ' + table + '/' + privilege)
            cur.execute("select pg_get_serial_sequence('public.ingestion_runs','id')")
            sequence = cur.fetchone()[0]
            cur.execute('select has_sequence_privilege(current_user, %s, %s)', (sequence, 'USAGE'))
            if not cur.fetchone()[0]:
                raise ValueError('Domain login lacks ingestion run sequence privilege')
        conn.rollback()
        return conn
    except BaseException:
        conn.close()
        raise


class Execution:
    def __init__(self, mode, entries, output, allow_missing, *, legacy=None, private=None, archive=None):
        self.mode, self.entries, self.output = mode, entries, Path(output)
        self.allow_missing = allow_missing
        self.legacy, self.private, self.archive = legacy, private, archive
        self.output.mkdir(parents=True, exist_ok=False)

    def attempt(self, season):
        return Attempt(self, season)

    def connection(self):
        return connect_legacy(self.legacy)


def configure(args, seasons):
    """No writes until combinations, inventory and both local identities pass."""
    seasons = normalize_seasons(seasons)
    fields = ('metrics_inputs', 'metrics_output', 'legacy_local_config',
              'metrics_local_config', 'metrics_archive')
    if args.game_metrics == 'off':
        if any(getattr(args, f) is not None for f in fields):
            raise ValueError('Metrics arguments require plan or local mode')
        return None
    if args.metrics_inputs is None or args.metrics_output is None:
        raise ValueError('Metrics inputs and new output required')
    if args.game_metrics == 'plan':
        if args.skip_acquire or args.data_dir is not None or any(
                getattr(args, f) is not None for f in fields[2:]):
            raise ValueError('Plan is offline only; legacy/SQL/archive arguments forbidden')
    elif not args.skip_acquire or args.data_dir is None or any(
            getattr(args, f) is None for f in fields[2:]):
        raise ValueError('Local mode requires skip-acquire, data-dir and both configurations/archive')
    entries = _spec(args.metrics_inputs, seasons)
    output = ensure_destination(args.metrics_output).resolve()
    archive = safe_root(args.metrics_archive) if args.metrics_archive else None
    sources = [args.metrics_inputs, *(p for e in entries.values() for k in ('calendar', 'pbp') for p in e[k]),
               *(e['metadata'] for e in entries.values() if e['metadata'])]
    for p in sources:
        p = p.resolve()
        if p == output or p.is_relative_to(output) or (archive and p.is_relative_to(archive)):
            raise ValueError('Operational destinations must not contain source inputs')
    if archive and (archive == output or archive.is_relative_to(output) or output.is_relative_to(archive)):
        raise ValueError('Archive and attempt output must be disjoint')
    legacy = private = None
    if args.game_metrics == 'local':
        for season, e in entries.items():
            base = args.data_dir.resolve() / 'raw'
            calendar = base / 'schedules' / f'season={season}' / 'schedules.parquet'
            pbp_dir = base / 'pbp' / f'season={season}'
            if e['calendar'] != [calendar] or any(p.suffix != '.parquet' or p.parent != pbp_dir for p in e['pbp']):
                raise ValueError('Local sources must use explicit canonical season partitions')
            existing = set(pbp_dir.glob('*.parquet'))
            if existing != {p for p in e['pbp'] if p.exists()}:
                raise ValueError('Entire local PBP partition inventory must be explicitly listed')
            if existing and pbp_dir / 'pbp.parquet' not in existing:
                raise ValueError('Legacy canonical pbp.parquet required when partitions exist')
        legacy = connection.configuration(args.legacy_local_config)
        private = connection.configuration(args.metrics_local_config)
        keys = ('host', 'port', 'database', 'instance_id')
        if tuple(legacy[k] for k in keys) != tuple(private[k] for k in keys):
            raise ValueError('Connections must identify the same local instance')
        a = connect_legacy(legacy)
        try:
            b = connection.connect(private)
            try:
                if _identity_check(a, legacy) != _identity_check(b, private):
                    raise ValueError('Verified connection identities differ')
            finally:
                b.close()
        finally:
            a.close()
    return Execution(args.game_metrics, entries, output, args.allow_missing_pbp,
                     legacy=legacy, private=private, archive=archive)


class Attempt:
    def __init__(self, execution, season):
        self.execution, self.season = execution, season
        self.attempt_id = str(uuid.uuid4())
        self.root = execution.output / f'{season}-{self.attempt_id}'
        self.root.mkdir()
        self.data_dir = self.root / 'legacy-data'
        self.events = 0
        self.run_id = None
        self.last_stage = 'CREATED'
        self.stage_result = 'NOT_STARTED'
        self.global_status = 'NOT_STARTED'
        self.sources = []
        self.paths = {'calendar': [], 'pbp': []}
        self.metadata = None
        self.plan = None
        self.details = {"versions": VERSIONS}
        if execution.mode == "local":
            self.details["instance"] = {k: execution.private[k] for k in ("host", "port", "database", "instance_id")}
        self.missing = False
        self._checkpoint = None  # tests/harness only, never a CLI option

    def event(self, stage, **details):
        report = {'reportVersion': REPORT_VERSION, 'mode': self.execution.mode,
                  'attempt_id': self.attempt_id, 'season': self.season, 'ingestion_run': self.run_id,
                  'stage': stage, 'previous_stage': self.last_stage, 'stage_result': self.stage_result,
                  'global_status': self.global_status, 'sources': self.sources, **self.details, **details}
        target = self.root / f'{self.events:04d}-{stage}.json'
        data = json_bytes(report)
        if publish(target, data) != data:
            raise ValueError('Operational event conflict')
        self.events += 1
        self.last_stage = stage
        if self._checkpoint:
            self._checkpoint(stage)

    def freeze(self):
        try:
            entry = self.execution.entries[self.season]
            for kind in ('calendar', 'pbp', 'metadata'):
                paths = [entry[kind]] if kind == 'metadata' and entry[kind] else ([] if kind == 'metadata' else entry[kind])
                if kind == 'pbp' and not paths:
                    self.missing = True
                for ordinal, original in enumerate(paths):
                    if kind == 'pbp' and not original.exists() and not original.is_symlink():
                        self.missing = True
                        self.sources.append({'kind': kind, 'original': str(original), 'state': 'MISSING'})
                        continue
                    data = _regular(original)
                    frozen = self.root / 'sources' / f'{kind}-{ordinal}{original.suffix}'
                    frozen.parent.mkdir(exist_ok=True)
                    frozen.write_bytes(data)
                    record = {'kind': kind, 'original': str(original), 'frozen': str(frozen),
                              'sha256': digest(data), 'bytes': len(data), 'state': 'PRESENT'}
                    self.sources.append(record)
                    if kind == 'metadata':
                        load_json(data)  # corruption stays fatal even for an unavailable batch
                        self.metadata = frozen
                    else:
                        self.paths[kind].append(frozen)
                        if self.execution.mode == 'local':
                            source = 'schedules' if kind == 'calendar' else 'pbp'
                            legacy = self.data_dir / 'raw' / source / f'season={self.season}' / original.name
                            legacy.parent.mkdir(parents=True, exist_ok=True)
                            legacy.write_bytes(data)
                            record['legacy_frozen'] = str(legacy)
            if self.missing and not self.execution.allow_missing:
                raise ValueError('PBP source missing; explicit allow-missing-pbp required')
            # Validate every present source, even if another partition is absent.
            inputs = read_inputs(self.paths['calendar'], self.paths['pbp'])
            if self.missing:
                # Still reject conflicts/invalid populations in the present subset.
                from .offline_metrics.validation import calendar_index, reconcile_raw
                games, _ = calendar_index(inputs[0])
                reconcile_raw(inputs[1], games)
            self.details['descriptors'] = inputs[2]
            self.details['pbp_state'] = ('MISSING' if self.missing else 'EMPTY_PRESENT' if not inputs[1] else 'PRESENT')
            if not inputs[1] and not self.missing and not self.execution.allow_missing:
                raise ValueError('Empty PBP requires explicit allow-missing-pbp')
            self.event('FROZEN')
        except Exception as exc:
            self.failed('freeze', exc)
            raise

    def verify_sources(self):
        for record in self.sources:
            if record['state'] == 'MISSING':
                if Path(record['original']).exists() or Path(record['original']).is_symlink():
                    raise ValueError('Missing source changed during attempt')
                continue
            for key in ('original', 'frozen', 'legacy_frozen'):
                if key in record and digest(_regular(record[key])) != record['sha256']:
                    raise ValueError('Frozen/original source changed during attempt')

    def run(self):
        self.verify_sources()
        if self.missing:
            self.stage_result = 'UNAVAILABLE_MISSING_PBP'
            self.event('UNAVAILABLE')
            return
        self.event('CALCULATING')
        inputs = read_inputs(self.paths['calendar'], self.paths['pbp'])
        metadata = load_json(_regular(self.metadata)) if self.metadata else None
        result = calculate(*inputs, metadata, seasons=(self.season,))
        artifact = self.root / 'artifact'
        write_artifact(artifact, result)
        # prepare's dry path does not create an archive, including plan mode.
        archive = self.execution.archive or self.root / 'not-created-archive'
        self.plan = prepare(artifact, self.paths['calendar'], self.paths['pbp'], archive)
        self.details.update(self.plan.summary())
        self.details['versions'] = result['manifest.json']['versions']
        self.details['file_hashes'] = self.plan.file_hashes
        self.details['coverages'] = [{'game_id': a['game_id'], 'coverage_revision_id': a['coverage_revision_id'],
                                     'scope': a['scope'], 'completeness': a['completeness']}
                                    for a in result['game-audit.json']]
        self.details['reconciliation'] = result['reconciliation.json']
        self.event('VALIDATED')
        self.verify_sources()
        if self.execution.mode == 'plan':
            self.stage_result = 'PLANNED'
            self.event('PLANNED')
            return

        def checkpoint(stage):
            if stage == 'after_archive':
                marker = load_json((archive / 'ARCHIVE.json').read_bytes())
                self.details['archive_id'] = marker['archive_id']
                self.details['archive_root'] = str(archive)
                hashes = sorted(set(self.plan.source_bytes) | set(self.plan.file_hashes.values()))
                self.details['receipts'] = [load_json((archive / 'receipts' / (h + '.json')).read_bytes())['receipt_id'] for h in hashes]
                self.event('ARCHIVED')
                self.verify_sources()
            if self._checkpoint:
                self._checkpoint(stage)

        self.event('PERSISTING')
        counts = writer.persist(self.plan, archive, self.execution.private, _checkpoint=checkpoint)
        self.details['writer_counts'] = counts
        self.details['database_connected'] = True
        self.stage_result = 'PERSISTED'
        self.event('PRIVATE_COMMITTED')

    def failed(self, stage, exc, *, global_status=None):
        if self.stage_result != 'PERSISTED':
            self.stage_result = 'FAILED'
        if global_status is not None:
            self.global_status = global_status
        try:
            self.event('FAILED', diagnostic=sanitize_error_message(stage, exc),
                       recovery='New attempt/output; revalidate content and reuse valid CAS/receipts. '
                       'Prior SQL commits remain; commit outcome may require reconciliation.')
        except Exception:
            # Never replace the original failure with an audit I/O failure.
            import logging
            logging.getLogger(__name__).error('Secondary operational journal failure')


def plan(execution, seasons):
    for season in seasons:
        attempt = execution.attempt(season)
        attempt.freeze()
        try:
            attempt.run()
        except Exception as exc:
            attempt.failed('plan', exc)
            raise
