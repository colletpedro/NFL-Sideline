#!/usr/bin/env python3
"""Offline fixture gate, stdlib only. Not a replacement for Java claims validation.

Implements only the schema vocabulary used by this frozen contract; unknown
keywords fail closed. Cross-file engine provenance must be verified by E2.
"""
import argparse
import hashlib
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'contracts/visual-analysis/v1'
SCHEMA = json.loads((CONTRACT / 'schema.json').read_text())
COPY = json.loads((CONTRACT / 'copy-catalog.json').read_text())['relations']
RESTRICTION_COPY = json.loads((CONTRACT / 'copy-catalog.json').read_text())['restrictions']

class ContractError(ValueError):
    def __init__(self, code, location=''):
        self.code = code
        super().__init__(f'{code}: {location}')

def require(condition, code, location=''):
    if not condition:
        raise ContractError(code, location)

def check_schema(value, schema, location='$'):
    supported = {'$schema', 'title', 'definitions', '$ref', 'type', 'properties',
                 'additionalProperties', 'required', 'items', 'minItems', 'maxItems',
                 'uniqueItems', 'minLength', 'maxLength', 'minimum', 'maximum',
                 'pattern', 'enum', 'anyOf'}
    require(not (set(schema) - supported), 'UNSUPPORTED_SCHEMA', location)
    if '$ref' in schema:
        return check_schema(value, SCHEMA['definitions'][schema['$ref'].split('/')[-1]], location)
    if 'anyOf' in schema:
        for option in schema['anyOf']:
            try:
                check_schema(value, option, location)
                return
            except ContractError as error:
                if error.code != 'SCHEMA':
                    raise
        raise ContractError('SCHEMA', location)
    if 'enum' in schema:
        require(any(type(value) is type(x) and value == x for x in schema['enum']), 'SCHEMA', location)
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'null': type(None)}
    if kind:
        require(type(value) is types[kind], 'SCHEMA', location)
    if kind == 'object':
        require(set(schema['required']) <= set(value), 'SCHEMA', location)
        require(not (set(value) - set(schema['properties'])), 'SCHEMA', location)
        for key, child in value.items():
            check_schema(child, schema['properties'][key], location + '.' + key)
    elif kind == 'array':
        require(schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', 10**9), 'SCHEMA', location)
        if schema.get('uniqueItems'):
            require(len({json.dumps(v, sort_keys=True) for v in value}) == len(value), 'SCHEMA', location)
        for i, child in enumerate(value):
            check_schema(child, schema['items'], f'{location}[{i}]')
    elif kind == 'string':
        require(schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', 10**9), 'SCHEMA', location)
        if 'pattern' in schema:
            require(re.search(schema['pattern'], value) is not None, 'SCHEMA', location)
    elif kind == 'integer':
        require(schema.get('minimum', value) <= value <= schema.get('maximum', value), 'SCHEMA', location)

def index(values):
    result = {v['id']: v for v in values}
    require(len(result) == len(values), 'DUPLICATE_ID')
    return result

def display_value(value):
    d = Decimal(value)
    if d == 0:
        return '0,000'
    if abs(d) < Decimal('0.0005'):
        return '0 < EPA < 0,0005' if d > 0 else '-0,0005 < EPA < 0'
    # Use a local context large enough for the decimal grammar, without silently rounding the input.
    from decimal import localcontext
    with localcontext() as context:
        context.prec = max(40, len(value) + 5)
        return format(d.quantize(Decimal('.001'), rounding=ROUND_HALF_UP), '+.3f').replace('.', ',')

def pattern(values):
    signs = {(Decimal(v) > 0) - (Decimal(v) < 0) for v in values}
    return ({frozenset({1}): 'ALL_POSITIVE', frozenset({-1}): 'ALL_NEGATIVE',
             frozenset({0}): 'ZERO_ONLY', frozenset({0, 1}): 'NONNEGATIVE_WITH_ZERO',
             frozenset({-1, 0}): 'NONPOSITIVE_WITH_ZERO'}.get(frozenset(signs), 'MIXED_SIGNS'))

def validate(doc):
    check_schema(doc, SCHEMA)
    game, scope = doc['game'], doc['scope']
    teams = {game['awayTeam'], game['homeTeam']}
    require(len(teams) == 2, 'TEAM_MISMATCH')
    require(scope['expectedCurrentWeeks'] == list(range(max(1, game['week'] - 3), game['week'])), 'COVERAGE_MISMATCH')
    if scope['declaredAsOfDate']:
        try:
            date.fromisoformat(scope['declaredAsOfDate'])
        except ValueError as exc:
            raise ContractError('SCHEMA', 'declaredAsOfDate') from exc
    evidence, series, encounters, findings, restrictions = [index(doc[k]) for k in ['evidence', 'series', 'encounters', 'findings', 'restrictions']]
    for e in evidence.values():
        require(e['team'] in teams, 'TEAM_MISMATCH')
        current = e['origin'] == 'CURRENT_SEASON_PRIOR_WEEKS'
        require((e['season'] == game['season'] and e['week'] < game['week']) if current
                else e['season'] < game['season'], 'TEMPORAL_LEAK')
        require(e['metric'].endswith('_PLAY') or e['plays'] is None, 'DENOMINATOR_MISMATCH')
        require(display_value(e['value']) == e['displayValue'], 'DISPLAY_MISMATCH')
    require(len({(e['team'], e['season'], e['week'], e['metric']) for e in evidence.values()}) == len(evidence), 'DUPLICATE_OBSERVATION')
    used_evidence = set()
    for s in series.values():
        require(set(s['evidenceIds']) <= evidence.keys(), 'INVALID_REFERENCE')
        rows = [evidence[e] for e in s['evidenceIds']]
        require(len({(e['team'], e['season'], e['origin'], e['metric']) for e in rows}) == 1, 'SERIES_MISMATCH')
        weeks = [e['week'] for e in rows]
        require(weeks == sorted(set(weeks)), 'SERIES_MISMATCH')
        used_evidence.update(s['evidenceIds'])
    require(used_evidence == evidence.keys(), 'ORPHAN_EVIDENCE')
    require({(e['attackTeam'], e['foundation']) for e in encounters.values()}
            == {(t, f) for t in teams for f in ['PASS', 'RUSH', 'GENERAL']}, 'ENCOUNTER_MISMATCH')
    used_series = set()
    for e in encounters.values():
        require(e['attackTeam'] in teams and e['defenseTeam'] in teams and e['attackTeam'] != e['defenseTeam'], 'TEAM_MISMATCH')
        suffix = 'PLAY' if e['foundation'] == 'GENERAL' else e['foundation']
        windows = []
        for key, team, metric in [('attackSeriesId', e['attackTeam'], 'OFF_EPA_' + suffix), ('defenseSeriesId', e['defenseTeam'], 'DEF_EPA_' + suffix)]:
            sid = e[key]
            if sid is None:
                windows.append([])
                continue
            require(sid in series, 'INVALID_REFERENCE')
            rows = [evidence[i] for i in series[sid]['evidenceIds']]
            require(all(r['team'] == team for r in rows), 'TEAM_MISMATCH')
            require(all(r['metric'] == metric for r in rows), 'METRIC_MISMATCH')
            windows.append(rows)
            used_series.add(sid)
        a, d = windows
        pairable = bool(a and d and (a[0]['origin'], a[0]['season']) == (d[0]['origin'], d[0]['season']))
        require((e['state'] != 'UNAVAILABLE') == pairable, 'ENCOUNTER_MISMATCH')
        if not pairable:
            reason = 'MISSING_BOTH' if not a and not d else 'MISSING_ATTACK' if not a else 'MISSING_DEFENSE' if not d else 'INCOMPATIBLE_ORIGIN'
            require(e['unavailableReason'] == reason, 'ENCOUNTER_MISMATCH')
        else:
            require(e['unavailableReason'] is None, 'ENCOUNTER_MISMATCH')
        if e['state'] != 'REPRESENTED_BY':
            require(not e['representedByFindingIds'], 'GROUPING_MISMATCH')
        else:
            require(e['foundation'] == 'GENERAL' and bool(e['representedByFindingIds']), 'GROUPING_MISMATCH')
            require(set(e['representedByFindingIds']) <= findings.keys(), 'INVALID_REFERENCE')
    require(used_series == series.keys(), 'ORPHAN_SERIES')
    seen_encounters = set()
    for f in findings.values():
        require(f['encounterId'] in encounters and f['primaryRestrictionId'] in restrictions, 'INVALID_REFERENCE')
        e = encounters[f['encounterId']]
        require(e['state'] == 'COMPARABLE' and e['id'] not in seen_encounters, 'ENCOUNTER_MISMATCH')
        seen_encounters.add(e['id'])
        require(not restrictions[f['primaryRestrictionId']]['encounterIds'] or e['id'] in restrictions[f['primaryRestrictionId']]['encounterIds'], 'RESTRICTION_MISMATCH')
        a, d = [[evidence[i] for i in series[e[k]]['evidenceIds']] for k in ['attackSeriesId', 'defenseSeriesId']]
        ap, dp = pattern([r['value'] for r in a]), pattern([r['value'] for r in d])
        require((ap, dp) == (f['attackPattern'], f['defensePattern']), 'SIGN_MISMATCH')
        relation = f['relation']
        # Necessary observable conditions only. Exact adequacy/selection belongs to Java + context.
        if ap == dp == 'ALL_POSITIVE':
            allowed = {'POSITIVE_CONVERGENCE', 'POSITIVE_COMPATIBILITY_ONLY'}
            if relation == 'POSITIVE_CONVERGENCE':
                require(game['phase'] == 'REG' and all(r['origin'] == 'CURRENT_SEASON_PRIOR_WEEKS' for r in a + d)
                        and [r['week'] for r in a] == [r['week'] for r in d] == scope['expectedCurrentWeeks'], 'COVERAGE_MISMATCH')
        elif ap == 'ALL_POSITIVE' and dp == 'ALL_NEGATIVE': allowed = {'FAVORABLE_ATTACK_AND_DEFENSE'}
        elif ap == 'ALL_NEGATIVE' and dp == 'ALL_POSITIVE': allowed = {'ATTACK_NOT_DEMONSTRATED'}
        elif ap == dp == 'ALL_NEGATIVE': allowed = {'BOTH_NEGATIVE'}
        elif 'MIXED_SIGNS' in (ap, dp): allowed = {'WEEKLY_SIGN_VARIATION'}
        else: allowed = {'ZERO_PROFILE'}
        require(relation in allowed, 'RELATION_MISMATCH')
        require({'title': f['title'], 'summary': f['summary']} == COPY[relation], 'COPY_MISMATCH')
    require(seen_encounters == {e['id'] for e in encounters.values() if e['state'] == 'COMPARABLE'}, 'ENCOUNTER_MISMATCH')
    for r in restrictions.values():
        require(set(r['encounterIds']) <= encounters.keys() and set(r['evidenceIds']) <= evidence.keys(), 'INVALID_REFERENCE')
        require(r['text'] == RESTRICTION_COPY[r['code']], 'COPY_MISMATCH')
    p = doc['presentation']
    require(set(p['highlightFindingIds']) <= findings.keys() and set(p['globalRestrictionIds']) <= restrictions.keys(), 'INVALID_REFERENCE')
    flattened = [i for group in p['equivalentHighlightGroups'] for i in group]
    require(len(flattened) == len(set(flattened)), 'TIE_MISMATCH')
    if len(p['highlightFindingIds']) > 1:
        require(len(p['equivalentHighlightGroups']) == 1 and set(flattened) == set(p['highlightFindingIds']), 'TIE_MISMATCH')
    else:
        require(not flattened, 'TIE_MISMATCH')
    require(all(not restrictions[i]['encounterIds'] for i in p['globalRestrictionIds']), 'RESTRICTION_MISMATCH')
    require({'TEMPORAL_AVAILABILITY_UNKNOWN', 'NO_OPPONENT_ADJUSTMENT'} <= {restrictions[i]['code'] for i in p['globalRestrictionIds']}, 'RESTRICTION_MISMATCH')
    for link in doc['links']:
        require(link['fromFindingId'] in findings and link['toFindingId'] in findings, 'INVALID_REFERENCE')
        require(link['fromFindingId'] != link['toFindingId'], 'RELATION_MISMATCH')
        require(link['fromFindingId'] not in p['highlightFindingIds'] and link['toFindingId'] in p['highlightFindingIds'], 'RELATION_MISMATCH')
        source, target = [findings[link[k]] for k in ['fromFindingId', 'toFindingId']]
        source_e, target_e = [encounters[f['encounterId']] for f in [source, target]]
        if link['relation'] == 'INDEPENDENT_OPPORTUNITY':
            require(source['relation'] == 'POSITIVE_CONVERGENCE' and source_e['attackTeam'] != target_e['attackTeam'], 'RELATION_MISMATCH')
        else:
            require(source_e['attackTeam'] == target_e['attackTeam'] and source_e['foundation'] != target_e['foundation']
                    and source['relation'] != 'POSITIVE_CONVERGENCE' and target['relation'] == 'POSITIVE_CONVERGENCE', 'RELATION_MISMATCH')
    for e in encounters.values():
        for fid in e['representedByFindingIds']:
            target = encounters[findings[fid]['encounterId']]
            require(target['attackTeam'] == e['attackTeam'] and target['foundation'] != 'GENERAL', 'GROUPING_MISMATCH')
            for key in ['attackSeriesId', 'defenseSeriesId']:
                rows, target_rows = [[evidence[i] for i in series[c[key]]['evidenceIds']] for c in [e, target]]
                signature = lambda rs: ([(r['season'], r['week'], r['origin']) for r in rs], pattern([r['value'] for r in rs]))
                require(signature(rows) == signature(target_rows), 'GROUPING_MISMATCH')
    return doc

def verify_fixtures():
    freeze_path = CONTRACT / 'freeze.json'
    if freeze_path.exists():
        freeze = json.loads(freeze_path.read_text())
        actual_files = {str(p.relative_to(CONTRACT)) for p in CONTRACT.rglob('*') if p.is_file() and p != freeze_path}
        require(actual_files == set(freeze['files']), 'FREEZE_MISMATCH')
        for path, expected in freeze['files'].items():
            require(hashlib.sha256((CONTRACT / path).read_bytes()).hexdigest() == expected, 'FREEZE_MISMATCH', path)
    manifest = json.loads((CONTRACT / 'fixtures/manifest.json').read_text())
    for file in manifest['valid']:
        validate(json.loads((CONTRACT / 'fixtures' / file).read_text()))
    for case in manifest['invalid']:
        try:
            validate(json.loads((CONTRACT / 'fixtures' / case['file']).read_text()))
        except ContractError as error:
            require(error.code == case['expectedError'], 'WRONG_ERROR', f"{case['file']}: {error}")
        else:
            raise ContractError('INVALID_ACCEPTED', case['file'])
    expected = set(manifest['valid']) | {x['file'] for x in manifest['invalid']}
    actual = {str(p.relative_to(CONTRACT / 'fixtures')) for category in ['valid','invalid'] for p in (CONTRACT / 'fixtures' / category).glob('*.json')}
    require(expected == actual, 'FIXTURE_MANIFEST_MISMATCH')
    return {'valid': len(manifest['valid']), 'invalidRejected': len(manifest['invalid']), 'status': 'PASS', 'engineProvenanceVerified': False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document', type=Path)
    args = parser.parse_args()
    if args.document:
        validate(json.loads(args.document.read_text()))
        print('PASS: structure and observable invariants; original claims/context not verified')
    else:
        print(json.dumps(verify_fixtures()))
