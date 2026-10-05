#!/usr/bin/env python3
"""Offline census/evaluation. Standard library only; never loads .env or calls a service."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess

from compare_local_rules import public_number

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / 'core-api/target/core-api-0.1.0.jar'
VERSION = 'coverage-harness-1.0.0'
FIELDS = ['fator_chave', 'vantagem_tatica', 'alerta_vermelho', 'veredito']
COHORTS = ['unseen', 'regression', 'synthetic', 'unknown']
LABELS = {'unseen': 'Inéditos confirmados', 'regression': 'Regressões / uso anterior comprovado',
          'synthetic': 'Sintéticos', 'unknown': 'Histórico de uso desconhecido'}
FOUNDATION = {'OFF_EPA_PASS': 'passe', 'OFF_EPA_RUSH': 'corrida', 'OFF_EPA_PLAY': 'panorama por jogada'}


def read(p):
    return json.loads(Path(p).read_text())


def write(p, value):
    with Path(p).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


def safe_directory(path):
    path = Path(path).resolve()
    if 'public' in path.parts or 'web-ui' in path.parts:
        raise ValueError('Public/frontend output forbidden')
    return path


def canonical(root, include_game=True):
    """Separate census normalization, not the engine context hash. Decimal-equivalent values dedup."""
    records = []
    for item in root['evidence']:
        e = {k: item.get(k) for k in ['id', 'team', 'metric', 'season', 'week', 'origin', 'value', 'unit', 'volume', 'sourceTable', 'sourceKey']}
        for k in ['value', 'volume']:
            if e[k] is not None:
                n = Decimal(str(e[k]))
                if not n.is_finite():
                    raise ValueError('Non-finite evidence')
                e[k] = format(n.normalize(), 'f') if n else '0'
        records.append(json.dumps(e, sort_keys=True))
    result = {'home_team': root['home_team'], 'away_team': root['away_team'], 'evidence': sorted(set(records)),
              'game': {k: root['game'].get(k) for k in ['season', 'week', 'phase']}}
    if include_game:
        result['game']['game_id'] = root['game']['game_id']
    return result


def descriptors(root):
    weeks = {t: sorted({e['week'] for e in root['evidence'] if e['team'] == t}) for t in [root['home_team'], root['away_team']]}
    signs = {}
    for e in root['evidence']:
        n = Decimal(str(e['value']))
        signs.setdefault(e['team'] + ':' + e['metric'], set()).add('positive' if n > 0 else 'negative' if n < 0 else 'zero')
    w = root['game']['week']
    expected = set(range(max(1, w - 3), w))
    gaps = {t: sorted(expected - set(ws)) for t, ws in weeks.items()}
    return {'season': root['game']['season'], 'gameWeek': w, 'seasonStage': 'early' if w <= 4 else 'middle' if w <= 12 else 'late',
            'weeksByTeam': weeks, 'weekCounts': sorted(len(ws) for ws in weeks.values()),
            'differentWeeks': len({tuple(ws) for ws in weeks.values()}) > 1,
            'signsByTeamMetric': {k: sorted(v) for k, v in sorted(signs.items())},
            'missingExpectedWeeks': gaps, 'byeConfirmed': False,
            'byeEvidence': None, 'gapCause': 'unknown' if any(gaps.values()) else 'no_gap_identified'}


def inventory(base):
    # Do not deserialize stored response_text/context_json: only cache metadata proves prior use.
    known_manifest = ROOT / 'editorial/evaluations/2026-09-26/cases.json'
    known = {c['gameId']: str(known_manifest.parent / c['context']) for c in read(known_manifest)['cases']}
    usage = {}
    db = ROOT / 'editorial/evaluations/2026-09-26/provenance/database-originals.json'
    for row in read(db):
        if row.get('response_text'):
            usage.setdefault(row['game_id'], []).append({'source': rel(db), 'type': 'prior_cached_generation', 'cacheId': row['id']})
    roots = ['editorial', 'core-api/src/test/resources', 'etl-pipeline/data', 'etl-pipeline/tests']
    files = sorted({p for directory in roots for p in (ROOT / directory).rglob('*') if p.is_file()
                    and not set(p.parts).intersection({'.venv', 'node_modules', 'target', '__pycache__', '.git'})
                    and not p.resolve().is_relative_to(base) and not any(part.startswith('.') for part in p.relative_to(ROOT).parts)
                    and p.suffix in {'.json', '.csv', '.parquet'}})
    # Result and attempt metadata from ALL previous evaluations, not just the original six.
    for p in files:
        if p.name not in {'result.json', 'attempt.json', 'attempt-ledger.json', 'cases.json'}:
            continue
        data = read(p)
        entries = data.get('attempts', data.get('cases', [data])) if isinstance(data, dict) else []
        for item in entries:
            game = item.get('gameId') or item.get('game_id')
            if game:
                usage.setdefault(game, []).append({'source': rel(p), 'type': 'prior_evaluation_record'})
    entries, excluded = [], []
    for p in files:
        if p.suffix != '.json':
            excluded.append({'path': rel(p), 'reason': 'NOT_DIRECT_CONTEXT_FORMAT', 'sha256': sha(p)})
            continue
        try:
            root = read(p)
        except (ValueError, UnicodeError):
            excluded.append({'path': rel(p), 'reason': 'INVALID_JSON'})
            continue
        if not isinstance(root, dict) or root.get('contract_version') != 3 or not all(k in root for k in ['game', 'home_team', 'away_team', 'evidence']):
            excluded.append({'path': rel(p), 'reason': 'NOT_TACTICAL_CONTEXT'})
            continue
        try:
            normalized = canonical(root)
            entries.append({'path': rel(p), 'sha256': sha(p), 'normalizedSha256': digest(normalized),
                            'contentSha256': digest(canonical(root, False)), 'gameId': root['game']['game_id'],
                            'descriptors': descriptors(root)})
        except (ValueError, KeyError, TypeError):
            excluded.append({'path': rel(p), 'reason': 'INVALID_CONTEXT_STRUCTURE', 'sha256': sha(p)})
    groups = {}
    for e in entries:
        groups.setdefault(e['gameId'], []).append(e)
    selected, seen_content = [], {}
    for game, origins in sorted(groups.items()):
        origins.sort(key=lambda e: (str(ROOT / e['path']) != known.get(game), '/contexts/' not in e['path'], e['path']))
        chosen = origins[0]
        if chosen['contentSha256'] in seen_content:
            excluded.append({'path': chosen['path'], 'reason': 'DUPLICATE_CONTENT_OTHER_ID', 'duplicateOf': seen_content[chosen['contentSha256']]})
            continue
        seen_content[chosen['contentSha256']] = game
        synthetic = not re.fullmatch(r'\d{4}_\d{2}_[A-Z0-9]+_[A-Z0-9]+', game)
        cohort = 'synthetic' if synthetic else 'regression' if game in known or game in usage else 'unknown'
        selected.append({**chosen, 'cohort': cohort, 'knownSix': game in known,
                         'usageHistory': usage.get(game, []), 'novelty': 'not_independent' if cohort != 'unknown' else 'unverified',
                         'origins': [{k: e[k] for k in ['path', 'sha256', 'normalizedSha256']} for e in origins],
                         'distinctNormalizedVersions': len({e['normalizedSha256'] for e in origins})})
    data = {'version': VERSION, 'createdAt': stamp(), 'protocolSha256': sha(base / 'PROTOCOL.md'), 'roots': roots,
            'selection': 'All unique directly consumable local contexts; no sampling', 'seed': None,
            'filesInventoried': len(files), 'contextFiles': len(entries),
            'uniqueNormalizedContexts': len({e['normalizedSha256'] for e in entries}),
            'duplicateContextFiles': len(entries) - len({e['normalizedSha256'] for e in entries}),
            'selectedCases': len(selected), 'cohorts': dict(Counter(c['cohort'] for c in selected)),
            'cases': selected, 'excluded': excluded,
            'calendarPolicy': 'Initial input descriptor only; calendar-evidence.json supplies separate verified annotations',
            'usageEvidence': [{'path': rel(db), 'sha256': sha(db)}, {'path': rel(known_manifest), 'sha256': sha(known_manifest)}]}
    write(base / 'manifest.json', data)
    print(json.dumps({k: data[k] for k in ['filesInventoried', 'contextFiles', 'uniqueNormalizedContexts', 'selectedCases', 'cohorts']}, indent=2))


def freeze(base):
    paths = list((ROOT / 'core-api/src').rglob('*.java'))
    paths += [JAR, ROOT / 'AGENTS.md', ROOT / 'scripts/test_local_calendar.py', ROOT / 'core-api/pom.xml', Path(__file__), ROOT / 'scripts/compare_local_rules.py',
              ROOT / 'scripts/test_evaluate_coverage.py', ROOT / 'scripts/test_inspection_page.cjs', ROOT / 'scripts/export_local_calendar.py', ROOT / 'Spec.md', ROOT / 'docs/local-rules-editorial.md',
              ROOT / 'docs/analysis-claims-contract.md', ROOT / 'docs/coverage-clarity-evaluation.md',
              base / 'PROTOCOL.md', base / 'manifest.json', base / 'calendar-evidence.json']
    paths += [ROOT / v['path'] for v in read(base / 'calendar-evidence.json')['schedules'].values()]
    paths += [ROOT / c['path'] for c in read(base / 'manifest.json')['cases']]
    paths += [p for p in (ROOT / 'core-api/src/main/resources').rglob('*') if p.is_file()]
    write(base / 'freeze.json', {'createdAt': stamp(), 'selector': 'local-descriptive-rules:2.0.0',
          'renderer': 'controlled-claims-v5.0.1', 'claimsContract': 5, 'inputContract': 3, 'harness': VERSION,
          'hashes': {rel(p): sha(p) for p in sorted(set(paths))}})


def verify(base):
    frozen = read(base / 'freeze.json')['hashes']
    bad = [p for p, value in frozen.items() if not (ROOT / p).is_file() or sha(ROOT / p) != value]
    if bad:
        raise ValueError('Freeze changed: ' + ', '.join(bad))
    return {'checkedAt': stamp(), 'filesChecked': len(frozen), 'mismatches': []}


def run(base, output, known_only=False):
    output = safe_directory(output)
    before = verify(base) if not known_only else {'developmentOnly': True}
    output.mkdir()
    write(output / 'check-before.json', before)
    manifest = read(base / 'manifest.json')
    java = str(Path(os.environ['JAVA_HOME']) / 'bin/java') if 'JAVA_HOME' in os.environ else 'java'
    # No .env or inherited generation/database credentials. No process output copied to public artifacts.
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'LANG': 'en_US.UTF-8'}
    results = []
    for case in manifest['cases']:
        if known_only and not (case['knownSix'] or case['cohort'] == 'synthetic'):
            continue
        dest = output / case['gameId']
        try:
            proc = subprocess.run([java, '-jar', str(JAR), 'editorial-local', str(ROOT / case['path']), str(dest)],
                                  cwd=ROOT, env=env, capture_output=True, timeout=90)
            result = read(dest / 'result.json') if (dest / 'result.json').exists() else {}
            record = {'gameId': case['gameId'], 'cohort': case['cohort'], 'knownSix': case['knownSix'],
                      'exitCode': proc.returncode, 'status': result.get('status', 'HARNESS_PROCESS_FAILURE'),
                      'failureCategory': result.get('validationFailures', [])}
            if not result:
                record['failureCategory'] = ['PROCESS_NO_RESULT']
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            record = {'gameId': case['gameId'], 'cohort': case['cohort'], 'knownSix': case['knownSix'],
                      'exitCode': None, 'status': 'HARNESS_PROCESS_FAILURE', 'failureCategory': [type(error).__name__]}
        results.append(record)
        # Exclusive per-case journal survives interruption without replacing prior records.
        write(output / (case['gameId'] + '.execution.json'), record)
    write(output / 'execution.json', {'startedUnderFreeze': not known_only, 'results': results, 'manifestSha256': sha(base / 'manifest.json')})
    write(output / 'check-after.json', verify(base) if not known_only else {'developmentOnly': True})
    print(dict(Counter(r['status'] for r in results)))


def words(text):
    return re.findall(r'[^\W_]+', text, re.UNICODE)


def normalize(text):
    return ' '.join(words(text.casefold()))


def distribution(values):
    values = sorted(values)
    return {'n': len(values), 'values': values, 'median': statistics.median(values) if values else None,
            'p90': values[math.ceil(.9 * len(values)) - 1] if values else None, 'max': max(values) if values else None}


def repetition(text):
    result = []
    for i, a in enumerate(FIELDS):
        for b in FIELDS[i + 1:]:
            sentences = lambda v: {normalize(s) for s in re.split(r'[.!?\n]+', v) if len(words(s)) >= 5}
            result.append({'fields': [a, b], 'exact': text[a] == text[b], 'normalized': normalize(text[a]) == normalize(text[b]),
                           'sharedSentences': sorted(sentences(text[a]) & sentences(text[b]))})
    return result


def checks(selection, text):
    """Trace candidate/window/claim to its own rendered segment; not whole-document keyword scoring."""
    doc = selection['document']
    candidates = {c['id']: c for c in selection['candidates']}
    issues, observations = [], []
    for cid in doc['sections']['vantagem_tatica']:
        if cid not in candidates:
            continue
        c = candidates[cid]
        label = FOUNDATION[c['foundation']].capitalize()
        lines = [line for line in text['vantagem_tatica'].splitlines() if line.startswith(label + ' — ' + c['attackTeam'] + ' (ataque):')]
        numeric_ok = len(lines) == 1 and ('; ' + c['defenseTeam'] + ' (EPA permitido):') in lines[0]
        scope_ok, aggregation_ok = True, True
        for side in ['attack', 'defense']:
            window = c[side]
            values = [window['value']]
            if Decimal(str(window['minimum'])) != Decimal(str(window['maximum'])):
                values += [window['minimum'], window['maximum']]
            # Keep each measure associated with the attack/defense side, not just anywhere in the analysis.
            separator = '; ' + c['defenseTeam'] + ' (EPA permitido):'
            parts = lines[0].split(separator, 1) if lines else []
            segment = parts[0 if side == 'attack' else 1] if len(parts) == 2 else ''
            numeric_ok = numeric_ok and all(public_number(v) in segment for v in values)
            scope = 'semanas ' + ', '.join(map(str, window['weeks'])) + ' ('
            scope_ok &= scope in text['vantagem_tatica'] and str(window['season']) in text['vantagem_tatica']
            aggregation_ok &= ('sem ponderação por jogadas' in text['vantagem_tatica'] if window['aggregation'] == 'MEAN_OF_WEEKLY_MEANS'
                               else 'ponderad' in text['vantagem_tatica'] and str(window['volume']) + ' jogadas' in segment)
        observations.append({'claimId': cid, 'type': 'principal_support', 'numericAttribution': numeric_ok,
                             'scopePresent': scope_ok, 'aggregationPresent': aggregation_ok})
        for name, ok in [('NUMERIC_ATTRIBUTION', numeric_ok), ('SCOPE', scope_ok), ('AGGREGATION', aggregation_ok)]:
            if not ok:
                issues.append({'claimId': cid, 'type': name})
    verdict = text['veredito']
    for claim in doc['claims']:
        if claim['type'] != 'MATCHUP':
            continue
        c = candidates[claim['claim_id']]
        # Sentences with semicolon remain one segment. Foundation grouping stays within that segment.
        segments = [s for s in verdict.split('. ') if ('ataque de ' + c['attackTeam'] + ' contra a defesa de ' + c['defenseTeam']) in s
                    and FOUNDATION[c['foundation']] in s]
        ok = bool(segments)
        signal_ok = True
        for side, team, prefix in [('attack', c['attackTeam'], 'EPA do ataque de '), ('defense', c['defenseTeam'], 'EPA permitido pela defesa de ')]:
            signal = c['signals'][side]
            if signal['pattern'] == 'MIXED_SIGNS':
                signal_ok &= any(prefix + team + ', há semanas com valores positivos e negativos' in s for s in segments)
            if signal['containsZero']:
                signal_ok &= any(prefix + team in s and 'zero' in s.split(prefix + team, 1)[1].split(';')[0] for s in segments)
        if c['signals']['relation'] == 'BOTH_NEGATIVE':
            signal_ok &= any('ataque de ' + c['attackTeam'] + ' apresentou EPA negativo' in s and
                             'defesa de ' + c['defenseTeam'] + ' permitiu EPA negativo' in s for s in segments)
        if c['signals']['relation'] == 'FAVORABLE_ATTACK_AND_DEFENSE':
            signal_ok &= any('ataque de ' + c['attackTeam'] + ' teve EPA positivo' in s and
                             'defesa de ' + c['defenseTeam'] + ' permitiu EPA negativo' in s for s in segments)
        observations.append({'claimId': claim['claim_id'], 'type': 'verdict_attribution', 'pairAndFoundation': ok, 'contrarySignsAndZero': bool(signal_ok)})
        if not ok or not signal_ok:
            issues.append({'claimId': claim['claim_id'], 'type': 'VERDICT_ATTRIBUTION_OR_SIGNAL'})
    by_id = {c['claim_id']: c for c in doc['claims']}
    for claim in doc['claims']:
        if claim['type'] != 'WINDOW_LIMITATION':
            continue
        links = [l for l in doc['links'] if l['from'] == claim['claim_id'] and l['relation'] == 'INTERNAL_LIMITATION']
        ok = bool(links) and all(claim['evidence_ids'] == by_id[l['to']]['evidence_ids'] for l in links)
        alert = text['alerta_vermelho'].lower()
        for link in links:
            c = candidates[link['to']]
            ok &= FOUNDATION[c['foundation']] in alert
            if claim['predicate'] == 'SIGN_VARIATION_LIMIT':
                for side, team in [('attack', c['attackTeam']), ('defense', c['defenseTeam'])]:
                    if c['signals'][side]['pattern'] == 'MIXED_SIGNS': ok &= team.lower() in alert
            else: ok &= c['attackTeam'].lower() in alert
        predicate_tokens = {'SIGN_VARIATION_LIMIT': 'sinais diferentes', 'SAMPLE_LIMIT': 'duas observações',
                            'COVERAGE_LIMIT': 'limitam uma leitura conjunta', 'LIMITED_SCOPE': 'sem ajuste por adversário'}
        expected = predicate_tokens.get(claim['predicate'], '')
        if claim['predicate'] == 'LIMITED_SCOPE': expected = 'não têm ajuste por adversário'
        ok &= expected in alert
        observations.append({'claimId': claim['claim_id'], 'type': 'internal_limit', 'linkedLimitationPresent': bool(ok)})
        if not ok: issues.append({'claimId': claim['claim_id'], 'type': 'INTERNAL_LIMIT_REALIZATION'})
    represented = {c['claim_id'] for c in doc['claims'] if c['type'] == 'MATCHUP'}
    grouped = {g['candidateId'] for g in doc.get('groupings', [])}
    if {c['id'] for c in candidates.values() if c['pairable']} != represented | grouped:
        issues.append({'type': 'PUBLIC_INVENTORY'})
    for link in doc['links']:
        if link['from'] == link['to']:
            issues.append({'type': 'SELF_LINK'})
    if 'não estima o vencedor' not in verdict:
        issues.append({'type': 'DESCRIPTIVE_SCOPE'})
    return {'issues': issues, 'observations': observations, 'commonValidatorApproved': True,
            'semanticLimit': 'Structural realization probes plus common validator; not proof of complete editorial correctness'}


def case_metrics(case, directory, execution):
    row = {**execution, 'source': case['path'], 'descriptors': case['descriptors']}
    if execution['status'] != 'VALIDATED':
        return row
    selection, text = read(directory / 'selection.json'), read(directory / 'rendered.json')
    candidates, doc = selection['candidates'], selection['document']
    row['directionalViolation'] = doc['verdict'] != 'INCONCLUSIVE' or doc['thesis_team'] != 'NONE'
    pairs = [c for c in candidates if c['pairable']]
    adequate = [c for c in candidates if c['adequateCoverage']]
    positive = [c for c in pairs if c['signals']['attack']['pattern'] == c['signals']['defense']['pattern'] == 'ALL_POSITIVE']
    opportunities = [c for c in candidates if c['signals']['relation'] == 'POSITIVE_CONVERGENCE']
    row['coverage'] = {'encounters': len(candidates), 'pairable': len(pairs), 'adequate': len(adequate), 'opportunities': len(opportunities),
                       'positivePairs': len(positive), 'coverageBlockedPositivePairs': len([c for c in positive if not c['adequateCoverage']]),
                       'adequateNonPositivePairs': len([c for c in adequate if c not in positive]),
                       'limitations': dict(Counter(l for c in candidates for l in c['limitations']))}
    if opportunities:
        reason = 'HAS_OPPORTUNITY'
    elif positive:
        reason = 'POSITIVE_PAIRS_BLOCKED_BY_COVERAGE_OTHER_SIGN_PATTERNS_MAY_COEXIST'
    elif pairs:
        reason = 'NO_POSITIVE_CONVERGENCE_IN_OBSERVED_SIGNS' if len(adequate) == len(pairs) else 'SIGN_PATTERN_AND_COVERAGE_LIMITS_COEXIST'
    else:
        reason = 'NO_PAIRABLE_ENCOUNTER_SIGN_RELATION_UNAVAILABLE'
    row['noOpportunityReason'] = reason
    row['patterns'] = sorted({c['signals']['relation'] for c in candidates})
    row['length'] = {f: {'words': len(words(text[f])), 'characters': len(text[f])} for f in FIELDS}
    row['length']['total'] = {unit: sum(row['length'][f][unit] for f in FIELDS) for unit in ['words', 'characters']}
    row['repetition'] = repetition(text)
    row['checks'] = checks(selection, text)
    row['groupings'] = doc.get('groupings', [])
    row['rendered'] = text
    row['versions'] = read(directory / 'result.json')
    return row


def summarize(rows):
    valid = [r for r in rows if r['status'] == 'VALIDATED']
    real = [r for r in rows if r['cohort'] != 'synthetic']
    observations = [o for r in valid for o in r['checks']['observations']]
    check_counts = {}
    for key in ['numericAttribution', 'scopePresent', 'aggregationPresent', 'pairAndFoundation', 'contrarySignsAndZero', 'linkedLimitationPresent']:
        relevant = [o[key] for o in observations if key in o]
        check_counts[key] = {'passed': sum(relevant), 'denominator': len(relevant)}
    repetitions = [p for r in valid for p in r['repetition']]
    return {'attempted': len(rows), 'validated': len(valid), 'failed': len(rows) - len(valid),
            'failureCategories': dict(Counter(str(x) for r in rows for x in r['failureCategory'])),
            'inputRejections': sum('INVALID_LOCAL_INPUT' in r['failureCategory'] for r in rows),
            'harnessProcessFailures': sum(r['status'] == 'HARNESS_PROCESS_FAILURE' for r in rows),
            'validationFailures': sum(any(x not in ['INVALID_LOCAL_INPUT', 'LOCAL_IO_OR_RUNTIME_FAILURE'] for x in r['failureCategory'])
                                      and r['status'] != 'HARNESS_PROCESS_FAILURE' for r in rows),
            'directionalViolations': sum(r['directionalViolation'] for r in valid), 'directionalDenominator': len(valid),
            'encountersDenominator': sum(r['coverage']['encounters'] for r in valid),
            'pairable': sum(r['coverage']['pairable'] for r in valid), 'adequate': sum(r['coverage']['adequate'] for r in valid),
            'opportunities': sum(r['coverage']['opportunities'] for r in valid),
            'noOpportunityReasons': dict(Counter(r['noOpportunityReason'] for r in valid)),
            'limitations': dict(sum((Counter(r['coverage']['limitations']) for r in valid), Counter())),
            'realCasesDenominator': len(real), 'confirmedByeCases': sum(r['descriptors']['byeConfirmed'] for r in real),
            'unknownGapCauseCases': sum(r['descriptors']['gapCause'] == 'unknown' for r in real),
            'textChecks': check_counts, 'textIssueCount': sum(len(r['checks']['issues']) for r in valid),
            'length': {f: {u: distribution([r['length'][f][u] for r in valid]) for u in ['words', 'characters']} for f in FIELDS + ['total']},
            'repetition': {'blockPairDenominator': len(repetitions), 'exactEqualPairs': sum(p['exact'] for p in repetitions),
                           'normalizedEqualPairs': sum(p['normalized'] for p in repetitions),
                           'pairsWithSharedSentence': sum(bool(p['sharedSentences']) for p in repetitions)},
            'editorialGroupings': sum(len(r['groupings']) for r in valid)}


def metrics(base, run_dir, output):
    manifest = read(base / 'manifest.json')
    cases = {c['gameId']: c for c in manifest['cases']}
    rows = [case_metrics(cases[r['gameId']], run_dir / r['gameId'], r) for r in read(run_dir / 'execution.json')['results']]
    calendar = read(base / 'calendar-evidence.json')['cases']
    for row in rows:
        if row['gameId'] in calendar:
            item = calendar[row['gameId']]
            row['descriptors'].update({'byeConfirmed': item['byeConfirmed'], 'byeEvidence': item,
                                      'gapCause': 'unknown' if item['unknownGap'] else 'confirmed_bye' if item['byeConfirmed'] else 'no_gap_identified'})
    write(output, {'version': VERSION, 'run': rel(run_dir), 'protocolSha256': sha(base / 'PROTOCOL.md'),
                   'independentEvaluation': any(r['cohort'] == 'unseen' for r in rows), 'qualityProven': False,
                   'inventory': {k: manifest[k] for k in ['filesInventoried', 'contextFiles', 'uniqueNormalizedContexts', 'duplicateContextFiles', 'selectedCases']},
                   'excludedFileReasons': dict(Counter(e['reason'] for e in manifest['excluded'])),
                   'inputStrataReal': {'seasonStage': dict(Counter(r['descriptors']['seasonStage'] for r in rows if r['cohort'] != 'synthetic')),
                                       'weekCountPairs': dict(Counter(str(r['descriptors']['weekCounts']) for r in rows if r['cohort'] != 'synthetic')),
                                       'differentWeeks': sum(r['descriptors']['differentWeeks'] for r in rows if r['cohort'] != 'synthetic')},
                   'cases': rows, 'all': summarize(rows), 'cohorts': {c: summarize([r for r in rows if r['cohort'] == c]) for c in COHORTS},
                   'knownSix': summarize([r for r in rows if r['knownSix']]),
                   'outsideKnownSixReal': summarize([r for r in rows if not r['knownSix'] and r['cohort'] != 'synthetic']),
                   'limits': ['Historical cached generation is prior use, not a confirmed unseen case.',
                              'No independent quality estimate or Gemini evaluation claim.',
                              'Byes require the frozen complete local calendar; remaining gaps have unknown causes.',
                              'Text probes and validity do not prove editorial quality.']})


def build_html(base, metric_path, output):
    data = read(metric_path)
    escape = lambda x: html.escape(str(x), quote=True)
    pre = lambda x: '<pre>' + escape(json.dumps(x, ensure_ascii=False, indent=2)) + '</pre>'
    cards = []
    renderers = set()
    for row in data['cases']:
        run_dir = ROOT / data['run'] / row['gameId']
        coverage = row.get('coverage', {})
        level = 'adequate' if coverage.get('adequate') == 6 else 'partial' if coverage.get('pairable', 0) else 'none'
        failed = row['status'] != 'VALIDATED' or bool(row.get('checks', {}).get('issues'))
        attrs = {'cohort': row['cohort'], 'coverage': level, 'failure': 'yes' if failed else 'no', 'patterns': ' '.join(row.get('patterns', []))}
        attr_text = ' '.join('data-' + k + '="' + escape(v) + '"' for k, v in attrs.items())
        blocks = ''.join('<section><h3>' + escape(f.replace('_', ' ')) + '</h3><p>' + escape(row.get('rendered', {}).get(f, 'Sem texto gerado.')) + '</p></section>' for f in FIELDS)
        details = {key: read(run_dir / (key + '.json')) for key in ['context', 'claims', 'selection', 'result'] if (run_dir / (key + '.json')).exists()}
        if details.get('result', {}).get('rendererVersion'):
            renderers.add(details['result']['rendererVersion'])
        details.update({'source': row['source'], 'descriptors': row['descriptors'], 'checks': row.get('checks', {}), 'metrics': row.get('length', {})})
        cards.append('<article ' + attr_text + '><header><h2>' + escape(row['gameId']) + '</h2><span>' + escape(LABELS[row['cohort']]) + ' · ' + escape(row['status']) + '</span></header>'
                     + '<p class="meta">Pareáveis: ' + escape(coverage.get('pairable', '—')) + '/6 · adequados: ' + escape(coverage.get('adequate', '—')) + '/6 · oportunidades: ' + escape(coverage.get('opportunities', '—')) + '/6</p>'
                     + '<div class="blocks">' + blocks + '</div><details><summary>Evidências, recortes, relações e motivos</summary>' + pre(details) + '</details></article>')
    def select(key, label, values):
        return '<label>' + label + '<select id="' + key + '"><option value="">Todos</option>' + ''.join('<option value="' + escape(v) + '">' + escape(t) + '</option>' for v, t in values) + '</select></label>'
    filters = select('cohort', 'Origem', list(LABELS.items())) + select('coverage', 'Cobertura', [('adequate', 'Seis adequados'), ('partial', 'Parcial'), ('none', 'Sem pares')])
    filters += select('patterns', 'Relação de sinais', [(p, p) for p in sorted({p for r in data['cases'] for p in r.get('patterns', [])})])
    filters += select('failure', 'Falhas ou alertas das verificações', [('yes', 'Com falha/alerta'), ('no', 'Sem falha/alerta')])
    table = '<table><caption>Denominadores por origem</caption><thead><tr><th>Origem</th><th>Gerados / executados</th><th>Pares / encontros</th><th>Adequados / encontros</th><th>Oportunidades / encontros</th></tr></thead><tbody>'
    for c in COHORTS:
        s = data['cohorts'][c]
        table += '<tr><th>' + escape(LABELS[c]) + '</th>' + ''.join('<td>' + str(s[a]) + ' / ' + str(s[b]) + '</td>' for a, b in [('validated', 'attempted'), ('pairable', 'encountersDenominator'), ('adequate', 'encountersDenominator'), ('opportunities', 'encountersDenominator')]) + '</tr>'
    table += '</tbody></table>'
    document = '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; font-src 'none'; base-uri 'none'; form-action 'none'">
<title>NFL Sideline · avaliação interna</title><style>
:root{--bg:#f1f5f9;--card:#fff;--ink:#172b45;--muted:#475569;--line:#cbd5e1;--accent:#1d4ed8}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}main{max-width:1800px;margin:auto;padding:32px}h1{font-size:clamp(26px,3vw,40px);margin:10px 0}h2{font-size:23px;margin:0}h3{font-size:14px;text-transform:uppercase;letter-spacing:.07em;color:var(--accent)}.eyebrow{font-weight:700;letter-spacing:.05em}.meta,header span{color:var(--muted)}.filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-top:24px}label{font-size:14px;font-weight:650}select{display:block;width:100%;min-height:46px;font:inherit;background:var(--card);border:1px solid var(--muted);border-radius:6px;padding:8px;margin-top:6px;color:var(--ink)}:focus-visible{outline:3px solid var(--accent);outline-offset:3px}article{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:24px 0;padding:24px}article header{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px}.blocks{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px}.blocks p{white-space:pre-line;overflow-wrap:anywhere}details{border-top:1px solid var(--line);padding-top:12px}summary{cursor:pointer;min-height:44px;font-weight:650;color:var(--accent)}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 ui-monospace,monospace;background:var(--bg);padding:16px;max-height:600px;overflow:auto}table{border-collapse:collapse;width:100%;background:var(--card);font-variant-numeric:tabular-nums}caption{text-align:left;font-size:20px;font-weight:650;padding:16px 0}th,td{padding:12px;text-align:left;border-bottom:1px solid var(--line)}.table-wrap{overflow:auto}.notice{border-left:4px solid var(--accent);padding:12px 18px;background:#e2e8f0}#count{font-weight:650}[hidden]{display:none!important}@media(max-width:1100px){.blocks,.filters{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:640px){main{padding:16px}.blocks,.filters{grid-template-columns:1fr}article{padding:16px}}
</style></head><body><main><div class="eyebrow">NFL SIDELINE · AVALIAÇÃO INTERNA — NÃO PUBLICADA</div><h1>Cobertura e clareza</h1>
<p>Seletor 2.0.0 · contrato 5 · renderer RENDERER_VERSIONS · harness 1.0.0</p>
<div class="notice">Censo de contextos locais congelados. Uso anterior comprovado não é avaliação inédita. Nenhuma nota de qualidade: validade, tamanho e repetição são verificações e indicadores, não prova de qualidade editorial. Lacunas não confirmam bye.</div>'''
    document = document.replace('RENDERER_VERSIONS', escape(', '.join(sorted(renderers)) or 'não informado'))
    document += '<p>Origem: ' + escape(data['run']) + '</p><div class="table-wrap">' + table + '</div><details><summary>Métricas, distribuições e limitações do lote</summary>' + pre({k: data[k] for k in ['all', 'cohorts', 'limits']}) + '</details>'
    document += '<div class="filters">' + filters + '</div><p id="count" role="status" aria-live="polite"></p>' + ''.join(cards)
    document += '''<script>
const selectors=[...document.querySelectorAll('select')], cards=[...document.querySelectorAll('article')];
function filter(){let visible=0; for(const card of cards){card.hidden=!selectors.every(s=>!s.value||(s.id==='patterns'?card.dataset.patterns.split(' ').includes(s.value):card.dataset[s.id]===s.value));if(!card.hidden)visible++;}document.getElementById('count').textContent=visible+' de '+cards.length+' casos exibidos';}
selectors.forEach(s=>s.addEventListener('change',filter));filter();
</script></main></body></html>'''
    with Path(output).open('x') as f:
        f.write(document)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inventory', 'freeze', 'check', 'run', 'known', 'metrics', 'html'])
    parser.add_argument('base', type=Path)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--metrics', type=Path)
    args = parser.parse_args()
    base = safe_directory(args.base)
    if args.output:
        args.output = safe_directory(args.output)
    if args.command == 'inventory': inventory(base)
    elif args.command == 'freeze': freeze(base)
    elif args.command == 'check': print(json.dumps(verify(base), indent=2))
    elif args.command in ['run', 'known']: run(base, args.output, args.command == 'known')
    elif args.command == 'metrics': metrics(base, args.run, args.output)
    else: build_html(base, args.metrics, args.output)


if __name__ == '__main__':
    main()
