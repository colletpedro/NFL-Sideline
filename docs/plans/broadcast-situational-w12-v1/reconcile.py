"""Independent raw-record reconciliation. Does not import the situational projector."""
import argparse
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

import polars as pl


def ratio(n,d):
    return dict(numerator=n,denominator=d)


def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads((a.bundle/'situational.json').read_bytes());ledger=json.loads((a.bundle/'ledger.json').read_bytes())
    raw=pl.read_parquet(a.bundle/'pbp.parquet').sort('game_id','order_sequence')
    assert hashlib.sha256((a.bundle/'pbp.parquet').read_bytes()).hexdigest()=='4e3707397912babcd0d7d02abd3be95db8e66785250e62bf9d874f37229d895e'
    key=lambda r:f"{r['game_id']}:{int(r['play_id'])}"
    ts={};drives={};inside_differences=[];sequence=[]
    # Column masks, independently of the per-record classifier in the projector.
    eligible=raw.filter((pl.col('down')==3)&pl.col('play_type').is_in(['pass','run'])&
        pl.all_horizontal([pl.col(c)==0 for c in ['play_deleted','aborted_play','qb_kneel','qb_spike','extra_point_attempt','two_point_attempt']])&
        pl.col('third_down_converted').is_in([0,1])&pl.col('third_down_failed').is_in([0,1])&
        (pl.col('third_down_converted')+pl.col('third_down_failed')==1))
    assert raw.group_by('game_id','play_id').len().filter(pl.col('len')!=1).is_empty()
    included={key(r) for r in eligible.to_dicts()}
    for r in raw.filter(pl.col('down')==3).to_dicts():
        k=key(r);good=k in included
        if good:reason=None
        elif r['play_type']=='no_play':reason='NO_PLAY'
        elif r['play_type']=='qb_kneel':reason='KNEEL'
        elif r['aborted_play']==1:reason='ABORTED'
        else:reason='OTHER_TYPE'
        ts[k]=dict(id=k,gameId=r['game_id'],week=r['week'],offense=r['posteam'],defense=r['defteam'],included=good,reason=reason,
            converted=int(r['third_down_converted']) if good else None,kind=r['play_type'] if good else None,
            distance='short' if 1<=r['ydstogo']<=3 else 'medium' if 4<=r['ydstogo']<=6 else 'long' if r['ydstogo']>=7 else 'unknown',
            penaltyFirstDown=r['first_down_penalty']==1,sack=r['sack']==1,scramble=r['qb_scramble']==1,uncertain=False)
    assert {u['id']:u for u in ledger['third']}==ts
    # Validate every fixed-drive block against chronological possession events.
    for (game,),g in raw.group_by('game_id',maintain_order=True):
        blocks=[]
        for r in g.to_dicts():
            if not blocks or blocks[-1]!=r['fixed_drive']:blocks.append(r['fixed_drive'])
        assert len(blocks)==len(set(blocks)),('reopened campaign',game)
        seq=g['order_sequence'].to_list();assert all(x<y for x,y in zip(seq,seq[1:])),game
        sequence.append(dict(gameId=game,fixedBlocks=len(blocks),rawDriveDifferences=g.filter(pl.col('drive')!=pl.col('fixed_drive')).height))
    for (game,drive),g in raw.group_by('game_id','fixed_drive',maintain_order=True):
        rs=g.to_dicts();scr=[]
        for r in rs:
            if r['down'] in [1,2,3,4] and r['play_deleted']==0 and r['extra_point_attempt']==0 and r['two_point_attempt']==0 and r['play_type'] in ['pass','run','qb_kneel','qb_spike','punt','field_goal','no_play'] and (r['play_type']!='no_play' or r['penalty']==1):scr.append(r)
        k=f'{game}:drive:{drive}'
        if not scr:
            drives[k]=dict(id=k,gameId=game,week=rs[0]['week'],offense=None,defense=None,included=False,reason='NO_SCRIMMAGE',uncertain=False,entryPlayIds=[],playIds=[key(r) for r in rs],rawDrives=sorted({r['drive'] for r in rs if r['drive'] is not None}),touchdownPlayIds=[],outcome=None,auxiliaryInside20=any(r['drive_inside20']==1 for r in rs),auxiliaryScored=any(r['drive_ended_with_score']==1 for r in rs));continue
        assert len({(r['posteam'],r['defteam']) for r in scr})==1
        assert all(r['yardline_100'] is not None and 0<=r['yardline_100']<=100 for r in scr)
        offense,defense=scr[0]['posteam'],scr[0]['defteam'];entry=[key(r) for r in scr if 0<r['yardline_100']<=20]
        touchdown=[key(r) for r in scr if r['touchdown']==1 and r['td_team']==offense and r['play_type'] in ['pass','run']]
        # Independent terminal reconstruction uses final event description/type, then checks the source label.
        last=scr[-1];desc=last['desc'];fixed={r['fixed_drive_result'] for r in rs};outcome=None
        if touchdown:outcome='TOUCHDOWN';assert touchdown==[key(last)]
        elif last['touchdown']==1 and last['td_team']==defense:outcome='OPPONENT_TOUCHDOWN'
        elif last['play_type']=='punt':outcome='PUNT'
        elif last['safety']==1 and 'SAFETY' in desc:outcome='SAFETY'
        elif last['play_type']=='field_goal':outcome='FIELD_GOAL' if last['field_goal_result']=='made' else 'MISSED_FIELD_GOAL'
        elif last['interception']==1 or last['fumble_lost']==1:outcome='TURNOVER'
        elif last['down']==4 and last['fourth_down_failed']==1:outcome='DOWNS'
        elif any(r['desc'] in ['END GAME','END QUARTER 2','END QUARTER 4','END QUARTER 5'] and r['game_seconds_remaining'] in [0,1800] for r in rs):outcome='END_HALF_GAME'
        assert outcome is not None,(k,desc)
        labels={'TOUCHDOWN':'Touchdown','OPPONENT_TOUCHDOWN':'Opp touchdown','PUNT':'Punt','SAFETY':'Safety','FIELD_GOAL':'Field goal','MISSED_FIELD_GOAL':'Missed field goal','TURNOVER':'Turnover','DOWNS':'Turnover on downs','END_HALF_GAME':'End of half'}
        assert fixed=={labels[outcome]},(k,outcome,fixed)
        drives[k]=dict(id=k,gameId=game,week=rs[0]['week'],offense=offense,defense=defense,included=bool(entry),reason=None if entry else 'NO_ENTRY',uncertain=False,entryPlayIds=entry,playIds=[key(r) for r in rs],rawDrives=sorted({r['drive'] for r in rs if r['drive'] is not None}),touchdownPlayIds=touchdown,outcome=outcome,auxiliaryInside20=any(r['drive_inside20']==1 for r in rs),auxiliaryScored=any(r['drive_ended_with_score']==1 for r in rs))
        if bool(entry)!=drives[k]['auxiliaryInside20']:inside_differences.append(dict(id=k,entryPlayIds=entry,sourceInside20=drives[k]['auxiliaryInside20'],reason='Inclusive line 20 / established kneel position; project definition'))
    assert {u['id']:u for u in ledger['campaigns']}==drives
    teams=sorted(set(raw['home_team'])|set(raw['away_team']));assert len(teams)==32
    expected_ids={f"{t}/{s}/{w}" for t in teams for s in ['off','def'] for w in ['1','2','1-2']}
    assert {d['id'] for d in data['documents']}==expected_ids
    rounded={};comparisons=0
    for d in data['documents']:
        team=d['team'];side=d['perspective'];weeks=d['weeks'];column='offense' if side=='off' else 'defense'
        games=raw.filter(pl.col('week').is_in(weeks)&((pl.col('home_team')==team)|(pl.col('away_team')==team))).select('game_id','week','home_team','away_team').unique().sort('game_id').to_dicts()
        expected_games=[dict(gameId=g['game_id'],week=g['week'],home=g['home_team'],away=g['away_team'],opponent=g['away_team'] if g['home_team']==team else g['home_team']) for g in games]
        assert sorted(d['games'],key=lambda g:g['gameId'])==expected_games
        assert len(games)==len(weeks)
        ids={g['game_id'] for g in games}
        for family,units in [('third',ts),('redZone',drives)]:
            sample=[u for u in units.values() if u['gameId'] in ids and u[column]==team];inc=[u for u in sample if u['included']];m=d[family]
            n=sum(u['converted'] if family=='third' else u['outcome']=='TOUCHDOWN' for u in inc);den=len(inc)
            assert (m['numerator'],m['denominator'])==(n,den)
            assert set(m['unitIds'])=={u['id'] for u in inc} and len(m['unitIds'])==len(set(m['unitIds']))
            assert set(m['excludedIds'])=={u['id'] for u in sample if not u['included']}
            assert m['exclusions']==dict(Counter(u['reason'] for u in sample if not u['included']))
            assert m['status']==('AVAILABLE' if den else 'NO_OPPORTUNITIES')
            assert m['ratio']==(ratio(n,den) if den else None) and m['ambiguousIds']==[]
            assert m['denominatorState']==('POSITIVE' if den else 'ZERO')
            if family=='third':
                for field,keys,col in [('byType',['pass','run'],'kind'),('byDistance',['short','medium','long','unknown'],'distance')]:
                    assert m[field]=={k:ratio(sum(u['converted'] for u in inc if u[col]==k),sum(u[col]==k for u in inc)) for k in keys}
                assert m['penaltyFirstDowns']==dict(included=sum(u['penaltyFirstDown'] for u in inc),excluded=sum(u['penaltyFirstDown'] for u in sample if not u['included']))
                assert m['sacks']==sum(u['sack'] for u in inc) and m['scrambles']==sum(u['scramble'] for u in inc)
            else:
                assert m['outcomes']==dict(Counter(u['outcome'] for u in inc));assert m['observedEntries']==den
            rounded[d['id']+'/'+family]=str((Decimal(n)*100/Decimal(den)).quantize(Decimal('.1'),rounding=ROUND_HALF_UP)).replace('.',',')+'%' if den else None
            comparisons+=1
    # Union proof for both families, every team/side. No rates averaged.
    for t in teams:
        for s in ['off','def']:
            docs={tuple(d['weeks']):d for d in data['documents'] if d['team']==t and d['perspective']==s}
            for f in ['third','redZone']:
                one,two,both=(docs[w][f] for w in [(1,),(2,),(1,2)])
                assert not set(one['unitIds'])&set(two['unitIds'])
                assert set(both['unitIds'])==set(one['unitIds'])|set(two['unitIds'])
                assert both['numerator']==one['numerator']+two['numerator'] and both['denominator']==one['denominator']+two['denominator']
    result=dict(independent=True,rawRows=raw.height,games=32,teams=32,documents=192,metricComparisons=comparisons,thirdCandidates=len(ts),thirdEligible=len(included),thirdConversions=sum(u['converted'] or 0 for u in ts.values()),thirdExclusions=dict(Counter(u['reason'] for u in ts.values() if not u['included'])),campaigns=len(drives),redZoneOpportunities=sum(u['included'] for u in drives.values()),redZoneTouchdowns=sum(u['included'] and u['outcome']=='TOUCHDOWN' for u in drives.values()),inside20Divergences=inside_differences,sequenceAudit=sequence,rounded=rounded,divergences=[])
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['rounded','sequenceAudit','inside20Divergences']})
if __name__=='__main__':main()
