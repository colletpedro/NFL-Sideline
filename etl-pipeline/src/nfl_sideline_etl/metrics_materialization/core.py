"""Relations + closed bytes + explicit documents -> explicit temporal input v3.

No driver, environment, network, clock or database. Temp files only enable the
accepted E5b-2 semantic verifier; archive paths in receipts are never accessed.
"""
import base64
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import tempfile
import uuid

from ..offline_metrics.artifact import identity, json_bytes
from ..offline_metrics.statistics import COUNTS
from ..metrics_persistence.archive import Archive, digest
from ..metrics_persistence.plan import prepare
from ..temporal_metrics import INPUT_VERSION
from ..temporal_metrics.core import canonical
from ..temporal_metrics.times import instant
from ..temporal_metrics.validation import fields, validate
from . import AUXILIARY_VERSION, RELATIONS_VERSION, MATERIALIZATION_VERSION
from .relations import TABLES, records


class ContractGap(ValueError):
    """An accepted earlier contract cannot represent the preserved batch IDs."""


def sorted_rows(rows):
    return sorted(rows, key=json_bytes)


def selection(document):
    fields(document, ('relationsVersion', 'selection', 'relations'))
    if document['relationsVersion'] != RELATIONS_VERSION or set(document['relations']) != set(TABLES):
        raise ValueError('Unsupported/ incomplete relations package')
    rows = document['selection']
    if not isinstance(rows, list) or not rows:
        raise ValueError('Explicit nonempty selection required')
    for row in rows:
        fields(row, ('calculation_id', 'artifact_id', 'archive_id'))
        for key in ('calculation_id', 'artifact_id'):
            v = row[key]
            if not isinstance(v, str) or len(v) != 71 or not v.startswith('sha256:'):
                raise ValueError('Invalid selected identity')
            Archive.locator(v[7:])
        if str(uuid.UUID(row['archive_id'])) != row['archive_id']:
            raise ValueError('Canonical archive UUID required')
    if len({s['calculation_id'] for s in rows}) != len(rows):
        raise ValueError('Select exactly one artifact/archive per calculation')
    return sorted_rows(rows)


def materialize(package, recovered, auxiliary, derived_at):
    package, recovered, aux = deepcopy((package, recovered, auxiliary))
    choices = selection(package)
    instant(derived_at)
    fields(aux, ('auxiliaryVersion', 'policy', 'archiveOrigin', 'resources', 'evidence', 'bindings'), ('file_ingestion',))
    if aux['auxiliaryVersion'] != AUXILIARY_VERSION or not isinstance(aux['archiveOrigin'], str) or not aux['archiveOrigin']:
        raise ValueError('Invalid explicit auxiliary document package')
    relations = package['relations']
    expected = {t: [] for t in TABLES}
    plans = []
    needed_blobs = {s['archive_id']: set() for s in choices}
    # Verify every closed byte and observation before interpreting source data.
    blobs = {}
    for aid, archive in recovered.items():
        fields(archive, ('archive_id', 'archive_root', 'blobs', 'receipts'))
        if archive['archive_id'] != aid or aid not in needed_blobs:
            raise ValueError('Unselected archive identity')
        if set(archive['blobs']) != set(archive['receipts']):
            raise ValueError('Missing bytes/receipts in recovered archive')
        if not isinstance(archive['archive_root'], str) or not Path(archive['archive_root']).is_absolute():
            raise ValueError('Explicit absolute archive root required')
        for sha, encoded in archive['blobs'].items():
            data = base64.b64decode(encoded, validate=True)
            if digest(data) != sha:
                raise ValueError('Recovered byte hash mismatch')
            receipt = archive['receipts'][sha]
            fields(receipt, ('receiptVersion', 'receipt_id', 'archive_id', 'archive_root',
                             'sha256', 'locator', 'observed_at', 'origin'))
            if (receipt['receiptVersion'] != 1 or receipt['archive_id'] != aid or
                    receipt['archive_root'] != archive['archive_root'] or receipt['sha256'] != sha or
                    receipt['locator'] != Archive.locator(sha) or
                    receipt['receipt_id'] != identity({k: v for k, v in receipt.items() if k != 'receipt_id'})):
                raise ValueError('Recovered receipt identity/root/locator mismatch')
            instant(receipt['observed_at'])
            if not receipt['observed_at'].endswith(('Z', '+00:00', '-00:00')):
                raise ValueError('Receipt observation must be UTC as required by E5b-2')
            if sha in blobs and blobs[sha] != data:
                raise ValueError('Conflicting byte identity')
            blobs[sha] = data
    if set(recovered) != set(needed_blobs):
        raise ValueError('Missing explicit archive')
    for choice in choices:
        artifacts = [r for r in relations['metric_artifact'] if r['artifact_id'] == choice['artifact_id']]
        if len(artifacts) != 1 or artifacts[0]['calculation_id'] != choice['calculation_id']:
            raise ValueError('Explicit artifact/calculation binding mismatch')
        artifact = artifacts[0]
        aid = choice['archive_id']
        with tempfile.TemporaryDirectory(prefix='nfl-e5b4-verify-') as tmp:
            root = Path(tmp); art = root / 'artifact'; art.mkdir()
            for filename, sha in artifact['files_json'].items():
                if filename not in ('manifest.json', 'game-audit.json', 'statistics.json',
                                    'reconciliation.json', 'limitations.json', 'COMPLETED.json'):
                    raise ValueError('Unknown original artifact filename')
                (art / filename).write_bytes(blobs[sha]); needed_blobs[aid].add(sha)
            from ..offline_metrics.inputs import load_json
            manifest = load_json((art / 'manifest.json').read_bytes())
            paths = {'calendar': [], 'pbp': []}
            for i, d in enumerate(manifest['inputs']):
                if d['kind'] not in paths:
                    raise ValueError('Invalid source descriptor kind')
                suffix = '.json' if all(v == 'JSON scalar (validated per row)' for v in d['relevant_schema'].values()) else '.parquet'
                path = root / (str(i) + suffix); path.write_bytes(blobs[d['sha256']])
                paths[d['kind']].append(path); needed_blobs[aid].add(d['sha256'])
            plan = prepare(art, paths['calendar'], paths['pbp'], root / 'unused-archive')
        if plan.artifact_id != choice['artifact_id'] or plan.result['manifest.json']['calculation_id'] != choice['calculation_id']:
            raise ValueError('Original artifact identities mismatch')
        plans.append(plan)
        for table, rows in records(plan).items():
            for row in rows:
                if row not in expected[table]:
                    expected[table].append(row)
    for aid, hashes in needed_blobs.items():
        if set(recovered[aid]['blobs']) != hashes:
            raise ValueError('Archive selection has extra/missing bytes or source partitions')
        for sha in sorted(hashes):
            receipt = recovered[aid]['receipts'][sha]
            expected['metric_archive_receipt'].append({**{k: receipt[k] for k in
                ('receipt_id', 'sha256', 'archive_id', 'archive_root', 'locator', 'observed_at')}, 'receipt_json': receipt})
    timestamp_tables = {'metric_archive_blob', 'metric_calculation', 'metric_archive_receipt'}
    for table in TABLES:
        actual = []
        for original in relations[table]:
            row = deepcopy(original)
            if table in timestamp_tables:
                instant(row.pop('persisted_at'))
            if table == 'team_game_metric_sums' and row['epa_sum'] is not None:
                if not isinstance(row['epa_sum'], str) or not Decimal(row['epa_sum']).is_finite():
                    raise ValueError('SQL numeric must be a finite decimal string')
                # SQL numeric scale is not a distinct sufficient sum.
                row['epa_sum'] = str(Decimal(row['epa_sum']).normalize()) if Decimal(row['epa_sum']) == 0 else row['epa_sum']
                ref = row['record_json']['epa_sum']
                if ref is None or Decimal(row['epa_sum']) != Decimal(ref):
                    raise ValueError('SQL sum and record_json diverge')
                row['epa_sum'] = ref
            if table == 'metric_archive_receipt':
                if instant(row['observed_at']) != instant(row['receipt_json']['observed_at']):
                    raise ValueError('Receipt SQL time mismatch')
                row['observed_at'] = row['receipt_json']['observed_at']
            actual.append(row)
        if [json_bytes(r) for r in sorted_rows(actual)] != [json_bytes(r) for r in sorted_rows(expected[table])]:
            raise ValueError('Persisted relation diverges from accepted artifact: ' + table)
    resources = deepcopy(aux['resources']); evidence = deepcopy(aux['evidence'])
    if any(r['kind'] not in ('CALENDAR', 'STATE', 'METADATA') for r in resources):
        raise ValueError('Auxiliary resources cannot override recovered FILE/SET')
    metadata = {r['revision_id']: r for r in resources if r['kind'] == 'METADATA'}
    metadata_ids = set(metadata)
    for r in metadata.values():
        document = r['payload']['document']
        fields(document, ('documentVersion', 'origin', 'received_at', 'reference', 'content'))
        if document['documentVersion'] != 'metrics-auxiliary-document-v1' or document['origin'] != r['payload']['origin']:
            raise ValueError('Invalid auxiliary document identity/origin')
        instant(document['received_at'])
        if not isinstance(document['reference'], str) or not document['reference']:
            raise ValueError('Explicit auxiliary document reference required')
    for e in evidence:
        if not set(e['dependencies']) & metadata_ids:
            raise ValueError('Auxiliary evidence requires explicit received METADATA document dependency')
        for dep in set(e['dependencies']) & metadata_ids:
            if instant(e['recorded_at']) < instant(metadata[dep]['payload']['document']['received_at']):
                raise ValueError('Evidence cannot predate its received auxiliary document')
    bindings = {}
    for b in aux['bindings']:
        fields(b, ('calculation_id', 'calendars', 'metadata_revision_ids', 'completeness', 'model', 'source_models'))
        if b['calculation_id'] in bindings or b['calculation_id'] not in {s['calculation_id'] for s in choices}:
            raise ValueError('Duplicate/unselected calculation binding')
        bindings[b['calculation_id']] = b
    # A FILE observation is taken from the explicitly selected archive, never min(receipts).
    file_receipts = {}
    for plan, choice in zip(plans, choices):
        for sha in plan.source_bytes:
            receipt = recovered[choice['archive_id']]['receipts'][sha]
            if sha in file_receipts and file_receipts[sha] != receipt:
                raise ValueError('Conflicting archive observations for same FILE; split packages explicitly')
            file_receipts[sha] = receipt
    ingestion = aux.get('file_ingestion', {})
    if not isinstance(ingestion, dict) or set(ingestion) - {'sha256:' + sha for sha in file_receipts}:
        raise ValueError('File ingestion must bind explicitly selected source revisions')
    for sha, receipt in sorted(file_receipts.items()):
        rid = 'sha256:' + sha; eid = receipt['receipt_id']
        evidence.append({'evidence_id': eid, 'kind': 'ARCHIVE_OBSERVATION', 'subject_id': rid,
            'origin': aux['archiveOrigin'], 'reference': 'receipt:' + eid,
            'recorded_at': receipt['observed_at'], 'value': receipt['observed_at'],
            'dependencies': [], 'receipt': receipt})
        resources.append({'revision_id': rid, 'kind': 'FILE', 'dependencies': [],
            'available_at': {'value': receipt['observed_at'], 'evidence_id': eid}, 'ingested_at': ingestion.get(rid),
            'payload': {'source_revision_id': rid, 'sha256': sha,
                        'bytes_base64': base64.b64encode(blobs[sha]).decode('ascii'), 'origin': aux['archiveOrigin']}})
    for row in expected['metric_source_set']:
        resources.append({'revision_id': row['revision_id'], 'kind': 'SET',
            'dependencies': [d['source_revision_id'] for d in row['members_json']],
            'available_at': None, 'ingested_at': None,
            'payload': {'source_set_id': row['revision_id'], 'source_kind': row['kind']}})
    calculations, diagnostics = [], []
    game_fields = ('game_id', 'season', 'phase', 'round', 'week', 'home_team', 'away_team')
    for plan in plans:
        m = plan.result['manifest.json']; cid = m['calculation_id']; audits = plan.result['game-audit.json']
        binding = bindings.get(cid)
        if binding and set(binding['calendars']) != {str(a['season']) + '/' + a['phase'] for a in audits}:
            raise ValueError('Binding must name every frozen season/phase, without extra scopes')
        cal_by_scope = {}
        for scope in sorted({(a['season'], a['phase']) for a in audits}):
            games = [{k: a[k] for k in game_fields} for a in audits if (a['season'], a['phase']) == scope]
            sid = audits[0]['calendar_revision_id']
            if binding:
                calid = binding['calendars'].get(str(scope[0]) + '/' + scope[1])
                cal = next((r for r in resources if r['revision_id'] == calid), None)
                if (cal is None or cal['kind'] != 'CALENDAR' or cal['payload']['season'] != scope[0] or
                        cal['payload']['phase'] != scope[1] or sorted_rows(cal['payload']['games']) != sorted_rows(games) or sid not in cal['dependencies']):
                    raise ValueError('Auxiliary calendar and frozen full inventory diverge')
            else:
                payload = {'season': scope[0], 'phase': scope[1], 'games': games, 'complete': None, 'closed_weeks': []}
                calid = identity({'calendarDocument': payload, 'source_set_id': sid})
                resources.append({'revision_id': calid, 'kind': 'CALENDAR', 'dependencies': [sid],
                    'available_at': None, 'ingested_at': None, 'payload': payload})
                diagnostics.append({'reason': 'AUXILIARY_CALENDAR_UNKNOWN', 'revision_id': calid})
            cal_by_scope[scope] = calid
            for g in games:
                if not any(r['kind'] == 'STATE' and r['payload']['calendar_revision_id'] == calid and r['payload']['game_id'] == g['game_id'] for r in resources):
                    payload = {'game_id': g['game_id'], 'calendar_revision_id': calid, 'status': 'UNKNOWN',
                               'event_upper_bound': None, 'event_lower_bound': None, 'kickoff': None}
                    resources.append({'revision_id': identity(payload), 'kind': 'STATE', 'dependencies': [calid],
                        'available_at': None, 'ingested_at': None, 'payload': payload})
                    diagnostics.append({'reason': 'AUXILIARY_STATE_UNKNOWN', 'game_id': g['game_id']})
        if binding and set(binding['completeness']) - {a['coverage_revision_id'] for a in audits}:
            raise ValueError('Completeness binding outside selected coverage')
        for a in audits:
            cov = a['coverage_revision_id']
            rows = [{k: s[k] for k in ('team', 'role', 'foundation', *COUNTS, 'epa_sum')}
                    for s in plan.result['statistics.json'] if s['coverage_revision_id'] == cov]
            if not rows:
                diagnostics.append({'reason': 'NO_SOURCE_OBSERVATION', 'calculation_id': cid,
                                    'coverage_revision_id': cov, 'game_id': a['game_id']})
                continue
            complete = binding['completeness'].get(cov) if binding else None
            if complete and complete['value'] != a['completeness']:
                raise ValueError('Auxiliary completeness disagrees with persisted effective completeness')
            sm = binding['source_models'] if binding else {d['source_revision_id']: None for d in plan.sets['pbp']}
            for d in plan.sets['pbp']:
                declared = m['source_model_versions'][d['sha256']]['value']
                env = sm.get(d['source_revision_id'])
                if env and declared != 'UNKNOWN' and env['value'] != declared:
                    raise ValueError('Auxiliary model conflicts with persisted known source model')
            c = {'calculation_id': cid, 'coverage_revision_id': cov,
                'calendar_revision_id': cal_by_scope[a['season'], a['phase']], 'pbp_revision_id': a['pbp_revision_id'],
                'metadata_revision_ids': binding['metadata_revision_ids'] if binding else [],
                'game': {k: a[k] for k in game_fields}, 'versions': {k: m['versions'][k] for k in ('population', 'definition', 'adapter')},
                'completeness': complete, 'model': binding['model'] if binding else None,
                'source_models': sm, 'unknown_filter_flags_n': a['unknown_filter_flags_n'], 'statistics': rows,
                'original': {'manifest': deepcopy(m), 'coverage': deepcopy(a)}}
            c['revision_id'] = identity({'temporalAssociation': c})
            calculations.append(c)
    temporal = {'inputVersion': INPUT_VERSION, 'policy': aux['policy'], 'resources': resources,
                'evidence': evidence, 'calculations': calculations}
    validate(temporal)
    lineage = {'materializationVersion': MATERIALIZATION_VERSION, 'derivedAt': derived_at,
               'relations': package, 'recoveredArchives': recovered, 'auxiliary': aux,
               'diagnostics': sorted_rows(diagnostics), 'temporalInputId': identity(canonical(temporal)),
               'assumptions': ['Explicit trust policy, not external authentication',
                   'persisted_at is audit only; no inferred ingestion', 'Receipt is current local observation only']}
    lineage['materialization_id'] = identity(lineage)
    return temporal, lineage
