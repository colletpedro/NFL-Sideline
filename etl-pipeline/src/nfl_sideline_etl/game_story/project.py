from math import isfinite
from ..season_analysis.policy import decision
from ..season_analysis import WEEKS
from . import VERSION, SOURCE_PIN


def clock(row):
    q,seconds=row['qtr'],row['quarter_seconds_remaining']
    if q not in (1,2,3,4,5) or seconds is None or not isfinite(seconds) or int(seconds)!=seconds or not 0<=seconds<=(900 if q<=4 else 600):
        raise ValueError('Unsupported or missing game clock')
    return dict(quarter=int(q),remaining=int(seconds),clock=f'{int(seconds)//60:02}:{int(seconds)%60:02}',
                elapsed=int((q-1)*900+900-seconds if q<=4 else 3600+600-seconds))


def score(row):
    s=[row['total_away_score'],row['total_home_score']]
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not isfinite(v) or int(v)!=v or v<0 for v in s):
        raise ValueError('Missing or invalid score state')
    return list(map(int,s))


def score_kind(row,points,team):
    if row['play_deleted']!=0:raise ValueError('Deleted scoring transition')
    if points==6 and row['touchdown']==1 and row['td_team']==team:return 'TOUCHDOWN'
    if points==3 and row['field_goal_result']=='made' and row['posteam']==team:return 'FIELD_GOAL'
    if points==1 and row['extra_point_result']=='good' and row['posteam']==team:return 'EXTRA_POINT'
    if points==2:
        if row['defensive_two_point_conv']==1 and row['defteam']==team:return 'DEFENSIVE_TWO_POINT'
        if row['safety']==1 and row['defteam']==team:return 'SAFETY'
        if row['two_point_conv_result']=='success' and row['posteam']==team:return 'TWO_POINT'
    raise ValueError('Score change lacks matching event evidence')


def timeline(game,doc,rows):
    if not rows:return dict(status='SOURCE_ABSENT',reason='NO_PLAY_BY_PLAY',events=[],campaigns=[])
    rows=sorted(rows,key=lambda r:r['order_sequence']);events=[];previous=[0,0];last_elapsed=0;by_id={}
    try:
        if len({r['play_id'] for r in rows})!=len(rows):raise ValueError('Duplicate play')
        for r in rows:
            by_id[f"{game['gameId']}:{int(r['play_id'])}"]=r
            current=score(r)
            if current==previous:continue
            delta=[current[j]-previous[j] for j in (0,1)]
            if min(delta)<0 or sum(v>0 for v in delta)!=1:raise ValueError('Nonmonotonic or simultaneous score change')
            side=0 if delta[0] else 1;team=game['away'] if side==0 else game['home'];time=clock(r)
            if time['elapsed']<last_elapsed:raise ValueError('Scoring clock reversal')
            events.append(dict(id=f"{game['gameId']}:{int(r['play_id'])}",playId=int(r['play_id']),sourceOrder=r['order_sequence'],
                               team=team,kind=score_kind(r,delta[side],team),points=delta[side],before=previous,after=current,
                               margin=current[0]-current[1],fixedDrive=r['fixed_drive'],description=r['desc'],**time))
            previous=current;last_elapsed=time['elapsed']
        if previous!=[game['awayScore'],game['homeScore']]:raise ValueError('Final score differs from calendar')
        end=clock(rows[-1]);end_elapsed=end['elapsed']
        if end_elapsed<last_elapsed:raise ValueError('End precedes scoring event')
        campaigns=[]
        for p in doc['productions']:
            for u in p['redZoneCampaigns']:
                # Chronological terminal evidence; END_HALF_GAME can include administrative ending rows.
                terminal=max(u['outcomeEvidence'],key=lambda e:e['order_sequence']);r=by_id[f"{game['gameId']}:{int(terminal['play_id'])}"]
                current=score(r)
                campaigns.append(dict(id=u['id'],team=u['offense'],opponent=u['defense'],outcome=u['outcome'],drive=u['fixedDrive'],
                                      playId=int(r['play_id']),sourceOrder=r['order_sequence'],score=current,margin=current[0]-current[1],
                                      entryPlayIds=u['entryPlayIds'],terminalPlayId=f"{game['gameId']}:{int(r['play_id'])}",description=r['desc'],**clock(r)))
        campaigns.sort(key=lambda u:u['sourceOrder'])
        return dict(status='AVAILABLE',reason=None,gameId=game['gameId'],away=game['away'],home=game['home'],final=previous,
                    endElapsed=end_elapsed,periods=list(range(1,end['quarter']+1)),events=events,campaigns=campaigns,
                    definition='OBSERVED_POST_PLAY_SCORES_AWAY_MINUS_HOME_V1',allScoringIncluded=True)
    except (ValueError,KeyError,TypeError) as e:
        return dict(status='INSUFFICIENT',reason=str(e),events=[],campaigns=[])


def reference(team_documents,family):
    inventory=[];descriptors=[]
    for team,doc in sorted(team_documents.items()):
        metric=doc['productions'][0]['metrics'][family];d=metric['descriptor']
        allowed=d['status']=='AVAILABLE' and metric['display']['allowed'] and metric['aggregation']['allowed']
        item=dict(team=team,perspective='off',observationId=d['id'],gameIds=d['gameIds'],numerator=d['numerator'],denominator=d['denominator'],
                  status=d['status'],unitIds=d['unitIds'],ratio=dict(numerator=d['numerator'],denominator=d['denominator']) if allowed else None,
                  includedInRateDistribution=allowed,reasonCodes=[] if allowed else [d['status']])
        inventory.append(item)
        if allowed:descriptors.append(d)
    points=[p for p in inventory if p['includedInRateDistribution']]
    return dict(season=2026,phase='REG',weeks=WEEKS,population=descriptors[0]['population'],candidateTeams=sorted(team_documents),
                representedTeams=[p['team'] for p in points],inventory=inventory,teamsWithoutRate=[p for p in inventory if not p['includedInRateDistribution']],
                teamRateDistribution=dict(points=points),pooledRate=dict(numerator=sum(p['numerator'] for p in points),denominator=sum(p['denominator'] for p in points),method='SUM_NUMERATORS_OVER_SUM_DENOMINATORS'),
                permission=decision('leagueReference',descriptors),participantsIncluded=[],participantsIndependentOfReference=False,
                context='RETROSPECTIVE_SEASON_THROUGH_W7_NOT_AS_OF_GAME')


def project(index,documents,team_documents,rows):
    grouped={g['gameId']:[] for g in index['games']}
    for r in rows:
        if r['game_id'] in grouped:grouped[r['game_id']].append(r)
    return dict(contractVersion=VERSION,sourcePin=SOURCE_PIN,season=2026,weeks=WEEKS,
                seasonReferences={f:reference(team_documents,f) for f in ('third','redZone')},
                timelines={g['gameId']:timeline(g,documents[g['gameId']],grouped[g['gameId']]) for g in index['games']},
                guarantees={k:'UNKNOWN' for k in ('completeness','expectedCoverage','epaModel','historicalAvailability')})
