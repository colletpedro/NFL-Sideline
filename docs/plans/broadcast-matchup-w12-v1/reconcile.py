"""Independent raw audit. Never imports the new projector or its policy.

The existing independent situational audit checks all 882 candidates and 684
campaigns. Here masks/groupings independently reconcile the new 32 documents,
192 EPA, calendar, enriched evidence, operation permissions and weekly inventory.
"""
import argparse
import base64
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
import hashlib
from io import BytesIO
import json
from math import isfinite
from pathlib import Path
import subprocess
import sys

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
sha = lambda b: 'sha256:'+hashlib.sha256(b).hexdigest()
key = lambda r: f"{r['game_id']}:{int(r['play_id'])}"


def run(bundle, output):
    src=bundle/'sources/situational'
    prior=output.with_name('reconciliation-situational.json')
    subprocess.run([sys.executable,'-B',str(ROOT/'docs/plans/broadcast-situational-w12-v1/reconcile.py'),'--bundle',str(src),'--output',str(prior)],check=True,stdout=subprocess.DEVNULL)
    assert json.loads(prior.read_bytes())['divergences']==[]
    raw=pl.read_parquet(src/'pbp.parquet').sort('game_id','order_sequence')
    rs=raw.to_dicts();by_id={key(r):r for r in rs};assert len(by_id)==len(rs)
    eligible=raw.filter((pl.col('down')==3)&pl.col('play_type').is_in(['pass','run'])&
        pl.all_horizontal([pl.col(c)==0 for c in ['play_deleted','aborted_play','qb_kneel','qb_spike','extra_point_attempt','two_point_attempt']])&
        pl.col('third_down_converted').is_in([0,1])&pl.col('third_down_failed').is_in([0,1])&
        (pl.col('third_down_converted')+pl.col('third_down_failed')==1)).to_dicts()
    ledger=json.loads((src/'ledger.json').read_bytes());campaigns={u['id']:u for u in ledger['campaigns'] if u['included']}
    sit=json.loads((src/'situational.json').read_bytes());sit_docs={d['id']:d for d in sit['documents']}
    old=json.loads((bundle/'sources/observations/observations.json').read_bytes())
    temporal=json.loads((bundle/'sources/observations/shared-source/input.json').read_bytes())
    resources={r['revision_id']:r for r in temporal['resources'] if r['kind']=='FILE'}
    schedules={}
    index=json.loads((bundle/'index.json').read_bytes());assert len(index['games'])==32
    report=[];weekly={};rounding={}
    for entry in index['games']:
        gid,week=entry['gameId'],entry['week'];participants=[entry['away'],entry['home']]
        payload=(bundle/'games'/(gid+'.json')).read_bytes();assert sha(payload)==entry['documentHash']
        d=json.loads(payload);assert d['game']==dict(gameId=gid,season=2026,phase='REG',weeks=[week],offenses=participants,away=participants[0],home=participants[1])
        assert d['calendar']=={k:v for k,v in entry.items() if k not in ('path','documentHash')}
        source=entry['calendarSourceHash']
        if source not in schedules:
            b=base64.b64decode(resources[source]['payload']['bytes_base64']);assert sha(b)==source;schedules[source]=pl.read_parquet(BytesIO(b))
        schedule=schedules[source].filter(pl.col('game_id')==gid).to_dicts();assert len(schedule)==1;schedule=schedule[0]
        assert (schedule['season'],schedule['game_type'],schedule['week'],schedule['away_team'],schedule['home_team'])==(2026,'REG',week,*participants)
        assert all(entry[k]==schedule[c] for k,c in [('gameday','gameday'),('awayScore','away_score'),('homeScore','home_score'),('result','result')])
        scores=[entry[k] for k in ('awayScore','homeScore','result')]
        assert all(x is None for x in scores) or all(type(x)==int for x in scores) and min(scores[:2])>=0 and scores[2]==scores[1]-scores[0]
        assert [p['offense'] for p in d['productions']]==participants
        production_report=[]
        for p in d['productions']:
            team,opponent=p['offense'],p['defense'];assert opponent==next(t for t in participants if t!=team)
            assert p['gameId']==gid and p['label']==team+' com a bola'
            ts=[r for r in eligible if r['game_id']==gid and r['posteam']==team]
            cs={k:u for k,u in campaigns.items() if u['gameId']==gid and u['offense']==team}
            assert [u['id'] for u in p['thirdAttempts']]==[key(r) for r in ts]
            for u,r in zip(p['thirdAttempts'],ts):
                assert (u['gameId'],u['offense'],u['defense'],u['week'],u['playId'],u['sourceOrder'],u['yardsToGo'],u['kind'],u['converted'],u['sack'],u['scramble'])==(gid,team,opponent,week,r['play_id'],r['order_sequence'],r['ydstogo'],r['play_type'],int(r['third_down_converted']),r['sack']==1,r['qb_scramble']==1)
            assert [u['id'] for u in p['redZoneCampaigns']]==list(cs)
            for u in p['redZoneCampaigns']:
                source_c=cs[u['id']];assert all(u[k]==v for k,v in source_c.items())
                rows=[by_id[i] for i in source_c['playIds']];assert u['chronologicalPlayIds']==[key(r) for r in rows]
                assert u['sourceOrder']==rows[0]['order_sequence'] and u['fixedDrive']==rows[0]['fixed_drive']
                assert [key(e) for e in u['entryEvidence']]==source_c['entryPlayIds']
                for ev in u['entryEvidence']+u['outcomeEvidence']:assert all(by_id[key(ev)][k]==v for k,v in ev.items())
                assert u['entryEvidence'] and all(0<e['yardline_100']<=20 for e in u['entryEvidence'])
                scr=[r for r in rows if r['down'] in (1,2,3,4) and r['play_deleted']==0 and r['extra_point_attempt']==0 and r['two_point_attempt']==0 and r['play_type'] in ('pass','run','qb_kneel','qb_spike','punt','field_goal','no_play') and (r['play_type']!='no_play' or r['penalty']==1)]
                last=scr[-1]
                if u['outcome']=='END_HALF_GAME':assert all(e['desc'] in ('END GAME','END QUARTER 2','END QUARTER 4','END QUARTER 5') and e['game_seconds_remaining'] in (0,1800) for e in u['outcomeEvidence'])
                else:assert [key(e) for e in u['outcomeEvidence']]==[key(last)]
            def bucket(r):
                y=r['ydstogo'];return 'unknown' if y is None or y<=0 or y!=int(y) else 'short' if y<=3 else 'medium' if y<=6 else 'long'
            assert len(p['thirdDistanceByType'])==8
            for cell in p['thirdDistanceByType']:
                sample=[r for r in ts if r['play_type']==cell['kind'] and bucket(r)==cell['distance']]
                assert cell['unitIds']==[key(r) for r in sample]
                assert (cell['numerator'],cell['denominator'])==(sum(int(r['third_down_converted']) for r in sample),len(sample))
            for f,n,den in [('third',sum(int(r['third_down_converted']) for r in ts),len(ts)),('thirdLong',sum(int(r['third_down_converted']) for r in ts if bucket(r)=='long'),sum(bucket(r)=='long' for r in ts)),('redZone',sum(c['outcome']=='TOUCHDOWN' for c in cs.values()),len(cs))]:
                m=p['metrics'][f];v=m['descriptor'];assert (v['numerator'],v['denominator'])==(n,den)
                assert v['status']==('AVAILABLE' if den else 'NO_OPPORTUNITIES') and v['weeks']==[week] and v['gameIds']==[gid]
                assert m['display']['allowed'] and m['display']['operation']=='display' and m['display']['observationIds']==[v['id']]
                rounding[v['id']]=str((Decimal(n)*100/Decimal(den)).quantize(Decimal('.1'),rounding=ROUND_HALF_UP)).replace('.',',')+'%' if den else None
                if f!='thirdLong':assert m['observation']==sit_docs[f'{team}/off/{week}'][f]==sit_docs[f'{opponent}/def/{week}'][f]
            epa=[]
            own=[r for r in rs if r['game_id']==gid and r['posteam']==team and r['play_type'] in ('pass','run') and all(r[c]==0 for c in ('qb_kneel','qb_spike','play_deleted','special_teams_play','two_point_attempt'))]
            assert len(p['epa'])==3
            for e in p['epa']:
                f=e['foundation'];sample=[r for r in own if f=='general' or r['play_type']==('pass' if f=='classified_pass' else 'run')]
                finite=[r for r in sample if r['epa'] is not None and isfinite(r['epa'])]
                total=sum((Fraction(str(r['epa'])) for r in finite),Fraction())
                o=e['originalObservation'];mirror=e['opponentDefenseObservation'];assert o in old and mirror in old
                assert o['subject']==dict(team=team,role='off',foundation=f) and mirror['subject']==dict(team=opponent,role='def',foundation=f)
                assert o['observed']['includedGameIds']==[gid] and o['request']['period']['weeks']==[week]
                assert o['totals']==mirror['totals'] and o['values']==mirror['values'] and o['definition']==mirror['definition']
                assert e['eligibleUnitIds']==[key(r) for r in sample] and e['finiteEpaUnitIds']==[key(r) for r in finite]
                t=o['totals'];assert (t['eligibleN'],t['epaN'],t['epaMissingN'],t['epaNonfiniteN'])==(len(sample),len(finite),sum(r['epa'] is None for r in sample),sum(r['epa'] is not None and not isfinite(r['epa']) for r in sample))
                assert Fraction(t['epaSum'])==total==Fraction(e['descriptor']['numerator']) and e['descriptor']['denominator']==len(finite)
                assert Fraction(o['values']['epa']['numerator'])==total and o['values']['epa']['denominator']==len(finite)
                assert o['guarantees']['compatibility']['epaModel']['state']=='UNKNOWN'
                digits=o['presentation']['epaDecimals'];text=(Decimal(t['epaSum'])/Decimal(len(finite))).quantize(Decimal(1).scaleb(-digits),rounding=ROUND_HALF_UP)
                sign='−' if total<0 else '+' if total>0 else ''
                display=sign+('<'+str(Decimal(1).scaleb(-digits)).replace('.',',') if text==0 and total!=0 else str(abs(text)).replace('.',','))
                epa.append(dict(foundation=f,eligible=len(sample),finite=len(finite),sum=t['epaSum'],rounded=str(text),display=display))
            production_report.append(dict(team=team,defense=opponent,third=p['metrics']['third']['descriptor'],redZone=p['metrics']['redZone']['descriptor'],epa=epa,thirdMarks=len(ts),campaignMarks=len(cs)))
        for name,c in d['comparisons'].items():
            ds=[p['metrics'][name]['descriptor'] if name in p['metrics'] else next(e['descriptor'] for e in p['epa'] if e['foundation']==name) for p in d['productions']]
            allowed=all(x['status']=='AVAILABLE' and x['denominator']>0 for x in ds)
            assert c['sideBySide']['allowed']==allowed and c['difference']['allowed']==allowed
            assert c['difference']['observationIds']==[x['id'] for x in ds]
            if allowed:
                diff=Fraction(str(ds[0]['numerator']))/ds[0]['denominator']-Fraction(str(ds[1]['numerator']))/ds[1]['denominator']
                assert c['differenceAminusB']==dict(numerator=str(diff.numerator),denominator=diff.denominator)
            else:assert c['differenceAminusB'] is None
        for family,ref in d['leagueReferences'].items():
            teams=sorted({r[c] for r in rs if r['week']==week for c in ('home_team','away_team')})
            assert ref['weeks']==[week] and ref['candidateTeams']==teams and [p['team'] for p in ref['inventory']]==teams
            for point in ref['inventory']:
                sample=[r for r in eligible if r['week']==week and r['posteam']==point['team']] if family=='third' else [c for c in campaigns.values() if c['week']==week and c['offense']==point['team']]
                n=sum(int(r['third_down_converted']) for r in sample) if family=='third' else sum(c['outcome']=='TOUCHDOWN' for c in sample)
                ids=[key(r) for r in sample] if family=='third' else [c['id'] for c in sample]
                assert (point['numerator'],point['denominator'],point['unitIds'])==(n,len(sample),ids)
                assert point['ratio']==(dict(numerator=n,denominator=len(sample)) if sample else None) and point['includedInRateDistribution']==bool(sample)
            points=[p for p in ref['inventory'] if p['denominator']];excluded=[p for p in ref['inventory'] if not p['denominator']]
            assert ref['teamRateDistribution']['points']==points and ref['teamsWithoutRate']==excluded
            units=[i for p in points for i in p['unitIds']];assert len(units)==len(set(units))
            assert ref['participantsIncluded']==participants and ref['participantsIndependentOfReference'] is False
            assert ref['permission']['allowed'] and ref['permission']['observationIds']==[p['observationId'] for p in points]
            pooled=dict(numerator=sum(p['numerator'] for p in points),denominator=sum(p['denominator'] for p in points),method='SUM_NUMERATORS_OVER_SUM_DENOMINATORS')
            assert ref['pooledRate']==pooled
            weekly[f'W{week}/{family}']=dict(points=len(points),candidates=len(teams),withoutRate=excluded,pooled=pooled)
        for f in d['facts']:
            assert f['metric'] in ('third','thirdLong','redZone') and f['scope']==dict(season=2026,phase='REG',weeks=[week],gameIds=[gid])
            ds=[p['metrics'][f['metric']]['descriptor'] for p in d['productions']]
            assert f['evidence']==[dict(observationId=x['id'],numerator=x['numerator'],denominator=x['denominator'],unitIds=x['unitIds']) for x in ds]
            assert f['permission']['allowed'] and f['permission']['operation']=='editorialFact' and d['comparisons'][f['metric']]['difference']['allowed']
            rates=[Fraction(x['numerator'],x['denominator']) for x in ds]
            if rates[0]==rates[1]:assert 'mesma taxa' in f['text'] or 'taxas observadas foram iguais' in f['text']
            else:
                winner=participants[int(rates[1]>rates[0])]
                assert (f['text'].startswith(winner+' teve maior') if f['metric']!='redZone' else winner+' teve maior taxa' in f['text'])
        expected_families={f for f in ('third','thirdLong','redZone') if d['comparisons'][f]['difference']['allowed']}
        assert {f['metric'] for f in d['facts']}==expected_families
        assert set(d['guarantees'].values())=={'UNKNOWN'} and d['temporalContext']['historicalAvailability']=='UNKNOWN'
        assert d['temporalContext']['otherGamesContextAllowed'] is False and d['temporalContext']['referenceWeeks']==[week]
        assert d['temporalContext']['previousRegularSeasonGames']['status']==('NOT_APPLICABLE' if week==1 else 'OUT_OF_SCOPE')
        for rec,source_record in zip(d['market']['records'],d['market']['sources']):assert source_record['sourceRevisionId']==entry['calendarSourceHash'] and all(schedule[k]==v for k,v in rec.items())
        assert d['market']['captureTime']=='UNKNOWN' and d['market']['preKickoffOrClosingClaimAllowed'] is False
        report.append(dict(gameId=gid,week=week,participants=participants,scores=scores,documentHash=sha(payload),productions=production_report,facts=len(d['facts'])))
    expected={'W1/third':(154,377),'W2/third':(169,410),'W1/redZone':(70,108),'W2/redZone':(54,100)}
    for k,(n,den) in expected.items():assert (weekly[k]['pooled']['numerator'],weekly[k]['pooled']['denominator'])==(n,den)
    result=dict(independent=True,projectorOrPolicyImported=False,bundleId=sha((bundle/'index.json').read_bytes()),games=report,weekly=weekly,offensiveProductions=64,epaObservations=192,thirdMarks=sum(p['thirdMarks'] for g in report for p in g['productions']),campaignMarks=sum(p['campaignMarks'] for g in report for p in g['productions']),rounding=rounding,divergences=[])
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('games','weekly','rounding')}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.bundle,a.output)
