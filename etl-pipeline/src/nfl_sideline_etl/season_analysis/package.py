"""Self-contained immutable sources, semantic verification and exact reproduction."""
import json
from pathlib import Path
import shutil
import tempfile

from ..situational import encoded, digest, safe
from ..offline_metrics.artifact import rename_exclusive
from . import VERSION
from .project import derive


def hashes(root):
    files={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError('Symlink inside package')
        if p.is_file():files[p.relative_to(root).as_posix()]=digest(p.read_bytes())
    return files


def source_check(source):
    receipts=json.loads((source/'receipts.json').read_bytes())
    if {r['file'] for r in receipts}!={'pbp.parquet','schedules.parquet'} or len(receipts)!=2:raise ValueError('Source receipts required')
    if set(hashes(source))!={'receipts.json','pbp.parquet','schedules.parquet'}:raise ValueError('Unexpected source files')
    for r in receipts:
        b=(source/r['file']).read_bytes()
        if digest(b)!=r['sha256'] or len(b)!=r['bytes'] or not r['url'].startswith('https://github.com/nflverse/nflverse-data/releases/download/'):raise ValueError('Source receipt mismatch')


def read(root, pin=None, rederive=True):
    root=safe(root);marker=json.loads((root/'COMPLETED.json').read_bytes())
    if marker['version']!=VERSION:raise ValueError('Wrong package version')
    actual=hashes(root);actual.pop('COMPLETED.json')
    if marker['files']!=actual:raise ValueError('Package byte inventory mismatch')
    index=(root/'index.json').read_bytes();actual_pin=digest(index)
    if actual_pin!=marker['bundleId'] or pin is not None and pin!=actual_pin:raise ValueError('Package pin mismatch')
    source_check(root/'source')
    if rederive:
        _,files=derive(root/'source')
        expected=set(files)|{'source/'+x for x in hashes(root/'source')}
        if set(actual)!=expected or any((root/p).read_bytes()!=b for p,b in files.items()):raise ValueError('Package semantic reproduction mismatch')
    return json.loads(index),marker


def generate(source,output):
    source,output=safe(source),safe(output)
    if output.exists() or source==output or source in output.parents or output in source.parents:raise ValueError('Disjoint new destination required')
    source_check(source);before=hashes(source);output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.'+output.name+'.pending-',dir=output.parent))
    try:
        shutil.copytree(source,stage/'source')
        if before!=hashes(source) or before!=hashes(stage/'source'):raise ValueError('Source changed during copy')
        index,files=derive(stage/'source')
        for name,b in files.items():
            p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        marker=dict(version=VERSION,bundleId=digest(encoded(index)),files=hashes(stage))
        (stage/'COMPLETED.json').write_bytes(encoded(marker));read(stage,marker['bundleId']);rename_exclusive(stage,output)
        return marker
    finally:
        if stage.exists():shutil.rmtree(stage)


def reproduce(source,output):
    _,original=read(source)
    marker=generate(Path(source)/'source',output)
    if marker!=original or hashes(Path(source))!=hashes(Path(output)):raise ValueError('Nonidentical reproduction')
    return marker
