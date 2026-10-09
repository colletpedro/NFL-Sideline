"""Closed structural contract, identity conflicts and sufficient-stat invariants."""
import base64
from decimal import Decimal
import hashlib

from ..offline_metrics.artifact import identity
from ..offline_metrics.statistics import COUNTS, FOUNDATIONS, exact_sum
from . import INPUT_VERSION, POLICY_VERSION
from .times import instant, eastern_kickoff

KINDS = {'FILE', 'SET', 'CALENDAR', 'STATE', 'METADATA'}
EVIDENCE_KINDS = {'HASH_CHECK', 'ARCHIVE_OBSERVATION', 'SYSTEM_INGESTION',
                  'FINAL_OBSERVATION', 'EVENT_END_BOUND', 'CALENDAR_COMPLETE',
                  'PERIOD_CLOSED', 'PBP_COMPLETE', 'METADATA'}


def fields(obj, required, optional=()):
    if not isinstance(obj, dict) or not set(required) <= set(obj) or set(obj) - set(required) - set(optional):
        raise ValueError('Invalid fields: ' + ','.join(required))


def string(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Nonempty string required')
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('Nonnegative integer required')
    return value


def index(records, key):
    if not isinstance(records, list):
        raise ValueError('Record list required')
    result = {}
    for record in records:
        string(record[key])
        ident = record[key]
        if ident in result and result[ident] != record:
            raise ValueError('IDENTITY_CONFLICT: ' + ident)
        result[ident] = record
    return dict(sorted(result.items()))


def envelope(value, *, timestamp=False):
    if value is None:
        return
    fields(value, ('value', 'evidence_id'))
    string(value['evidence_id'])
    if timestamp:
        instant(value['value'])


def game(value):
    fields(value, ('game_id', 'season', 'phase', 'round', 'week', 'home_team', 'away_team'))
    for key in ('game_id', 'home_team', 'away_team'):
        string(value[key])
    integer(value['season'], 1999)
    integer(value['week'], 1)
    if value['phase'] not in ('REG', 'POST') or value['home_team'] == value['away_team']:
        raise ValueError('Invalid game phase/participants')
    if ((value['phase'] == 'REG' and value['round'] != 'REG') or
            (value['phase'] == 'POST' and value['round'] not in (None, 'WC', 'DIV', 'CON', 'SB'))):
        raise ValueError('Invalid explicit phase/round')


def stats(rows, frozen_game):
    by_key = {}
    for row in rows:
        fields(row, ('team', 'role', 'foundation', *COUNTS, 'epa_sum'))
        key = (row['team'], row['role'], row['foundation'])
        if key in by_key:
            raise ValueError('Duplicate statistics group')
        if row['team'] not in (frozen_game['home_team'], frozen_game['away_team']) or row['role'] not in ('off', 'def') or row['foundation'] not in FOUNDATIONS:
            raise ValueError('Invalid statistics group')
        for count in COUNTS:
            integer(row[count])
        if row['eligible_n'] != row['epa_n'] + row['epa_missing_n'] + row['epa_nonfinite_n'] or row['success_n'] > row['epa_n']:
            raise ValueError('Invalid sufficient-stat counts')
        if (row['epa_n'] == 0) != (row['epa_sum'] is None):
            raise ValueError('Invalid null sufficient sum')
        if row['epa_sum'] is not None:
            if not isinstance(row['epa_sum'], str) or not Decimal(row['epa_sum']).is_finite():
                raise ValueError('Finite decimal string required')
        by_key[key] = row
    if len(by_key) != 12:
        raise ValueError('Exactly 12 statistics groups required per observed game')
    for (team, role, foundation), row in by_key.items():
        opponent = frozen_game['away_team'] if team == frozen_game['home_team'] else frozen_game['home_team']
        other = by_key[opponent, 'def' if role == 'off' else 'off', foundation]
        if any(row[c] != other[c] for c in (*COUNTS, 'epa_sum')):
            raise ValueError('off != opponent def')
        if foundation == 'general':
            parts = [by_key[team, role, f] for f in FOUNDATIONS[1:]]
            if any(row[c] != sum(p[c] for p in parts) for c in COUNTS):
                raise ValueError('general != pass + rush')
            if row['epa_n'] and Decimal(row['epa_sum']) != exact_sum(Decimal(p['epa_sum']) for p in parts if p['epa_n']):
                raise ValueError('General EPA sum reconciliation failed')


def json_values(value):
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError('JSON keys must be strings')
        for child in value.values():
            json_values(child)
    elif isinstance(value, list):
        for child in value:
            json_values(child)
    elif value is not None and type(value) not in (str, int, bool):
        raise ValueError('Temporal JSON requires decimal strings instead of floating numbers')


def validate(document):
    json_values(document)
    fields(document, ('inputVersion', 'policy', 'resources', 'evidence', 'calculations'))
    if document['inputVersion'] != INPUT_VERSION:
        raise ValueError('Unsupported temporal input version')
    fields(document['policy'], ('policyVersion', 'trustedOrigins'))
    if document['policy']['policyVersion'] != POLICY_VERSION or not isinstance(document['policy']['trustedOrigins'], list):
        raise ValueError('Unsupported evidence policy')
    for origin in document['policy']['trustedOrigins']:
        string(origin)
    resources = index(document['resources'], 'revision_id')
    proofs = index(document['evidence'], 'evidence_id')
    calculations = index(document['calculations'], 'revision_id')
    for r in resources.values():
        fields(r, ('revision_id', 'kind', 'dependencies', 'available_at', 'ingested_at', 'payload'))
        if r['kind'] not in KINDS or not isinstance(r['dependencies'], list):
            raise ValueError('Invalid resource kind/dependencies')
        for dep in r['dependencies']:
            if dep not in resources:
                raise ValueError('Unresolved dependency')
        for key in ('available_at', 'ingested_at'):
            envelope(r[key], timestamp=True)
        p = r['payload']
        if r['kind'] == 'FILE':
            fields(p, ('source_revision_id', 'sha256', 'bytes_base64', 'origin'))
            string(p['origin'])
            raw = base64.b64decode(p['bytes_base64'], validate=True)
            if hashlib.sha256(raw).hexdigest() != p['sha256'] or p['source_revision_id'] != 'sha256:' + p['sha256']:
                raise ValueError('File byte integrity mismatch')
            if r['revision_id'] != p['source_revision_id'] or r['dependencies']:
                raise ValueError('FILE identity/dependencies mismatch')
        elif r['kind'] == 'SET':
            fields(p, ('source_set_id', 'source_kind'))
            if p['source_kind'] not in ('calendar', 'pbp') or r['revision_id'] != p['source_set_id'] or not r['dependencies']:
                raise ValueError('Invalid source set')
            if any(resources[d]['kind'] != 'FILE' for d in r['dependencies']):
                raise ValueError('SET must contain entire FILE members')
            if p['source_set_id'] != identity(sorted(r['dependencies'])):
                raise ValueError('Source set identity mismatch')
            if r['available_at'] is not None or r['ingested_at'] is not None:
                raise ValueError('SET derives temporal maxima from all members')
        elif r['kind'] == 'CALENDAR':
            fields(p, ('season', 'phase', 'games', 'complete', 'closed_weeks'))
            integer(p['season'], 1999)
            if p['phase'] not in ('REG', 'POST'):
                raise ValueError('Invalid calendar phase')
            games = index(p['games'], 'game_id')
            for g in games.values():
                game(g)
                if g['season'] != p['season'] or g['phase'] != p['phase']:
                    raise ValueError('Calendar mixes season/phase')
            if len(games) != len(p['games']):
                raise ValueError('Duplicate calendar event')
            envelope(p['complete'])
            if p['complete'] is not None and type(p['complete']['value']) is not bool:
                raise ValueError('Calendar complete must be boolean')
            for closed in p['closed_weeks']:
                fields(closed, ('week', 'evidence_id'))
                integer(closed['week'], 1)
            if len({c['week'] for c in p['closed_weeks']}) != len(p['closed_weeks']):
                raise ValueError('Duplicate closed week')
            if not any(resources[d]['kind'] == 'SET' and resources[d]['payload']['source_kind'] == 'calendar' for d in r['dependencies']):
                raise ValueError('Calendar must bind source set')
        elif r['kind'] == 'STATE':
            fields(p, ('game_id', 'calendar_revision_id', 'status', 'event_upper_bound', 'kickoff'), ('source_cause',))
            if 'source_cause' in p:
                envelope(p['source_cause'])
                if p['source_cause'] is not None and p['source_cause']['value'] not in ('SOURCE_UNKNOWN', 'PBP_ABSENT', 'SOURCE_DELAY', 'INGESTION_FAILED'):
                    raise ValueError('Invalid explicit source cause')
            if p['status'] not in ('FINAL', 'SCHEDULED', 'POSTPONED', 'UNKNOWN'):
                raise ValueError('Invalid game state')
            calendar = resources.get(p['calendar_revision_id'])
            if calendar is None or calendar['kind'] != 'CALENDAR' or p['calendar_revision_id'] not in r['dependencies']:
                raise ValueError('State must bind calendar dependency')
            if p['game_id'] not in {g['game_id'] for g in calendar['payload']['games']}:
                raise ValueError('State game outside calendar')
            envelope(p['event_upper_bound'], timestamp=True)
            k = p['kickoff']
            if k is not None:
                if 'value' in k:
                    envelope(k, timestamp=True)
                else:
                    fields(k, ('gameday', 'gametime', 'evidence_id'))
                    eastern_kickoff(k['gameday'], k['gametime'])
        else:
            fields(p, ('origin', 'document'))
            string(p['origin'])
    # Reject cycles even when reconstruction does not need the time proof.
    def visit(rid, path):
        if rid in path:
            raise ValueError('Dependency cycle')
        for dep in resources[rid]['dependencies']:
            visit(dep, path | {rid})
    for rid in resources:
        visit(rid, set())
    for e in proofs.values():
        fields(e, ('evidence_id', 'kind', 'subject_id', 'origin', 'reference', 'recorded_at', 'value', 'dependencies'), ('receipt',))
        if e['kind'] not in EVIDENCE_KINDS or not isinstance(e['dependencies'], list):
            raise ValueError('Invalid evidence kind/dependencies')
        for key in ('subject_id', 'origin', 'reference'):
            string(e[key])
        instant(e['recorded_at'])
        if e['kind'] in ('FINAL_OBSERVATION', 'EVENT_END_BOUND'):
            instant(e['value'])
        if e['kind'] == 'ARCHIVE_OBSERVATION':
            receipt = e.get('receipt')
            fields(receipt, ('receiptVersion', 'receipt_id', 'archive_id', 'archive_root', 'sha256', 'locator', 'observed_at', 'origin'))
            if (receipt['receiptVersion'] != 1 or identity({k: v for k, v in receipt.items() if k != 'receipt_id'}) != receipt['receipt_id'] or
                    e['subject_id'] != 'sha256:' + receipt['sha256'] or instant(receipt['observed_at']) != instant(e['recorded_at']) or
                    receipt['locator'] != f"blobs/sha256/{receipt['sha256'][:2]}/{receipt['sha256']}"):
                raise ValueError('Archive receipt binding/integrity mismatch')
        if any(dep not in resources for dep in e['dependencies']):
            raise ValueError('Unresolved evidence dependency')
    for c in calculations.values():
        fields(c, ('revision_id', 'calculation_id', 'coverage_revision_id', 'calendar_revision_id', 'pbp_revision_id', 'metadata_revision_ids', 'game', 'versions', 'completeness', 'model', 'source_models', 'unknown_filter_flags_n', 'statistics'), ('source_cause',))
        for key in ('calculation_id', 'coverage_revision_id'):
            string(c[key])
        game(c['game'])
        cal = resources.get(c['calendar_revision_id'])
        pbp = resources.get(c['pbp_revision_id'])
        if cal is None or cal['kind'] != 'CALENDAR' or c['game'] not in cal['payload']['games']:
            raise ValueError('Calculation/calendar mismatch')
        if pbp is None or pbp['kind'] != 'SET' or pbp['payload']['source_kind'] != 'pbp':
            raise ValueError('Calculation requires entire PBP source set')
        if not isinstance(c['metadata_revision_ids'], list) or any(resources.get(d, {}).get('kind') != 'METADATA' for d in c['metadata_revision_ids']):
            raise ValueError('Invalid metadata dependencies')
        fields(c['versions'], ('population', 'definition', 'adapter'))
        for value in c['versions'].values():
            string(value)
        integer(c['unknown_filter_flags_n'])
        envelope(c['completeness'])
        if c['completeness'] is not None and c['completeness']['value'] not in ('UNKNOWN', 'PARTIAL', 'COMPLETE'):
            raise ValueError('Invalid completeness')
        if not isinstance(c['source_models'], dict) or set(c['source_models']) != set(pbp['dependencies']):
            raise ValueError('Source model map must bind every PBP file')
        for env in c['source_models'].values():
            envelope(env)
            if env is not None:
                string(env['value'])
        envelope(c['model'])
        if c['model'] is not None:
            string(c['model']['value'])
        if 'source_cause' in c:
            envelope(c['source_cause'])
            if c['source_cause'] is not None and c['source_cause']['value'] not in ('SOURCE_UNKNOWN', 'PBP_ABSENT', 'SOURCE_DELAY', 'INGESTION_FAILED'):
                raise ValueError('Invalid explicit source cause')
        stats(c['statistics'], c['game'])
    # Missing proof is UNKNOWN; dangling explicit references are structural errors.
    def check_refs(value):
        if isinstance(value, dict):
            if 'evidence_id' in value and value['evidence_id'] not in proofs:
                raise ValueError('Unresolved evidence reference')
            for v in value.values():
                check_refs(v)
        elif isinstance(value, list):
            for v in value:
                check_refs(v)
    check_refs(list(resources.values()))
    check_refs(list(calculations.values()))
    # Separate accepted identities must also be immutable across associations.
    for key, projection in (('calculation_id', lambda c: c), ('coverage_revision_id', lambda c: {k: c[k] for k in ('coverage_revision_id', 'calendar_revision_id', 'pbp_revision_id', 'game', 'statistics', 'unknown_filter_flags_n', 'completeness', 'versions')})):
        seen = {}
        for c in calculations.values():
            content = {k: v for k, v in projection(c).items() if k != 'revision_id'}
            if c[key] in seen and seen[c[key]] != content:
                raise ValueError('IDENTITY_CONFLICT: ' + c[key])
            seen[c[key]] = content
    return resources, proofs, calculations
