"""Calendar-driven projection with original unit classifiers and exact arithmetic."""
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from math import isfinite

import polars as pl

from ..seasons import normalize_seasons
from ..situational import FIELDS, campaign, third, measure, scrimmage, encoded, digest, play_key
from ..offline_metrics.population import exclusion_reason
from ..matchup_w12.project import terminal_evidence, EVIDENCE_FIELDS
from ..redzone_epa.project import production as redzone_production, aggregate as redzone_aggregate, GUARANTEES
from . import VERSION, POLICY, WEEKS, SEASON
from .policy import decision, fraction, LIMITS

FOUNDATIONS = ('general', 'classified_pass', 'classified_rush')
VALID = ('AVAILABLE', 'NO_OPPORTUNITIES')
DEFINITION = '''# Definições preservadas · W1–7
EPA: classified-scrimmage-v1, passe/corrida com flags válidas; sacks no passe, scrambles na corrida.
Soma exata de Decimal(str(Float64)) / jogadas com EPA finito. Ausentes e não finitos não viram zero.
Terceiras: situational-1.0.0; tentativas elegíveis com flags de conversão/falha atômicas.
Flags contraditórias impedem a taxa completa. Ajoelhadas, spikes, anuladas e abortadas excluídas.
Red zone: campanha fixed_drive com entrada observada antes de scrimmage em 0 < yardline_100 <= 20,
contada uma vez, com desfecho cronológico demonstrado. TDs ofensivos / campanhas elegíveis.
EPA da red zone: classified-scrimmage-redzone-start-v1, jogadas elegíveis que começam em 0 < posição <= 20.
Não é EPA por campanha e não usa o denominador da taxa de TDs. Chutes não entram no EPA.
Time: união de jogos do calendário em W1–7. Folga não é componente nem ausência.
Componente ausente/insuficiente impede a taxa agregada; sem oportunidades é 0/0, sem taxa.
Liga: uma taxa ofensiva definida por participante da mesma semana; folgas fora do universo.
Posições descritivas pela razão exata (empates 1,2,2,4); não medem qualidade ou previsão.
Completude, cobertura esperada, modelo EPA e disponibilidade histórica: UNKNOWN.
'''
POLICY_TEXT = '''Comparações descritivas exigem mesma fonte, definição, unidade e período; valores AVAILABLE.
Subtração, fatos e liga exigem unidades distintas. Ataque e defesa adversária são a mesma evidência,
não confirmação independente. Uma página de jogo usa somente esse jogo e referência da própria semana.
Página do time identifica explicitamente o agregado inclusivo W1–7. Sem projeção pré-jogo, qualidade,
causalidade, significância ou modelo de machine learning. Mercado separado; instante/provedor UNKNOWN.
'''


def decimal(value):
    with localcontext() as ctx:
        ctx.prec = 150
        return format(Decimal(value.numerator) / Decimal(value.denominator), 'f')


def descriptor(id_, metric, team, n, den, status, units, game_ids, weeks, pbp_hash, ambiguous=()):
    epa = metric in FOUNDATIONS
    return dict(id=id_, metric='epa' if epa else metric, team=team, perspective='off', season=SEASON, phase='REG', weeks=weeks,
                definition=dict(version='classified-scrimmage-v1', foundation=metric) if epa else dict(version='situational-1.0.0', family=metric),
                population='classified-scrimmage-v1' if epa else 'third-eligible-1.0.0' if metric in ('third','thirdLong') else 'red-zone-campaign-1.0.0',
                unit='finite-epa-play' if epa else 'attempt' if metric in ('third','thirdLong') else 'campaign',
                sourceHash=pbp_hash, sourceColumn='epa' if epa else 'third_down_converted' if metric in ('third','thirdLong') else 'yardline_100+fixed_drive+terminal-events',
                numerator=n, denominator=den, status=status, unitIds=list(units), gameIds=game_ids, ambiguousIds=list(ambiguous),
                integrityVerified=True, provenanceVerified=True, guarantees=GUARANTEES)


def permission(operation, descriptors):
    p = decision('display' if operation == 'aggregate' else operation, descriptors)
    return {**p, 'operation': operation}


def epa(rows, team, game, foundation, pbp_hash, source_present):
    candidates = [r for r in rows if r['posteam']==team and (foundation=='general' or r['play_type']==('pass' if foundation=='classified_pass' else 'run'))]
    unknown = [play_key(r) for r in candidates if exclusion_reason(r)=='unknown_filter_flags']
    eligible = [r for r in candidates if exclusion_reason(r) is None]
    finite = [r for r in eligible if r['epa'] is not None and isfinite(r['epa'])]
    total = sum((Fraction(str(r['epa'])) for r in finite), Fraction())
    status = 'SOURCE_ABSENT' if not source_present else 'INSUFFICIENT' if unknown or eligible and not finite else 'AVAILABLE' if finite else 'NO_OPPORTUNITIES'
    id_ = f"{game['gameId']}/{team}/{foundation}"
    d = descriptor(id_,foundation,team,decimal(total),len(finite),status,[play_key(r) for r in finite],[game['gameId']],[game['week']],pbp_hash,unknown)
    totals=dict(eligibleN=len(eligible),epaN=len(finite),epaMissingN=sum(r['epa'] is None for r in eligible),epaNonfiniteN=sum(r['epa'] is not None and not isfinite(r['epa']) for r in eligible),epaSum=decimal(total))
    original=dict(observationId=id_, subject=dict(team=team,role='off',foundation=foundation),
                  values=dict(epa=dict(numerator=decimal(total),denominator=len(finite)) if status=='AVAILABLE' else None),totals=totals,presentation=dict(epaDecimals=3))
    return dict(foundation=foundation,descriptor=d,display=decision('display',[d]),originalObservation=original,
                eligibleUnitIds=[play_key(r) for r in eligible],finiteEpaUnitIds=d['unitIds'])


def metric(units, family, team, game, pbp_hash, present):
    obs=measure(units,family)
    if not present: obs.update(status='SOURCE_ABSENT', ratio=None)
    d=descriptor(f"{game['gameId']}/{team}/{family}",family,team,obs['numerator'],obs['denominator'],obs['status'],obs['unitIds'],[game['gameId']],[game['week']],pbp_hash,obs['ambiguousIds'])
    return dict(observation=obs,descriptor=d,display=decision('display',[d]))


def joint(attempts):
    return [dict(distance=b,kind=k,numerator=sum(u['converted'] for u in attempts if u['distance']==b and u['kind']==k),denominator=sum(u['distance']==b and u['kind']==k for u in attempts),unitIds=[u['id'] for u in attempts if u['distance']==b and u['kind']==k]) for b in ('short','medium','long','unknown') for k in ('pass','run')]


def game_productions(game, rows, pbp_hash):
    present=bool(rows);by_play={play_key(r):r for r in rows}
    thirds=[third(r) for r in rows if r['down']==3]
    grouped=defaultdict(list);blocks=[]
    for r in rows:
        grouped[r['fixed_drive']].append(r)
        if not blocks or blocks[-1]!=r['fixed_drive']:blocks.append(r['fixed_drive'])
    reopened={d for d,n in Counter(blocks).items() if n>1}
    campaigns=[campaign(rs,set()) for rs in grouped.values()]
    for u in campaigns:
        if any(u['id']==f"{game['gameId']}:drive:{d}" for d in reopened):u.update(included=False,uncertain=True,reason='INSUFFICIENT_CAMPAIGN')
    productions=[]
    for team,opponent in ((game['away'],game['home']),(game['home'],game['away'])):
        ts=[u for u in thirds if u['offense']==team];cs=[u for u in campaigns if u['offense']==team]
        metrics={f:metric(us,f,team,game,pbp_hash,present) for us,f in ((ts,'third'),(cs,'redZone'))}
        long=metric([u for u in ts if u['distance']=='long'],'third',team,game,pbp_hash,present)
        long['descriptor'].update(id=long['descriptor']['id']+'/long',metric='thirdLong',definition=dict(version='situational-1.0.0',family='thirdLong'))
        long['display']=decision('display',[long['descriptor']]);metrics['thirdLong']=long
        attempts=[dict(**u,playId=by_play[u['id']]['play_id'],yardsToGo=by_play[u['id']]['ydstogo'],sourceOrder=by_play[u['id']]['order_sequence']) for u in ts if u['included']]
        marks=[]
        for u in cs:
            if not u['included']:continue
            rs=[by_play[p] for p in u['playIds']];terminal=terminal_evidence(rs,u['outcome'])
            ev=lambda ids:[{k:by_play[p][k] for k in EVIDENCE_FIELDS} for p in ids]
            marks.append(dict(**u,fixedDrive=rs[0]['fixed_drive'],sourceOrder=rs[0]['order_sequence'],entryEvidence=ev(u['entryPlayIds']),outcomeEvidence=ev([play_key(r) for r in terminal]),chronologicalPlayIds=u['playIds']))
        productions.append(dict(offense=team,defense=opponent,label=team+' com a bola',gameId=game['gameId'],metrics=metrics,
                                 epa=[epa(rows,team,game,f,pbp_hash,present) for f in FOUNDATIONS],thirdAttempts=attempts,
                                 redZoneCampaigns=sorted(marks,key=lambda u:u['sourceOrder']),thirdDistanceByType=joint(attempts)))
    return productions,dict(third=thirds,campaigns=campaigns)


def comparisons(productions, aggregate=False):
    out={}
    for name in ('third','redZone',*FOUNDATIONS,*(() if aggregate else ('thirdLong',))):
        ds=[p['metrics'][name]['descriptor'] if name in p['metrics'] else next(e['descriptor'] for e in p['epa'] if e['foundation']==name) for p in productions]
        side=decision('sideBySide',ds);diff=decision('difference',ds)
        delta=fraction(ds[0])-fraction(ds[1]) if diff['allowed'] else None
        out[name]=dict(sideBySide=side,difference=diff,differenceAminusB=None if delta is None else dict(numerator=str(delta.numerator),denominator=delta.denominator))
    return out


def league(documents, week, family, teams):
    inventory=[];descs=[]
    for d in documents.values():
        if d['game']['weeks']!=[week]:continue
        for p in d['productions']:
            desc=p['metrics'][family]['descriptor'];represented=desc['status']=='AVAILABLE' and decision('display',[desc])['allowed']
            item=dict(team=p['offense'],perspective='off',observationId=desc['id'],gameIds=desc['gameIds'],numerator=desc['numerator'],denominator=desc['denominator'],status=desc['status'],ratio=dict(numerator=desc['numerator'],denominator=desc['denominator']) if represented else None,unitIds=desc['unitIds'],includedInRateDistribution=represented,reasonCodes=[] if represented else [desc['status']])
            inventory.append(item)
            if represented:descs.append(desc)
    inventory.sort(key=lambda p:p['team']);points=[p for p in inventory if p['includedInRateDistribution']]
    candidates=[p['team'] for p in inventory]
    return dict(season=SEASON,phase='REG',weeks=[week],population=descs[0]['population'] if descs else family,
                candidateTeams=candidates,byeTeams=sorted(set(teams)-set(candidates)),representedTeams=[p['team'] for p in points],inventory=inventory,
                teamsWithoutRate=[p for p in inventory if not p['includedInRateDistribution']],teamRateDistribution=dict(points=points),
                pooledRate=dict(numerator=sum(p['numerator'] for p in points),denominator=sum(p['denominator'] for p in points),method='SUM_NUMERATORS_OVER_SUM_DENOMINATORS'),
                permission=decision('leagueReference',descs),participantsIncluded=[],participantsIndependentOfReference=False)


def facts(productions,game):
    out=[]
    for family in ('third','thirdLong','redZone'):
        ds=[p['metrics'][family]['descriptor'] for p in productions];perm=decision('editorialFact',ds)
        if not perm['allowed']:continue
        i=int(fraction(ds[1])>fraction(ds[0]));j=1-i;equal=fraction(ds[0])==fraction(ds[1])
        name={'third':'conversão em terceiras','thirdLong':'conversão em terceiras de 7+ jardas','redZone':'TDs por campanha de red zone'}[family]
        text=(f"{productions[i]['offense']} teve maior taxa observada de {name}: {ds[i]['numerator']}/{ds[i]['denominator']}, frente a {ds[j]['numerator']}/{ds[j]['denominator']} de {productions[j]['offense']}." if not equal else f"{productions[0]['offense']} e {productions[1]['offense']} tiveram a mesma taxa observada de {name}: {ds[0]['numerator']}/{ds[0]['denominator']} e {ds[1]['numerator']}/{ds[1]['denominator']}.")
        if family=='redZone':text += ' Contagem e taxa descrevem esta amostra, não qualidade futura.'
        out.append(dict(id=family+'-observed',metric=family,text=text,participants=[p['offense'] for p in productions],scope=dict(season=SEASON,phase='REG',weeks=[game['week']],gameIds=[game['gameId']]),evidence=[dict(observationId=d['id'],numerator=d['numerator'],denominator=d['denominator'],unitIds=d['unitIds']) for d in ds],permission=perm,limitations=LIMITS))
    return out


def aggregated_descriptor(parts,team,role,name,games,pbp_hash):
    units=[u for p in parts for u in p['unitIds']]
    if len(set(units))!=len(units):raise ValueError('Duplicate aggregate units')
    if len(parts)!=len(games) or [g for p in parts for g in p['gameIds']]!=games:raise ValueError('Missing or wrong scheduled component')
    for field in ('metric','definition','population','unit','sourceHash','sourceColumn','season','phase'):
        if any(p[field]!=parts[0][field] for p in parts):raise ValueError('Incompatible aggregate component '+field)
    status='SOURCE_ABSENT' if any(p['status']=='SOURCE_ABSENT' for p in parts) else 'INSUFFICIENT' if any(p['status'] not in VALID for p in parts) else 'AVAILABLE' if sum(p['denominator'] for p in parts) else 'NO_OPPORTUNITIES'
    n=sum((Fraction(str(p['numerator'])) for p in parts),Fraction());den=sum(p['denominator'] for p in parts)
    d=descriptor(f"{team}/{role}/1-7/{name}",name,team,decimal(n) if name in FOUNDATIONS else int(n),den,status,units,games,WEEKS,pbp_hash,[a for p in parts for a in p['ambiguousIds']])
    d['perspective']=role
    if status not in VALID:d.update(numerator=None,denominator=None)
    return d


def team_document(team,games,documents,pbp_hash):
    members=[g for g in games if team in (g['away'],g['home'])];ids=[g['gameId'] for g in members];productions=[]
    for role in ('off','def'):
        parts=[next(p for p in documents[g['gameId']]['productions'] if p['offense' if role=='off' else 'defense']==team) for g in members]
        attempts=[u for p in parts for u in p['thirdAttempts']];campaigns=[u for p in parts for u in p['redZoneCampaigns']];metrics={}
        for family in ('third','redZone'):
            ms=[p['metrics'][family] for p in parts];d=aggregated_descriptor([m['descriptor'] for m in ms],team,role,family,ids,pbp_hash)
            obs=dict(exclusions=dict(sum((Counter(m['observation']['exclusions']) for m in ms),Counter())))
            if family=='third':
                obs.update(byDistance={b:dict(numerator=sum(u['converted'] for u in attempts if u['distance']==b),denominator=sum(u['distance']==b for u in attempts)) for b in ('short','medium','long','unknown')},byType={k:dict(numerator=sum(u['converted'] for u in attempts if u['kind']==k),denominator=sum(u['kind']==k for u in attempts)) for k in ('pass','run')})
            else:obs['outcomes']=dict(Counter(u['outcome'] for u in campaigns))
            metrics[family]=dict(descriptor=d,display=decision('display',[d]),aggregation=permission('aggregate',[d]),components=ms,observation=obs)
        epas=[]
        for f in FOUNDATIONS:
            es=[next(e for e in p['epa'] if e['foundation']==f) for p in parts];d=aggregated_descriptor([e['descriptor'] for e in es],team,role,f,ids,pbp_hash)
            totals={k:sum(e['originalObservation']['totals'][k] for e in es) for k in ('eligibleN','epaN','epaMissingN','epaNonfiniteN')};totals['epaSum']=decimal(sum((Fraction(e['originalObservation']['totals']['epaSum']) for e in es),Fraction()))
            orig=dict(observationId=d['id'],subject=dict(team=team,role=role,foundation=f),values=dict(epa=dict(numerator=d['numerator'],denominator=d['denominator']) if d['status']=='AVAILABLE' else None),totals=totals,presentation=dict(epaDecimals=3))
            epas.append(dict(descriptor=d,foundation=f,originalObservation=orig,calculatedTotals=totals,display=decision('display',[d]),aggregation=permission('aggregate',[d]),components=es,eligibleUnitIds=[u for e in es for u in e['eligibleUnitIds']],finiteEpaUnitIds=d['unitIds']))
        components=[dict(gameId=g['gameId'],week=g['week'],offense=p['offense'],defense=p['defense'],sourceDocumentHash=g['documentHash'],production=p) for g,p in zip(members,parts)]
        productions.append(dict(team=team,perspective=role,label=team+' com a bola' if role=='off' else 'Adversários contra '+team,opponents=[p['defense' if role=='off' else 'offense'] for p in parts],gameIds=ids,components=components,metrics=metrics,epa=epas,thirdAttempts=attempts,redZoneCampaigns=campaigns,thirdDistanceByType=joint(attempts)))
    team_facts=[]
    for family,label in (('third','terceiras descidas'),('redZone','campanhas de red zone')):
        d=productions[0]['metrics'][family]['descriptor'];perm=decision('display',[d])
        if d['status']=='AVAILABLE' and perm['allowed']:
            team_facts.append(dict(text=f"{team}: {d['numerator']} {'conversões' if family=='third' else 'TDs ofensivos'} em {d['denominator']} {label} observadas em W1–7 ({len(members)} jogos).",observationId=d['id'],numerator=d['numerator'],denominator=d['denominator'],unitIds=d['unitIds'],permission=perm))
    return dict(contractVersion=VERSION,projectionVersion='1.0.0',scope=dict(team=team,season=SEASON,phase='REG',weeks=WEEKS),games=members,byeWeeks=sorted(set(WEEKS)-{g['week'] for g in members}),productions=productions,comparisons=comparisons(productions,True),facts=team_facts,definitions=dict(document=DEFINITION),policy=dict(version=POLICY,document=POLICY_TEXT),guarantees=GUARANTEES,sources=dict(pbpHash=pbp_hash),limitations=LIMITS)


def derive(source):
    normalize_seasons([SEASON])
    raw=pl.read_parquet(source/'pbp.parquet');schedule=pl.read_parquet(source/'schedules.parquet')
    if set(FIELDS+['epa','special_teams_play'])-set(raw.columns):raise ValueError('Missing PBP schema')
    rows=raw.filter((pl.col('season')==SEASON)&(pl.col('season_type')=='REG')&pl.col('week').is_in(WEEKS)).sort('game_id','order_sequence').to_dicts()
    ss=schedule.filter((pl.col('season')==SEASON)&(pl.col('game_type')=='REG')&pl.col('week').is_in(WEEKS)).sort('week','gameday','game_id').to_dicts()
    if not ss or len({s['game_id'] for s in ss})!=len(ss):raise ValueError('Empty or duplicate calendar')
    pbp_hash=digest((source/'pbp.parquet').read_bytes());schedule_hash=digest((source/'schedules.parquet').read_bytes())
    by_game=defaultdict(list)
    for r in rows:by_game[r['game_id']].append(r)
    if set(by_game)-{s['game_id'] for s in ss}:raise ValueError('PBP outside selected calendar')
    if len({play_key(r) for r in rows})!=len(rows):raise ValueError('Duplicate raw play identities')
    games=[];documents={};ledgers={};rz_games={}
    for s in ss:
        trio=[s['away_score'],s['home_score'],s['result']]
        if not (all(v is None for v in trio) or all(isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v) and int(v)==v for v in trio) and min(trio[:2])>=0 and trio[2]==trio[1]-trio[0]):raise ValueError('Invalid atomic score trio')
        g=dict(gameId=s['game_id'],season=SEASON,phase='REG',week=s['week'],away=s['away_team'],home=s['home_team'],gameday=s['gameday'],awayScore=s['away_score'],homeScore=s['home_score'],result=s['result'],calendarSourceHash=schedule_hash,calendarOrigin='nflverse-data/releases/schedules/games.parquet')
        rs=by_game[g['gameId']]
        if any((r['season'],r['season_type'],r['week'],r['away_team'],r['home_team'])!=(SEASON,'REG',g['week'],g['away'],g['home']) for r in rs):raise ValueError('PBP/calendar context mismatch')
        if any(r['posteam'] not in (g['away'],g['home']) or r['defteam'] not in (g['away'],g['home']) or r['posteam']==r['defteam'] for r in rs if scrimmage(r)):raise ValueError('Unattributed scrimmage')
        pp,ledger=game_productions(g,rs,pbp_hash);ledgers[g['gameId']]=ledger
        quote={k:s.get(k) for k in ('away_moneyline','home_moneyline','spread_line','total_line')}
        documents[g['gameId']]=dict(contractVersion=VERSION,projectionVersion='1.0.0',game=dict(gameId=g['gameId'],season=SEASON,phase='REG',weeks=[g['week']],offenses=[g['away'],g['home']],away=g['away'],home=g['home']),calendar=deepcopy(g),productions=pp,comparisons=comparisons(pp),facts=facts(pp,g),definitions=dict(document=DEFINITION),policy=dict(version=POLICY,document=POLICY_TEXT),guarantees=GUARANTEES,sources=dict(pbpHash=pbp_hash,scheduleHash=schedule_hash),temporalContext=dict(mode='RETROSPECTIVE',otherGamesContextAllowed=False,referenceWeeks=[g['week']],historicalAvailability='UNKNOWN',previousRegularSeasonGames=dict(status='NOT_APPLICABLE' if g['week']==1 else 'OUT_OF_SCOPE',reason='THIS_GAME_ONLY',weeks=[])),market=dict(status='OBSERVED_QUOTES_TEMPORAL_UNKNOWN',records=[quote],sources=[dict(sourceRevisionId=schedule_hash,origin=g['calendarOrigin'])],captureTime='UNKNOWN',provider='UNKNOWN',preKickoffOrClosingClaimAllowed=False),unavailableOperations=[dict(operation='prediction',reason='NO_MODEL'),dict(operation='epaLeagueReference',reason='MODEL_UNKNOWN')])
        rz=[]
        for team,opponent in ((g['away'],g['home']),(g['home'],g['away'])):
            p=redzone_production(rs,team,opponent,g['gameId'],g['week'])
            if not rs:p.update(status='SOURCE_ABSENT',mean=None)
            rz.append(p)
        rz_games[g['gameId']]=dict(gameId=g['gameId'],week=g['week'],away=g['away'],home=g['home'],productions=rz)
        games.append(g)
    teams=sorted({g[k] for g in games for k in ('away','home')});week_inventory=[]
    if len(teams)!=32:raise ValueError('Expected NFL 32-team identity inventory')
    for w in WEEKS:
        gs=[g for g in games if g['week']==w];counts=Counter(t for g in gs for t in (g['away'],g['home']))
        if not gs or any(n!=1 for n in counts.values()):raise ValueError('Duplicate or empty participant/week')
        week_inventory.append(dict(week=w,games=len(gs),participants=sorted(counts),byes=sorted(set(teams)-set(counts)),pbpGames=sum(bool(by_game[g['gameId']]) for g in gs)))
        refs={f:league(documents,w,f,teams) for f in ('third','redZone')}
        for g in gs:
            d=documents[g['gameId']];d['leagueReferences']={f:{**refs[f],'participantsIncluded':d['game']['offenses']} for f in refs}
    rz_teams={};team_docs={}
    for g in games:
        d=documents[g['gameId']];d['redzoneEpa']=rz_games[g['gameId']]
        g.update(path=f"games/{g['gameId']}.json",documentHash=digest(encoded(d)))
    for t in teams:
        team_docs[t]=team_document(t,games,documents,pbp_hash);members=[rz_games[g['gameId']] for g in games if t in (g['away'],g['home'])];pp=[]
        for role in ('off','def'):
            parts=[next(p for p in g['productions'] if p['offense' if role=='off' else 'defense']==t) for g in members]
            pp.append(dict(perspective=role,gameIds=[g['gameId'] for g in members],weeks=WEEKS,components=[dict(gameId=g['gameId'],week=g['week'],status=p['status'],validN=p['validN'],sum=p['sum'],mean=p['mean']) for g,p in zip(members,parts)],**redzone_aggregate(parts)))
        rz_teams[t]=dict(team=t,productions=pp);team_docs[t]['redzoneEpa']=rz_teams[t]
    index=dict(contractVersion=VERSION,projectionVersion='1.0.0',season=SEASON,phase='REG',weeks=WEEKS,weekInventory=week_inventory,games=games,teams=[dict(team=t,gameIds=[g['gameId'] for g in team_docs[t]['games']],path=f'teams/{t}.json',documentHash=digest(encoded(team_docs[t]))) for t in teams],counts=dict(games=len(games),offensiveProductions=2*len(games),teams=len(teams),rawRows=len(rows)),historicalAvailability='UNKNOWN',sources=dict(pbpHash=pbp_hash,scheduleHash=schedule_hash,receiptsHash=digest((source/'receipts.json').read_bytes())))
    files={g['path']:encoded(documents[g['gameId']]) for g in games}
    files.update({t['path']:encoded(team_docs[t['team']]) for t in index['teams']});files['index.json']=encoded(index);files['ledger.json']=encoded(ledgers)
    files['definitions.md']=DEFINITION.encode();files['policy.md']=POLICY_TEXT.encode()
    return index,files
