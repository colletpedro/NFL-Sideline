"""Atomic no-clobber packages, with byte and derivation checks."""
from pathlib import Path
import shutil
import tempfile

from ..offline_metrics.artifact import ensure_destination, identity, json_bytes, rename_exclusive
from ..offline_metrics.inputs import load_json
from ..metrics_persistence.archive import digest
from ..temporal_metrics.core import canonical
from ..temporal_metrics.validation import validate
from . import MATERIALIZATION_VERSION


def publish(destination, temporal, lineage):
    destination = ensure_destination(destination)
    validate(temporal)
    if lineage['temporalInputId'] != identity(canonical(temporal)) or lineage['materialization_id'] != identity({k: v for k, v in lineage.items() if k != 'materialization_id'}):
        raise ValueError('Materialization identity mismatch')
    data = {'input.json': json_bytes(temporal), 'lineage.json': json_bytes(lineage)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.' + destination.name + '.pending-', dir=destination.parent))
    try:
        for name, raw in data.items():
            (staging / name).write_bytes(raw)
        (staging / 'COMPLETED.json').write_bytes(json_bytes({'materializationVersion': MATERIALIZATION_VERSION,
            'materialization_id': lineage['materialization_id'], 'temporalInputId': lineage['temporalInputId'],
            'files': {n: digest(b) for n, b in data.items()}}))
        rename_exclusive(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def read(destination):
    root = Path(destination)
    if root.is_symlink() or any(p.is_symlink() for p in root.absolute().parents):
        raise ValueError('Materialized package symlink forbidden')
    data = {}
    for name in ('COMPLETED.json', 'input.json', 'lineage.json'):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Materialized file missing or symlink')
        data[name] = path.read_bytes()
    marker = load_json(data['COMPLETED.json'])
    if (set(marker) != {'materializationVersion', 'materialization_id', 'temporalInputId', 'files'} or
            marker['materializationVersion'] != MATERIALIZATION_VERSION or
            marker['files'] != {n: digest(data[n]) for n in ('input.json', 'lineage.json')}):
        raise ValueError('Materialized package hash/version mismatch')
    temporal = load_json(data['input.json']); lineage = load_json(data['lineage.json'])
    if (marker['materialization_id'] != lineage['materialization_id'] or
            marker['temporalInputId'] != lineage['temporalInputId'] or
            lineage['materialization_id'] != identity({k: v for k, v in lineage.items() if k != 'materialization_id'}) or
            lineage['temporalInputId'] != identity(canonical(temporal))):
        raise ValueError('Materialized semantic identity mismatch')
    validate(temporal)
    return temporal, lineage
