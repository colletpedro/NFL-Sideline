"""Self-contained, no-clobber file bundles; read always rederives from originals."""
from pathlib import Path
import shutil
import tempfile

from ..metrics_materialization.publication import read as read_materialization
from ..metrics_materialization.publication import publish as publish_materialization
from ..offline_metrics.artifact import ensure_destination, identity, json_bytes, rename_exclusive
from ..offline_metrics.inputs import load_json
from ..metrics_persistence.archive import digest
from ..temporal_metrics.validation import fields
from . import BUNDLE_VERSION
from .core import project_verified
from .lineage import verify_source

FILES = ('manifest.json', 'request.json', 'observations.json',
         'shared-source/input.json', 'shared-source/lineage.json', 'shared-source/COMPLETED.json')


def safe_path(path):
    path = Path(path)
    if '..' in path.parts or any(p.is_symlink() for p in (path.absolute(), *path.absolute().parents)):
        raise ValueError('Unsafe path or symlink forbidden')
    return path


def exact_tree(root, names):
    safe_path(root)
    require_files = set(names)
    if not root.is_dir():
        raise ValueError('Package directory missing')
    actual = set()
    for child in root.rglob('*'):
        if child.is_symlink() or not (child.is_dir() or child.is_file()):
            raise ValueError('Unsafe package entry')
        if child.is_file():
            actual.add(child.relative_to(root).as_posix())
        else:
            rel = child.relative_to(root).as_posix() + '/'
            if not any(name.startswith(rel) for name in require_files):
                raise ValueError('Unexpected package directory')
    if actual != require_files:
        raise ValueError('Package file/dependency missing or unexpected')


def publish(destination, temporal, lineage, request):
    destination = ensure_destination(safe_path(destination))
    verify_source(temporal, lineage)
    q, documents, manifest = project_verified(temporal, lineage, request)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.' + destination.name + '.pending-', dir=destination.parent))
    try:
        publish_materialization(staging / 'shared-source', temporal, lineage)
        for name, value in (('request.json', q), ('observations.json', documents), ('manifest.json', manifest)):
            (staging / name).write_bytes(json_bytes(value))
        marker = {'bundleVersion': BUNDLE_VERSION, 'bundleId': manifest['bundleId'],
                  'files': {name: digest((staging / name).read_bytes()) for name in FILES}}
        (staging / 'COMPLETED.json').write_bytes(json_bytes(marker))
        rename_exclusive(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return manifest


def generate(materialized, request, destination):
    root = safe_path(materialized)
    exact_tree(root, ('input.json', 'lineage.json', 'COMPLETED.json'))
    temporal, lineage = read_materialization(root)
    return publish(destination, temporal, lineage, request)


def read(root):
    root = safe_path(root)
    exact_tree(root, (*FILES, 'COMPLETED.json'))
    data = {name: (root / name).read_bytes() for name in FILES}
    marker = load_json((root / 'COMPLETED.json').read_bytes())
    fields(marker, ('bundleVersion', 'bundleId', 'files'))
    if marker['bundleVersion'] != BUNDLE_VERSION or marker['files'] != {name: digest(raw) for name, raw in data.items()}:
        raise ValueError('Observation bundle version/hash mismatch')
    temporal, lineage = read_materialization(root / 'shared-source')
    verify_source(temporal, lineage)
    q, documents, manifest = project_verified(temporal, lineage, load_json(data['request.json']))
    expected = {'request.json': q, 'observations.json': documents, 'manifest.json': manifest}
    if (marker['bundleId'] != manifest['bundleId'] or
            any(json_bytes(value) != data[name] for name, value in expected.items())):
        raise ValueError('Observation derivation differs from accepted originals/nominal request')
    return documents, manifest


def inspect(root):
    documents, manifest = read(root)
    return {'bundleVersion': manifest['bundleVersion'], 'bundleId': manifest['bundleId'],
            'source': manifest['source'], 'observationCount': len(documents),
            'observationIds': manifest['observationIds'], 'selfContained': True,
            'temporalGuarantee': 'NOT_DEMONSTRATED', 'comparison': 'NOT_IMPLEMENTED'}
