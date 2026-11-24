"""Independent raw audit of the new projection. No projector/policy imports.

The previous independent auditor first checks every preserved situational ledger
record against raw columns and terminal events. This audit independently groups
W1 raw records and verifies new unit enrichment, EPA, league and concrete facts.
"""
import argparse
import base64
from collections import Counter
from fractions import Fraction
from io import BytesIO
import hashlib
import json
from math import isfinite
from pathlib import Path
import subprocess
import sys

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
GAME = '2026_01_NYJ_TEN'


def sha(b):
    return 'sha256:'+hashlib.sha256(b).hexdigest()


def key(r):
    return f"{r['game_id']}:{int(r['play_id'])}"


def ratio(n, d):
    return dict(numerator=n, denominator=d)


def run(bundle, output):
    data = json.loads((bundle/'comparison.json').read_bytes())
    artifact_pin=sha((bundle/'comparison.json').read_bytes())
    assert json.loads((bundle/'COMPLETED.json').read_bytes())['bundleId']==artifact_pin
    src = bundle/'sources/situational'
    previous = output.with_name(output.stem+'-situational.json')
    subprocess.run([sys.executable, '-B', str(ROOT/'docs/plans/broadcast-situational-w12-v1/reconcile.py'),
                    '--bundle', str(src), '--output', str(previous)], check=True, stdout=subprocess.DEVNULL)
    assert json.loads(previous.read_bytes())['divergences'] == []
    raw = pl.read_parquet(src/'pbp.parquet').sort('game_id', 'order_sequence')
    assert sha((src/'pbp.parquet').read_bytes()) == 'sha256:4e3707397912babcd0d7d02abd3be95db8e66785250e62bf9d874f37229d895e'
    w1 = raw.filter((pl.col('season')==2026)&(pl.col('season_type')=='REG')&(pl.col('week')==1))
    games = w1.select('game_id','home_team','away_team').unique().to_dicts()
    candidate_teams = sorted({g[c] for g in games for c in ('home_team','away_team')})
    assert len(games)==16 and len(candidate_teams)==32
    assert Counter(g[c] for g in games for c in ('home_team','away_team'))==Counter({t:1 for t in candidate_teams})
    third = w1.filter((pl.col('down')==3)&pl.col('play_type').is_in(['pass','run'])&
                      pl.all_horizontal([pl.col(f)==0 for f in ['play_deleted','aborted_play','qb_kneel','qb_spike','extra_point_attempt','two_point_attempt']])&
                      pl.col('third_down_converted').is_in([0,1])&pl.col('third_down_failed').is_in([0,1])&
                      (pl.col('third_down_converted')+pl.col('third_down_failed')==1)).to_dicts()
    thirds = {key(r):r for r in third}
    campaigns = {}
    # Drive inclusion from positions, not source ledger or projected marks.
    for (gid, drive), group in w1.group_by('game_id','fixed_drive',maintain_order=True):
        rows = group.sort('order_sequence').to_dicts()
        scr = [r for r in rows if r['down'] in (1,2,3,4) and r['play_deleted']==0 and r['extra_point_attempt']==0 and r['two_point_attempt']==0 and
               r['play_type'] in ('pass','run','qb_kneel','qb_spike','punt','field_goal','no_play') and (r['play_type']!='no_play' or r['penalty']==1)]
        entries = [r for r in scr if 0<r['yardline_100']<=20]
        if not entries:
            continue
        assert len({(r['posteam'],r['defteam']) for r in scr})==1
        last=scr[-1]
        if last['play_type'] in ('pass','run') and last['touchdown']==1 and last['td_team']==last['posteam']:
            outcome='TOUCHDOWN'
        elif last['play_type']=='field_goal':
            outcome='FIELD_GOAL' if last['field_goal_result']=='made' else 'MISSED_FIELD_GOAL'
        elif last['play_type']=='punt':outcome='PUNT'
        elif last['touchdown']==1 and last['td_team']==last['defteam']:outcome='OPPONENT_TOUCHDOWN'
        elif last['interception']==1 or last['fumble_lost']==1:outcome='TURNOVER'
        elif last['safety']==1:outcome='SAFETY'
        elif last['down']==4 and last['fourth_down_failed']==1:outcome='DOWNS'
        else:
            assert any(r['desc'] in ('END GAME','END QUARTER 2','END QUARTER 4','END QUARTER 5') and r['game_seconds_remaining'] in (0,1800) for r in rows)
            outcome='END_HALF_GAME'
        campaigns[f'{gid}:drive:{drive}']=dict(rows=rows, entries=entries, last=last, offense=scr[0]['posteam'], defense=scr[0]['defteam'], outcome=outcome)
    assert (len(thirds),sum(int(r['third_down_converted']) for r in third))==(377,154)
    assert (len(campaigns),sum(d['outcome']=='TOUCHDOWN' for d in campaigns.values()))==(108,70)
    old = json.loads((bundle/'sources/observations/observations.json').read_bytes())
    sit = json.loads((src/'situational.json').read_bytes())
    ledger = json.loads((src/'ledger.json').read_bytes())
    docs = {d['id']:d for d in sit['documents']}
    ledger_third = {u['id']:u for u in ledger['third']}
    ledger_drive = {u['id']:u for u in ledger['campaigns']}
    joint_report={}; epa_report={}; marks=0; entry_evidence=0
    for prod in data['productions']:
        t, defense = prod['offense'], prod['defense']
        ts=[r for r in third if r['game_id']==GAME and r['posteam']==t]
        ds={k:d for k,d in campaigns.items() if d['rows'][0]['game_id']==GAME and d['offense']==t}
        assert prod['label']==t+' com a bola' and prod['gameId']==GAME
        assert [u['id'] for u in prod['thirdAttempts']]==[key(r) for r in ts]
        assert [u['id'] for u in prod['redZoneCampaigns']]==list(ds)
        for u in prod['thirdAttempts']:
            r=thirds[u['id']]
            assert u==dict(**ledger_third[u['id']],playId=r['play_id'],yardsToGo=r['ydstogo'],sourceOrder=r['order_sequence'])
            assert u['gameId']==GAME and (u['offense'],u['defense'])==(t,defense)
            marks+=1
        for u in prod['redZoneCampaigns']:
            d=ds[u['id']]; original=ledger_drive[u['id']]
            assert {k:u[k] for k in original}==original
            assert u['fixedDrive']==d['rows'][0]['fixed_drive'] and u['sourceOrder']==d['rows'][0]['order_sequence']
            assert u['outcome']==d['outcome'] and (u['offense'],u['defense'])==(t,defense)
            assert u['chronologicalPlayIds']==[key(r) for r in d['rows']]
            assert [key(r) for r in u['entryEvidence']]==[key(r) for r in d['entries']]
            for ev in u['entryEvidence']:
                r=next(r for r in d['entries'] if key(r)==key(ev));assert all(r[k]==v for k,v in ev.items());assert 0<ev['yardline_100']<=20
                entry_evidence+=1
            assert [key(r) for r in u['outcomeEvidence']]==[key(d['last'])]
            assert all(d['last'][k]==v for k,v in u['outcomeEvidence'][0].items())
            marks+=1
        long=[r for r in ts if r['ydstogo']>=7]
        expected={'third':ratio(sum(int(r['third_down_converted']) for r in ts),len(ts)),
                  'thirdLong':ratio(sum(int(r['third_down_converted']) for r in long),len(long)),
                  'redZone':ratio(sum(d['outcome']=='TOUCHDOWN' for d in ds.values()),len(ds))}
        for family,expected_ratio in expected.items():
            m=prod['metrics'][family];desc=m['descriptor']
            assert {k:desc[k] for k in expected_ratio}==expected_ratio and m['display']['allowed']
            assert len(desc['unitIds'])==desc['denominator']==len(set(desc['unitIds']))
        for family in ('third','redZone'):
            assert prod['metrics'][family]['observation']==docs[t+'/off/1'][family]==docs[defense+'/def/1'][family]
        for cell in prod['thirdDistanceByType']:
            rs=[r for r in ts if r['play_type']==cell['kind'] and ('short' if r['ydstogo']<=3 else 'medium' if r['ydstogo']<=6 else 'long')==cell['distance']]
            assert cell['unitIds']==[key(r) for r in rs]
            assert (cell['numerator'],cell['denominator'])==(sum(int(r['third_down_converted']) for r in rs),len(rs))
        for field,choices,col in [('byDistance',['short','medium','long','unknown'],'distance'),('byType',['pass','run'],'kind')]:
            for x in choices:
                cells=[c for c in prod['thirdDistanceByType'] if c[col]==x]
                assert ratio(sum(c['numerator'] for c in cells),sum(c['denominator'] for c in cells))==docs[t+'/off/1']['third'][field][x]
        joint_report[t]=prod['thirdDistanceByType']
        # EPA eligibility is independent of down, distance, campaign or aborted flag.
        epa_rows=w1.filter((pl.col('game_id')==GAME)&(pl.col('posteam')==t)&pl.col('play_type').is_in(['pass','run'])&
                           pl.all_horizontal([pl.col(f)==0 for f in ['qb_kneel','qb_spike','play_deleted','special_teams_play','two_point_attempt']])).to_dicts()
        for e in prod['epa']:
            f=e['foundation']; rs=[r for r in epa_rows if f=='general' or r['play_type']==('pass' if f=='classified_pass' else 'run')]
            allowed=w1.filter((pl.col('game_id')==GAME)&(pl.col('defteam')==defense)&pl.col('play_type').is_in(['pass','run'])&
                              pl.all_horizontal([pl.col(flag)==0 for flag in ['qb_kneel','qb_spike','play_deleted','special_teams_play','two_point_attempt']])).to_dicts()
            allowed=[r for r in allowed if f=='general' or r['play_type']==('pass' if f=='classified_pass' else 'run')]
            assert [key(r) for r in rs]==[key(r) for r in allowed]
            finite=[r for r in rs if r['epa'] is not None and isfinite(r['epa'])]
            total=sum((Fraction(str(r['epa'])) for r in finite),Fraction())
            o=e['originalObservation']; mirror=e['opponentDefenseObservation']
            assert o in old and mirror in old and o['totals']==mirror['totals'] and o['values']==mirror['values']
            assert o['subject']==dict(team=t,role='off',foundation=f) and mirror['subject']==dict(team=defense,role='def',foundation=f)
            assert e['eligibleUnitIds']==[key(r) for r in rs] and e['finiteEpaUnitIds']==[key(r) for r in finite]
            assert o['totals']['eligibleN']==len(rs) and o['totals']['epaN']==len(finite)
            assert o['totals']['epaMissingN']==sum(r['epa'] is None for r in rs)
            assert o['totals']['epaNonfiniteN']==sum(r['epa'] is not None and not isfinite(r['epa']) for r in rs)
            assert o['totals']['successN']==sum(r['epa']>0 for r in finite)
            assert Fraction(o['totals']['epaSum'])==total and o['values']['epa']['denominator']==len(finite)
            assert o['guarantees']['compatibility']['epaModel']['state']=='UNKNOWN'
            assert e['descriptor']['unitIds']==[key(r) for r in finite] and e['descriptor']['sourceColumn']=='epa'
            assert Fraction(e['descriptor']['numerator'])==total and e['descriptor']['denominator']==len(finite)
            epa_report[t+'/'+f]=dict(eligible=len(rs),finite=len(finite),sumNumerator=str(total.numerator),sumDenominator=total.denominator)
    assert [(p['metrics']['third']['descriptor']['numerator'],p['metrics']['third']['descriptor']['denominator']) for p in data['productions']]==[(2,10),(4,12)]
    assert [(p['metrics']['thirdLong']['descriptor']['numerator'],p['metrics']['thirdLong']['descriptor']['denominator']) for p in data['productions']]==[(1,5),(1,5)]
    assert [Counter(u['outcome'] for u in p['redZoneCampaigns']) for p in data['productions']]==[Counter(TOUCHDOWN=2,FIELD_GOAL=1),Counter(TOUCHDOWN=1)]
    refs={}
    for family,ref in data['leagueReferences'].items():
        assert ref['candidateTeams']==candidate_teams and ref['weeks']==[1] and ref['season']==2026 and ref['phase']=='REG'
        assert [p['team'] for p in ref['inventory']]==candidate_teams
        independent=[]
        all_ids=[]
        for item in ref['inventory']:
            t=item['team']
            sample=[r for r in third if r['posteam']==t] if family=='third' else [d for d in campaigns.values() if d['offense']==t]
            n=sum(int(r['third_down_converted']) for r in sample) if family=='third' else sum(d['outcome']=='TOUCHDOWN' for d in sample)
            ids=[key(r) for r in sample] if family=='third' else [k for k,d in campaigns.items() if d['offense']==t]
            assert (item['numerator'],item['denominator'])==(n,len(sample)) and item['unitIds']==ids
            assert item['perspective']=='off' and item['observationId']==t+'/off/1/'+family
            assert item['includedInRateDistribution']==bool(sample)
            assert item['ratio']==(ratio(n,len(sample)) if sample else None)
            assert item['reasonCodes']==([] if sample else ['ZERO_ELIGIBLE_OPPORTUNITIES'])
            assert item['gameIds']==sorted(g['game_id'] for g in games if t in (g['home_team'],g['away_team']))
            all_ids.extend(ids)
            if sample:independent.append(item)
        assert len(all_ids)==len(set(all_ids))
        assert ref['teamRateDistribution']['points']==independent and ref['representedTeams']==[p['team'] for p in independent]
        assert ref['teamsWithoutRate']==[p for p in ref['inventory'] if not p['denominator']]
        n=sum(p['numerator'] for p in independent); d=sum(p['denominator'] for p in independent)
        assert ref['pooledRate']==dict(numerator=n,denominator=d,method='SUM_NUMERATORS_OVER_SUM_DENOMINATORS')
        mean=sum((Fraction(p['numerator'],p['denominator']) for p in independent),Fraction())/len(independent)
        assert mean!=Fraction(n,d) # Distinct constructs, demonstrated in this dataset.
        assert ref['pilotTeamsIncluded']==['NYJ','TEN'] and ref['pilotIndependentOfReference'] is False
        refs[family]=dict(points=len(independent),pooled=ratio(n,d),arithmeticMeanOfTeamRates=dict(numerator=str(mean.numerator),denominator=mean.denominator),uniqueUnits=len(all_ids))
    assert refs['third']['points']==32 and refs['redZone']['points']==31
    assert data['leagueReferences']['redZone']['teamsWithoutRate'][0]['team']=='ATL'
    for name,comparison in data['comparisons'].items():
        ds=[p['metrics'][name]['descriptor'] if name in p['metrics'] else next(e['descriptor'] for e in p['epa'] if e['foundation']==name) for p in data['productions']]
        delta=Fraction(str(ds[0]['numerator']))/ds[0]['denominator']-Fraction(str(ds[1]['numerator']))/ds[1]['denominator']
        assert comparison['differenceAminusB']==dict(numerator=str(delta.numerator),denominator=delta.denominator)
        assert comparison['sideBySide']['allowed'] and comparison['difference']['allowed']
        assert comparison['difference']['commonGameIds']==[GAME] and comparison['difference']['commonUnitIds']==[]
    assert {f['id'] for f in data['facts']}=={'third-observed-rate','long-third-equal','red-zone-count-and-rate'}
    for fact in data['facts']:
        assert fact['permission']['allowed'] and fact['scope']['weeks']==[1] and fact['scope']['gameIds']==[GAME]
        ds=[p['metrics'][fact['metric']]['descriptor'] for p in data['productions']]
        assert fact['evidence']==[dict(observationId=d['id'],numerator=d['numerator'],denominator=d['denominator'],unitIds=d['unitIds']) for d in ds]
        assert 'NO_SCORE_CAUSAL_EXPLANATION' in fact['limitations']
    assert data['temporalContext']['previousRegularSeasonGames']['weeks']==[] and data['temporalContext']['w2ContextAllowed'] is False
    assert set(data['guarantees'].values())=={'UNKNOWN'}
    # Independently inventory preserved market fields; never infer capture time from game date.
    temporal=json.loads((bundle/'sources/observations/shared-source/input.json').read_bytes())
    calc=next(c for c in temporal['calculations'] if c['game']['game_id']==GAME)
    files={r['revision_id']:r for r in temporal['resources'] if r['kind']=='FILE'}
    for record, source in zip(data['market']['records'],data['market']['sources']):
        payload=files[source['sourceRevisionId']]['payload'];b=base64.b64decode(payload['bytes_base64']);assert sha(b)==source['sourceRevisionId']
        frame=pl.read_parquet(BytesIO(b)).filter(pl.col('game_id')==GAME).to_dicts();assert len(frame)==1
        assert all(frame[0][k]==v for k,v in record.items())
        assert source['sourceRevisionId'] in [i['source_revision_id'] for i in calc['original']['manifest']['inputs'] if i['kind']=='calendar']
    assert data['market']['preKickoffOrClosingClaimAllowed'] is False and data['market']['captureTime']=='UNKNOWN'
    report=dict(bundleId=artifact_pin,independent=True,projectorOrPolicyImported=False,previousIndependentLedgerAudit=str(previous.name),
                rawW1Rows=w1.height,rawW1Games=len(games),marksChecked=marks,entryEvidenceChecked=entry_evidence,
                jointDistribution=joint_report,epaRawRationals=epa_report,league=refs,factsChecked=len(data['facts']),
                offenseDefenseSameEvidence=True,unknownsPreserved=True,divergences=[])
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('jointDistribution','epaRawRationals')},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.bundle,a.output)
