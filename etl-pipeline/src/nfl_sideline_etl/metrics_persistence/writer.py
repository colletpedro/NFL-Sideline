"""One immutable SQL transaction after verified local archive publication."""
from collections import Counter
from copy import deepcopy
from decimal import Decimal

from ..offline_metrics.artifact import identity
from .archive import Archive
from .connection import connect
from .plan import validate_plan

TABLES = ('metric_archive_blob', 'metric_source_revision', 'metric_source_set',
          'metric_source_member', 'metric_calculation', 'game_metric_coverage_revision',
          'metric_calculation_coverage', 'team_game_metric_sums', 'metric_artifact',
          'metric_artifact_file', 'metric_archive_receipt')


def immutable_insert(cursor, table, key, record, counts):
    """Conflicts never overwrite. Compare every caller-controlled immutable field."""
    from psycopg2 import sql
    from psycopg2.extras import Json
    if table not in TABLES:
        raise ValueError('Unknown metrics relation')
    columns = list(record)
    values = [Json(v) if isinstance(v, (dict, list)) else v for v in record.values()]
    relation = sql.Identifier('metrics_private', table)
    cursor.execute(sql.SQL('insert into {} ({}) values ({}) on conflict ({}) do nothing returning 1').format(
        relation, sql.SQL(',').join(map(sql.Identifier, columns)),
        sql.SQL(',').join(sql.Placeholder() for _ in columns),
        sql.SQL(',').join(map(sql.Identifier, key))), values)
    inserted = cursor.fetchone() is not None
    if not inserted:
        # SQL IS NOT DISTINCT FROM preserves numeric/JSON semantic comparison;
        # persisted_at defaults are intentionally not part of immutable content.
        predicates = sql.SQL(' and ').join(sql.SQL('{} is not distinct from %s').format(sql.Identifier(k)) for k in columns)
        cursor.execute(sql.SQL('select 1 from {} where {}').format(relation, predicates), values)
        if cursor.fetchone() is None:
            raise ValueError(f'Immutable identity conflict in {table}')
    counts['inserted' if inserted else 'reused'] += 1


def persist(plan, archive_root, config, *, _checkpoint=None):
    """Private failure-injection hook supports real rollback tests, never CLI flags."""
    plan = deepcopy(plan)  # freeze nested caller state for this attempt
    validate_plan(plan, archive_root)
    conn = connect(config)
    try:
        archive = Archive(archive_root)
        all_bytes = {sha: data for sha, (data, _) in plan.source_bytes.items()}
        receipts = {}
        for sha, (data, origin) in sorted(plan.source_bytes.items()):
            receipts[sha] = archive.put(data, sha, {'type': 'explicit_source', **origin})
        for name, data in sorted(plan.artifact_bytes.items()):
            sha = plan.file_hashes[name]
            all_bytes[sha] = data
            receipts[sha] = archive.put(data, sha, {'type': 'artifact_file', 'filename': name,
                                                   'artifact_id': plan.artifact_id})
        if _checkpoint:
            _checkpoint('after_archive')
        counts = Counter(inserted=0, reused=0, conflicts=0)
        with conn:
            with conn.cursor() as cursor:
                # Small isolated persistence path, no throughput claims. This
                # serializes even different calculations sharing byte identities.
                cursor.execute('select pg_advisory_xact_lock(523052, 2)')
                def put(table, key, record):
                    immutable_insert(cursor, table, key, record, counts)
                for sha, data in sorted(all_bytes.items()):
                    archive.read(sha)
                    put('metric_archive_blob', ('sha256',), {'sha256': sha, 'byte_length': len(data)})
                for sha in sorted(plan.source_bytes):
                    put('metric_source_revision', ('revision_id',), {'revision_id': 'sha256:' + sha, 'sha256': sha})
                for kind, members in plan.sets.items():
                    set_id = identity([d['source_revision_id'] for d in members])
                    put('metric_source_set', ('revision_id', 'kind'),
                        {'revision_id': set_id, 'kind': kind, 'members_json': members})
                    for ordinal, descriptor in enumerate(members):
                        put('metric_source_member', ('set_id', 'kind', 'ordinal'),
                            {'set_id': set_id, 'kind': kind, 'ordinal': ordinal,
                             'source_id': descriptor['source_revision_id'], 'raw_rows': descriptor['raw_rows'],
                             'descriptor_json': descriptor})
                if _checkpoint:
                    _checkpoint('after_sources')
                result = plan.result
                manifest = result['manifest.json']
                calculation = manifest['calculation_id']
                versions = manifest['versions']
                put('metric_calculation', ('calculation_id',),
                    {'calculation_id': calculation, 'artifact_version': manifest['artifactVersion'],
                     'adapter_version': versions['adapter'], 'definition_version': versions['definition'],
                     'population_version': versions['population'],
                     'calendar_set_id': identity([d['source_revision_id'] for d in plan.sets['calendar']]),
                     'pbp_set_id': identity([d['source_revision_id'] for d in plan.sets['pbp']]),
                     'manifest_json': manifest})
                fields = ('coverage_revision_id', 'game_id', 'season', 'week', 'phase', 'round',
                          'home_team', 'away_team', 'calendar_revision_id', 'pbp_revision_id',
                          'pbp_content_id', 'completeness', 'declared_completeness', 'scope',
                          'statistics_status', 'raw_n', 'unique_n', 'duplicate_rows_ignored',
                          'excluded_n', 'eligible_content_n', 'expected_unique_rows',
                          'calendar_duplicate_rows_ignored', 'outside_pass_run_null_teams_n', 'unknown_filter_flags_n')
                for audit in result['game-audit.json']:
                    put('game_metric_coverage_revision', ('coverage_revision_id',),
                        {**{k: audit[k] for k in fields}, 'audit_json': audit})
                    put('metric_calculation_coverage', ('calculation_id', 'game_id'),
                        {'calculation_id': calculation, 'game_id': audit['game_id'],
                         'coverage_revision_id': audit['coverage_revision_id']})
                key = ('coverage_revision_id', 'team', 'role', 'foundation', 'population_version', 'definition_version')
                fields = (*key, 'scope', 'statistics_status', 'completeness', 'eligible_n', 'epa_n',
                          'success_n', 'epa_missing_n', 'epa_nonfinite_n')
                for stat in result['statistics.json']:
                    put('team_game_metric_sums', key,
                        {**{k: stat[k] for k in fields},
                         'epa_sum': None if stat['epa_sum'] is None else Decimal(stat['epa_sum']),
                         'record_json': stat})
                put('metric_artifact', ('artifact_id',), {'artifact_id': plan.artifact_id,
                    'calculation_id': calculation, 'files_json': plan.file_hashes})
                for name, sha in sorted(plan.file_hashes.items()):
                    put('metric_artifact_file', ('artifact_id', 'filename'),
                        {'artifact_id': plan.artifact_id, 'filename': name, 'sha256': sha})
                for sha, receipt in sorted(receipts.items()):
                    archive.validate_receipt(receipt, sha)
                    put('metric_archive_receipt', ('archive_id', 'sha256'),
                        {**{k: receipt[k] for k in ('receipt_id', 'sha256', 'archive_id', 'archive_root',
                                                   'locator', 'observed_at')}, 'receipt_json': receipt})
                if _checkpoint:
                    _checkpoint('before_commit')
        return dict(counts)
    finally:
        conn.close()
