"""New projection of verified legacy sources; legacy documents stay untouched."""
from fractions import Fraction
from math import isfinite
import base64
from io import BytesIO
import json

import polars as pl

from ..situational import encoded, digest, RAW_HASH
from . import VERSION, POLICY, GAME, SITUATIONAL_PIN, OBSERVATION_PIN
from .policy import decision, fraction, LIMITS

GUARANTEES = {k: 'UNKNOWN' for k in ('completeness', 'expectedCoverage', 'epaModel', 'historicalAvailability')}
EVIDENCE_FIELDS = '''game_id play_id fixed_drive order_sequence posteam defteam down play_type yardline_100 ydstogo play_deleted penalty extra_point_attempt two_point_attempt touchdown td_team field_goal_result interception fumble_lost fourth_down_failed safety fixed_drive_result qtr game_seconds_remaining desc'''.split()


def key(r):
    return f"{r['game_id']}:{int(r['play_id'])}"


def exact(value):
    return dict(numerator=str(value.numerator), denominator=value.denominator)


def descriptor(id_, metric, team, definition, population, unit, source_column, n, d, status, ids, games, ambiguous=()):
    return dict(id=id_, metric=metric, team=team, perspective='off', season=2026, phase='REG', weeks=[1],
                definition=definition, population=population, unit=unit, sourceHash=RAW_HASH, sourceColumn=source_column,
                numerator=n, denominator=d, status=status, unitIds=ids, gameIds=games, ambiguousIds=list(ambiguous),
                integrityVerified=True, provenanceVerified=True, guarantees=GUARANTEES)


def situational_descriptor(d, family, suffix=None):
    m = d[family] if suffix is None else d[family]['byDistance'][suffix]
    ids = d[family]['unitIds']
    return descriptor(d['id']+'/'+family+('/'+suffix if suffix else ''), family, d['team'],
                      dict(version='situational-1.0.0', family=family, distance=suffix or 'all'), 'third-eligible-1.0.0' if family == 'third' else 'red-zone-campaign-1.0.0',
                      'attempt' if family == 'third' else 'campaign',
                      'third_down_converted' if family == 'third' else 'yardline_100+fixed_drive+terminal-events',
                      m['numerator'], m['denominator'], d[family]['status'], ids,
                      [g['gameId'] for g in d['games']], d[family]['ambiguousIds'])


def epa_projection(off, defense, rows):
    if off['definition'] != defense['definition'] or off['totals'] != defense['totals'] or off['values'] != defense['values']:
        raise ValueError('EPA offense/opponent-defense mismatch')
    if off['definition'] != dict(definitionVersion='1.0.0', populationVersion='classified-scrimmage-v1', adapterVersion='1.0.0'):
        raise ValueError('Unsupported EPA definition')
    if off['observed']['includedGameIds'] != [GAME] or defense['observed']['includedGameIds'] != [GAME]:
        raise ValueError('EPA game scope mismatch')
    foundation = off['subject']['foundation']
    eligible = [r for r in rows if r['posteam'] == off['subject']['team'] and r['play_type'] in ('pass', 'run') and
                all(r[c] == 0 for c in ('qb_kneel', 'qb_spike', 'play_deleted', 'special_teams_play', 'two_point_attempt')) and
                (foundation == 'general' or r['play_type'] == ('pass' if foundation == 'classified_pass' else 'run'))]
    defense_units = [r for r in rows if r['defteam'] == defense['subject']['team'] and r['play_type'] in ('pass', 'run') and
                     all(r[c] == 0 for c in ('qb_kneel', 'qb_spike', 'play_deleted', 'special_teams_play', 'two_point_attempt')) and
                     (foundation == 'general' or r['play_type'] == ('pass' if foundation == 'classified_pass' else 'run'))]
    if [key(r) for r in defense_units] != [key(r) for r in eligible] or any(
            m['sourceRevisionIds'] != [RAW_HASH] for o in (off, defense) for m in o['members']):
        raise ValueError('EPA opponent-defense units/source mismatch')
    finite = [r for r in eligible if r['epa'] is not None and isfinite(r['epa'])]
    total = sum((Fraction(str(r['epa'])) for r in finite), Fraction())
    v = off['values']['epa']
    if v is None or Fraction(str(v['numerator'])) != total or v['denominator'] != len(finite) or off['totals']['eligibleN'] != len(eligible):
        raise ValueError('EPA raw sum/denominator mismatch')
    desc = descriptor(off['observationId'], 'epa', off['subject']['team'], off['definition'],
                      off['definition']['populationVersion'], 'finite-epa-play', 'epa', v['numerator'], v['denominator'],
                      'AVAILABLE' if v['denominator'] else 'NO_OPPORTUNITIES', [key(r) for r in finite], [GAME])
    # Foundation must be part of the definition for operation compatibility.
    desc['definition'] = {**off['definition'], 'foundation': foundation}
    return dict(foundation=foundation, originalObservation=off, opponentDefenseObservation=defense,
                descriptor=desc, display=decision('display', [desc]), eligibleUnitIds=[key(r) for r in eligible],
                finiteEpaUnitIds=[key(r) for r in finite], source=dict(hash=RAW_HASH, column='epa', numeric='Decimal(str(Float64))'),
                equality=dict(verified=True, sameEvidence=True, independentConfirmation=False,
                              offenseObservationId=off['observationId'], defenseObservationId=defense['observationId']))


def market_inventory(temporal):
    """Inventory only the preserved schedule bytes used for this calculation."""
    c = next(c for c in temporal['calculations'] if c['game']['game_id'] == GAME)
    inputs = [i for i in c['original']['manifest']['inputs'] if i['kind'] == 'calendar']
    resources = {r['revision_id']: r for r in temporal['resources'] if r['kind'] == 'FILE'}
    sources = []
    values = []
    for i in inputs:
        r = resources[i['source_revision_id']]
        b = base64.b64decode(r['payload']['bytes_base64'], validate=True)
        if digest(b) != i['source_revision_id']:
            raise ValueError('Schedule source mismatch')
        df = pl.read_parquet(BytesIO(b))
        fields = [x for x in ('home_moneyline', 'away_moneyline', 'spread_line', 'total_line', 'odds_timestamp', 'odds_provider', 'gameday', 'gametime') if x in df.columns]
        matches = df.filter(pl.col('game_id') == GAME).select(['game_id', *fields]).to_dicts()
        if len(matches) != 1:
            raise ValueError('Ambiguous schedule game')
        values.append(matches[0]); sources.append(dict(sourceRevisionId=i['source_revision_id'], origin=r['payload']['origin'], inspectedColumns=fields))
    odds = any(any(v.get(k) is not None for k in ('home_moneyline', 'away_moneyline', 'spread_line', 'total_line')) for v in values)
    return dict(scope='PRESERVED_SCHEDULE_INPUTS_ONLY', status='OBSERVED_QUOTES_TEMPORAL_UNKNOWN' if odds else 'NO_QUOTES_IN_PRESERVED_INPUTS',
                sources=sources, records=values, historicalAvailability='UNKNOWN', captureTime='UNKNOWN', provider='UNKNOWN',
                preKickoffOrClosingClaimAllowed=False, reasonCodes=['QUOTE_CAPTURE_AND_PROVIDER_NOT_DEMONSTRATED'],
                limitations=['Não inventariou serviços externos, banco ou odds novas; data do jogo não demonstra instante da cotação.'])


def project(sit, ledger, observations, temporal, raw, request, policy_text, receipt, definitions_text):
    rows = pl.read_parquet(raw).sort('game_id', 'order_sequence').to_dicts()
    by_play = {key(r): r for r in rows}
    if len(by_play) != len(rows):
        raise ValueError('Ambiguous raw identities')
    pilot_rows = [r for r in rows if r['game_id'] == GAME]
    docs = {d['id']: d for d in sit['documents']}
    productions = []
    for team, opponent in (('NYJ', 'TEN'), ('TEN', 'NYJ')):
        d, mirror = docs[team+'/off/1'], docs[opponent+'/def/1']
        if d['games'][0]['gameId'] != GAME or any(d[f] != mirror[f] for f in ('third', 'redZone')):
            raise ValueError('Situational offense/opponent-defense mismatch')
        thirds = []
        for u in ledger['third']:
            if u['id'] not in d['third']['unitIds']:
                continue
            r = by_play[u['id']]
            thirds.append(dict(**u, playId=r['play_id'], yardsToGo=r['ydstogo'], sourceOrder=r['order_sequence']))
        campaigns = []
        for u in ledger['campaigns']:
            if u['id'] not in d['redZone']['unitIds']:
                continue
            rs = [by_play[p] for p in u['playIds']]
            ev = lambda ids: [{k: by_play[p][k] for k in EVIDENCE_FIELDS} for p in ids]
            # Pilot terminal evidence is TD or FG; keep the full chronological drive too.
            terminal = [r for r in rs if r['play_type'] == 'field_goal' or key(r) in u['touchdownPlayIds']]
            campaigns.append(dict(**u, fixedDrive=rs[0]['fixed_drive'], sourceOrder=rs[0]['order_sequence'],
                                  entryEvidence=ev(u['entryPlayIds']), outcomeEvidence=ev([key(r) for r in terminal]),
                                  chronologicalPlayIds=[key(r) for r in sorted(rs, key=lambda r: r['order_sequence'])]))
        thirds.sort(key=lambda u: u['sourceOrder']); campaigns.sort(key=lambda u: u['sourceOrder'])
        metrics = {}
        for f in ('third', 'redZone'):
            desc = situational_descriptor(d, f)
            metrics[f] = dict(observation=d[f], observationRef=d['id']+'/'+f, descriptor=desc, display=decision('display', [desc]))
        long = situational_descriptor(d, 'third', 'long')
        long['unitIds'] = [u['id'] for u in thirds if u['distance'] == 'long']
        metrics['thirdLong'] = dict(descriptor=long, display=decision('display', [long]))
        joint = [dict(distance=b, kind=k, numerator=sum(u['converted'] for u in thirds if u['distance']==b and u['kind']==k),
                      denominator=sum(u['distance']==b and u['kind']==k for u in thirds),
                      unitIds=[u['id'] for u in thirds if u['distance']==b and u['kind']==k])
                 for b in ('short', 'medium', 'long', 'unknown') for k in ('pass', 'run')]
        epa = []
        for foundation in ('general', 'classified_pass', 'classified_rush'):
            def pick(t, role):
                selected = [o for o in observations if o['subject'] == dict(team=t, role=role, foundation=foundation) and
                            o['request']['season']==2026 and o['request']['phase']=='REG' and o['request']['period']['weeks']==[1]]
                if len(selected) != 1:
                    raise ValueError('EPA nominal observation not unique')
                return selected[0]
            epa.append(epa_projection(pick(team, 'off'), pick(opponent, 'def'), pilot_rows))
        productions.append(dict(offense=team, defense=opponent, label=team+' com a bola', gameId=GAME, metrics=metrics,
                                thirdAttempts=thirds, redZoneCampaigns=campaigns, thirdDistanceByType=joint, epa=epa,
                                orderDefinition='Within this game: ascending original order_sequence; campaign: first source event',
                                opponentDefenseEquality=dict(documentId=mirror['id'], verified=True, sameEvidence=True, independentConfirmation=False)))
    comparisons = {}
    for name in ('third', 'thirdLong', 'redZone', 'general', 'classified_pass', 'classified_rush'):
        ds = [p['metrics'][name]['descriptor'] if name in p['metrics'] else next(e['descriptor'] for e in p['epa'] if e['foundation']==name) for p in productions]
        side, diff = decision('sideBySide', ds), decision('difference', ds)
        comparisons[name] = dict(sideBySide=side, difference=diff,
                                 differenceAminusB=exact(fraction(ds[0])-fraction(ds[1])) if diff['allowed'] else None,
                                 participants=['NYJ', 'TEN'])
    league = {}
    candidates = sorted({g[k] for g in sit['games'] if g['week']==1 for k in ('home', 'away')})
    for family in ('third', 'redZone'):
        inventory, points, descs = [], [], []
        for team in candidates:
            d = docs[team+'/off/1']; desc = situational_descriptor(d, family)
            display = decision('display', [desc])
            represented = display['allowed'] and desc['status']=='AVAILABLE'
            item = dict(team=team, perspective='off', observationId=desc['id'], gameIds=desc['gameIds'],
                        numerator=desc['numerator'], denominator=desc['denominator'], status=desc['status'],
                        ratio=dict(numerator=desc['numerator'], denominator=desc['denominator']) if represented else None,
                        unitIds=desc['unitIds'], includedInRateDistribution=represented,
                        reasonCodes=[] if represented else ['ZERO_ELIGIBLE_OPPORTUNITIES'] if desc['status']=='NO_OPPORTUNITIES' else display['reasonCodes'])
            inventory.append(item)
            if represented:
                points.append(item); descs.append(desc)
        permission = decision('leagueReference', descs)
        if not permission['allowed']:
            raise ValueError('Invalid league reference: '+str(permission['reasonCodes']))
        league[family] = dict(season=2026, phase='REG', weeks=[1], definition=descs[0]['definition'], population=descs[0]['population'],
                              candidateTeams=candidates, representedTeams=[p['team'] for p in points], teamsWithoutRate=[p for p in inventory if not p['includedInRateDistribution']],
                              inventory=inventory, teamRateDistribution=dict(unit='ONE_OFFENSIVE_TEAM_RATE', points=points),
                              pooledRate=dict(numerator=sum(p['numerator'] for p in points), denominator=sum(p['denominator'] for p in points),
                                              method='SUM_NUMERATORS_OVER_SUM_DENOMINATORS'),
                              permission=permission, guarantees=GUARANTEES, pilotTeamsIncluded=['NYJ','TEN'],
                              pilotIndependentOfReference=False, limitations=LIMITS)
    facts = []
    def fact(id_, metric, text, entries, permission):
        if permission['allowed']:
            facts.append(dict(id=id_, metric=metric, scope=dict(season=2026, phase='REG', weeks=[1], gameIds=[GAME]),
                              text=text, participants=['NYJ','TEN'], evidence=[dict(observationId=e['id'], numerator=e['numerator'], denominator=e['denominator'], unitIds=e['unitIds']) for e in entries],
                              permission=permission, limitations=LIMITS+['NO_SCORE_CAUSAL_EXPLANATION']))
    for metric in ('third', 'thirdLong', 'redZone'):
        ds=[p['metrics'][metric]['descriptor'] for p in productions]
        perm=comparisons[metric]['difference']
        if metric=='third':
            winner='NYJ' if fraction(ds[0])>fraction(ds[1]) else 'TEN' if fraction(ds[1])>fraction(ds[0]) else None
            if winner: fact('third-observed-rate','third',winner+' teve maior taxa observada de conversão geral em terceiras.',ds,perm)
        elif metric=='thirdLong' and ds[0]['numerator']==ds[1]['numerator'] and ds[0]['denominator']==ds[1]['denominator']:
            fact('long-third-equal','thirdLong',f"Ambos converteram {ds[0]['numerator']} de {ds[0]['denominator']} terceiras de 7+ jardas observadas.",ds,perm)
        elif metric=='redZone' and ds[0]['numerator']>ds[1]['numerator'] and fraction(ds[0])<fraction(ds[1]):
            count=ds[1]['denominator']
            volume='uma única oportunidade' if count==1 else f'{count} oportunidades'
            fact('red-zone-count-and-rate','redZone',f"NYJ marcou mais TDs nas campanhas de red zone observadas; TEN teve maior taxa em {volume}.",ds,perm)
    return dict(contractVersion=VERSION, projectionVersion='1.0.0', request=request,
                policy=dict(version=POLICY, document=policy_text, interpretation='OBSERVED_SAMPLE_DESCRIPTIVE'),
                definitions=dict(document=definitions_text, situational=dict(definitionsVersion=sit['definitionsVersion'], calculationVersion=sit['calculationVersion']),
                                 epa=dict(definitionVersion='1.0.0', populationVersion='classified-scrimmage-v1', adapterVersion='1.0.0', model='UNKNOWN')),
                sources=dict(situationalBundleId=SITUATIONAL_PIN, observationBundleId=OBSERVATION_PIN, pbpHash=RAW_HASH, receipt=receipt,
                             packageRelativePaths=dict(situational='sources/situational', observations='sources/observations')),
                game=dict(gameId=GAME, season=2026, phase='REG', weeks=[1], offenses=['NYJ','TEN']),
                guarantees=GUARANTEES, productions=productions, comparisons=comparisons, leagueReferences=league, facts=facts,
                temporalContext=dict(mode='RETROSPECTIVE', previousRegularSeasonGames=dict(status='NOT_APPLICABLE', reason='W1_HAS_NO_EARLIER_REGULAR_SEASON_WEEKS_IN_THIS_SCOPE', weeks=[]),
                                     w2ContextAllowed=False, historicalAvailability='UNKNOWN', pregameKnowledge='UNKNOWN'),
                market=market_inventory(temporal), unavailableOperations=[dict(operation=o, reason=r) for o,r in (
                    ('epaLeagueReference','OUT_OF_SCOPE_AND_MODEL_UNKNOWN'),('qualitySuperiority','COUNTS_DO_NOT_ESTABLISH_ABILITY'),
                    ('prediction','NO_MODEL_OR_TEMPORAL_GUARANTEE'),('causalScoreExplanation','NO_CAUSAL_EVIDENCE'),
                    ('preKickoffOrClosingMarket','QUOTE_TEMPORAL_EVIDENCE_UNKNOWN'))], limitations=LIMITS)
