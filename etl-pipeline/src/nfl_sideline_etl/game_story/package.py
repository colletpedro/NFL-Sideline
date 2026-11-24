import json,shutil,tempfile
from pathlib import Path
import polars as pl
from ..situational import safe,digest,encoded
from ..season_analysis.package import read as read_season, hashes
from ..offline_metrics.artifact import rename_exclusive
from . import VERSION,SOURCE_PIN
from .project import project


def derive(root):
    source=root/'source';i,_=read_season(source,SOURCE_PIN)
    docs={g['gameId']:json.loads((source/g['path']).read_bytes()) for g in i['games']}
    teams={t['team']:json.loads((source/t['path']).read_bytes()) for t in i['teams']}
    rows=pl.read_parquet(source/'source/pbp.parquet').sort('game_id','order_sequence').to_dicts()
    return encoded(project(i,docs,teams,rows))


def read(root,pin=None):
    root=safe(root);m=json.loads((root/'COMPLETED.json').read_bytes());h=hashes(root);h.pop('COMPLETED.json')
    if m['version']!=VERSION or m['files']!=h:raise ValueError('Story package changed')
    b=(root/'story.json').read_bytes();actual=digest(b)
    if m['bundleId']!=actual or pin is not None and pin!=actual:raise ValueError('Story pin mismatch')
    if derive(root)!=b:raise ValueError('Story semantic reproduction mismatch')
    return b,m


def generate(source,output):
    source,output=safe(source),safe(output)
    if output.exists() or source==output or source in output.parents or output in source.parents:raise ValueError('New disjoint destination required')
    read_season(source,SOURCE_PIN);before=hashes(source);output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.'+output.name+'.pending-',dir=output.parent))
    try:
        shutil.copytree(source,stage/'source')
        if before!=hashes(source) or before!=hashes(stage/'source'):raise ValueError('Source changed during copy')
        b=derive(stage);(stage/'story.json').write_bytes(b);m=dict(version=VERSION,bundleId=digest(b),files=hashes(stage))
        (stage/'COMPLETED.json').write_bytes(encoded(m));read(stage,m['bundleId']);rename_exclusive(stage,output);return m
    finally:
        if stage.exists():shutil.rmtree(stage)
