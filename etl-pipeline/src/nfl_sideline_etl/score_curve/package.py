import json,shutil,tempfile
from pathlib import Path
import polars as pl
from ..game_story.package import read as read_story
from ..game_story.project import clock,score
from ..season_analysis.package import hashes
from ..situational import safe,digest,encoded
from ..offline_metrics.artifact import rename_exclusive
VERSION='broadcast-curve-events-v1'
SOURCE_PIN='sha256:93b6cad3ea3a1db822c16e4bfdadf70f28122e2dd60002708d44745776129624'


def project(rows,timelines):
    games={gid:[] for gid in timelines}
    for r in sorted(rows,key=lambda r:(r['game_id'],r['order_sequence'])):
        gid=r['game_id']
        if gid not in games or r['play_deleted']!=0 or not (r['interception']==1 or r['fumble_lost']==1):continue
        t=timelines[gid];teams=[t['away'],t['home']];changes=[]
        if r['interception']==1:changes.append((r['posteam'],r['defteam'],'INTERCEPTION'))
        if r['fumble_lost']==1:
            fumbles=[]
            for n in (1,2):
                lost,recovered=r[f'fumbled_{n}_team'],r[f'fumble_recovery_{n}_team']
                if lost is not None and recovered is not None and lost!=recovered:fumbles.append((lost,recovered,'FUMBLE_LOST'))
            if not fumbles:raise ValueError('Lost fumble without recovery evidence')
            changes.extend(fumbles)
        if not changes:raise ValueError('Turnover flag without recoverable team evidence')
        for n,(lost,recovered,kind) in enumerate(changes):
            if lost not in teams or recovered not in teams or lost==recovered:raise ValueError('Invalid turnover identity')
            s=score(r);c=clock(r)
            games[gid].append(dict(id=f"{gid}:{int(r['play_id'])}:turnover:{n}",playId=int(r['play_id']),sourceOrder=r['order_sequence'],
                                  lostTeam=lost,recoveredTeam=recovered,kind=kind,score=s,margin=s[0]-s[1],description=r['desc'],**c))
    return dict(contractVersion=VERSION,sourcePin=SOURCE_PIN,games=games,rule='OBSERVED_INTERCEPTION_OR_LOST_FUMBLE_WITH_TEAM_EVIDENCE_V1')


def derive(root):
    b,_=read_story(root/'source',SOURCE_PIN);story=json.loads(b)
    rows=pl.read_parquet(root/'source/source/source/pbp.parquet').to_dicts()
    return encoded(project(rows,story['timelines']))


def read(root,pin=None):
    root=safe(root);m=json.loads((root/'COMPLETED.json').read_bytes());h=hashes(root);h.pop('COMPLETED.json');b=(root/'events.json').read_bytes()
    if m['version']!=VERSION or m['files']!=h or m['bundleId']!=digest(b) or pin is not None and pin!=digest(b) or derive(root)!=b:raise ValueError('Curve events package mismatch')
    return b,m


def generate(source,output):
    source,output=safe(source),safe(output)
    if output.exists() or source==output or source in output.parents or output in source.parents:raise ValueError('New disjoint destination required')
    read_story(source,SOURCE_PIN);before=hashes(source);output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.'+output.name+'.pending-',dir=output.parent))
    try:
        shutil.copytree(source,stage/'source')
        if before!=hashes(source) or before!=hashes(stage/'source'):raise ValueError('Source changed during copy')
        b=derive(stage);(stage/'events.json').write_bytes(b);m=dict(version=VERSION,bundleId=digest(b),files=hashes(stage));(stage/'COMPLETED.json').write_bytes(encoded(m));read(stage,m['bundleId']);rename_exclusive(stage,output);return m
    finally:
        if stage.exists():shutil.rmtree(stage)
