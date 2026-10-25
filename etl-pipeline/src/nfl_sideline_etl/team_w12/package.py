"""Exclusive publication, complete operational source copy and full reader before HTTP."""
import json
from pathlib import Path
import shutil
import tempfile
from . import VERSION, PROJECTION, SOURCE_PIN
from .project import project
from ..situational import safe, encoded, digest
from ..comparison_foundation.package import hashes
from ..matchup_w12.package import read as read_matchups
from ..metrics_observations.publication import exact_tree
from ..offline_metrics.artifact import rename_exclusive

REQUEST = dict(contractVersion=VERSION, projectionVersion=PROJECTION, season=2026, phase='REG', weeks=[1,2],
               perspectives=['off','def'], sourceCollection=SOURCE_PIN, leagueReference=False)


def derive(root):
    if json.loads((root/'request.json').read_bytes()) != REQUEST: raise ValueError('Unsupported team request')
    index, raw, _ = read_matchups(root/'source/matchups', SOURCE_PIN)
    docs = project(index, {i: json.loads(b) for i,b in raw.items()}, root/'source/matchups', (root/'policy.md').read_text())
    payloads = {t: encoded(d) for t,d in docs.items()}
    out = dict(contractVersion=VERSION, projectionVersion=PROJECTION, season=2026, phase='REG', weeks=[1,2], sourceCollection=SOURCE_PIN,
               teams=[dict(team=t, gameIds=[g['gameId'] for g in docs[t]['games']], opponents=docs[t]['productions'][0]['opponents'],
                           documentHash=digest(b), path='teams/'+t+'.json') for t,b in sorted(payloads.items())],
               counts=dict(teams=32, perspectives=64, epa=192), guarantees=docs['ATL']['guarantees'])
    return encoded(out), payloads


def read(root, expected_pin=None):
    root=safe(root);m=json.loads((root/'COMPLETED.json').read_bytes());b=(root/'index.json').read_bytes()
    if set(m)!={'version','bundleId','files'} or m['version']!=VERSION or digest(b)!=m['bundleId'] or expected_pin and expected_pin!=m['bundleId']: raise ValueError('Team pin/marker mismatch')
    index=json.loads(b);teams=[t['team'] for t in index['teams']]
    if len(teams)!=32 or len(set(teams))!=32 or any(not __import__('re').fullmatch('[A-Z]{2,3}',t) for t in teams): raise ValueError('Invalid team inventory')
    names={'index.json','request.json','policy.md','source-receipt.json'}|{'teams/'+t+'.json' for t in teams}|{'source/matchups/'+f for f in hashes(root/'source/matchups')}
    exact_tree(root,names|{'COMPLETED.json'})
    if m['files']!={n:digest((root/n).read_bytes()) for n in names}: raise ValueError('Team file integrity mismatch')
    receipt=dict(sourceCollection=SOURCE_PIN,files=hashes(root/'source/matchups'),copy='PHYSICAL_SELF_CONTAINED',reader='matchup_w12 full reader; own aggregate reconciliation')
    if json.loads((root/'source-receipt.json').read_bytes())!=receipt:raise ValueError('Team source receipt mismatch')
    actual,docs=derive(root)
    if b!=actual or any((root/'teams'/(t+'.json')).read_bytes()!=v for t,v in docs.items()): raise ValueError('Team derivation mismatch')
    return index,docs,m


def publish(output,populate):
    output=safe(output)
    if output.exists(): raise ValueError('New destination required')
    output.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.'+output.name+'.pending-',dir=output.parent))
    try:
        populate(stage);index,docs=derive(stage);(stage/'index.json').write_bytes(index);(stage/'teams').mkdir()
        for team,b in docs.items():(stage/'teams'/(team+'.json')).write_bytes(b)
        m=dict(version=VERSION,bundleId=digest(index),files=hashes(stage));(stage/'COMPLETED.json').write_bytes(encoded(m));read(stage,m['bundleId']);rename_exclusive(stage,output);return m
    finally:
        if stage.exists():shutil.rmtree(stage)


def generate(source,output,policy):
    source,output=safe(source),safe(output)
    if source==output or source in output.parents or output in source.parents:raise ValueError('Disjoint roots required')
    read_matchups(source,SOURCE_PIN);before=hashes(source)
    def populate(stage):
        shutil.copytree(source,stage/'source/matchups');(stage/'request.json').write_bytes(encoded(REQUEST));(stage/'policy.md').write_text(policy)
        (stage/'source-receipt.json').write_bytes(encoded(dict(sourceCollection=SOURCE_PIN,files=before,copy='PHYSICAL_SELF_CONTAINED',reader='matchup_w12 full reader; own aggregate reconciliation')))
        if hashes(source)!=before:raise ValueError('Source changed during copy')
    return publish(output,populate)


def reproduce(source,output):
    source,output=safe(source),safe(output)
    if source==output or source in output.parents or output in source.parents:raise ValueError('Disjoint roots required')
    _,_,original=read(source)
    def populate(stage):
        shutil.copytree(source/'source',stage/'source')
        for n in ('request.json','policy.md','source-receipt.json'):shutil.copyfile(source/n,stage/n)
    m=publish(output,populate)
    if m!=original or hashes(source)!=hashes(output):raise ValueError('Reproduction differs')
    return m
