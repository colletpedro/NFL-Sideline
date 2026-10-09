"""Offline verification against the accepted canonicalization and adapter."""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import tempfile

from ..offline_metrics.artifact import VERSIONS, calculate, identity
from ..offline_metrics.inputs import load_json, read_inputs
from .archive import digest, safe_root

FILES = ('manifest.json', 'game-audit.json', 'statistics.json',
         'reconciliation.json', 'limitations.json')


@dataclass(frozen=True)
class Plan:
    result: dict
    artifact_bytes: dict
    source_bytes: dict
    artifact_id: str
    file_hashes: dict
    sets: dict

    def summary(self):
        return {'calculation_id': self.result['manifest.json']['calculation_id'],
                'artifact_id': self.artifact_id, 'sources': len(self.source_bytes),
                'games': len(self.result['game-audit.json']),
                'statistics': len(self.result['statistics.json']),
                'coverage_states': dict(Counter(a['scope'] for a in self.result['game-audit.json'])),
                'database_connected': False}


def prepare(artifact, calendars, pbps, archive):
    safe_root(archive)  # dry-run also refuses the public destination, without mkdir.
    root = Path(artifact)
    buffers = {}
    for name in (*FILES, 'COMPLETED.json'):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Artifact file missing or not regular')
        buffers[name] = path.read_bytes()
    marker = load_json(buffers['COMPLETED.json'])
    if (not isinstance(marker, dict) or
            set(marker) != {'artifactVersion', 'calculation_id', 'files'} or
            marker['artifactVersion'] != VERSIONS['artifact'] or
            set(marker['files']) != set(FILES)):
        raise ValueError('Invalid COMPLETED marker')
    for name in FILES:
        if digest(buffers[name]) != marker['files'][name]:
            raise ValueError('Artifact file hash mismatch')
    result = {name: load_json(buffers[name]) for name in FILES}
    manifest = result['manifest.json']
    if (not isinstance(manifest, dict) or manifest.get('artifactVersion') != VERSIONS['artifact'] or
            manifest.get('versions') != VERSIONS or
            manifest.get('mode') != 'OFFLINE_DRY_RUN'):
        raise ValueError('Unsupported artifact version or structure')
    content = deepcopy(result)
    calculation_id = content['manifest.json'].pop('calculation_id', None)
    if calculation_id != identity(content) or marker['calculation_id'] != calculation_id:
        raise ValueError('Calculation identity mismatch')
    # Explicit files must match the entire descriptor list, including partitions
    # and multiplicity, not just the set of hashes.
    sources = {}
    with tempfile.TemporaryDirectory(prefix='nfl-e5b2-validation-') as temporary:
        paths = {'calendar': [], 'pbp': []}
        for kind, supplied in (('calendar', calendars), ('pbp', pbps)):
            for ordinal, original in enumerate(supplied):
                original = Path(original)
                data = original.read_bytes()
                sha = digest(data)
                sources[sha] = (data, {'kind': kind, 'source_format': original.suffix,
                                       'supplied_path': str(original.resolve())})
                snapshot = Path(temporary) / f'{kind}-{ordinal}{original.suffix}'
                snapshot.write_bytes(data)
                paths[kind].append(snapshot)
        calendar_rows, plays, descriptors = read_inputs(paths['calendar'], paths['pbp'])
    descriptors = sorted(descriptors, key=lambda i: (i['kind'], i['sha256']))
    if descriptors != manifest.get('inputs'):
        raise ValueError('Explicit sources do not match artifact manifest')
    metadata = deepcopy(manifest['metadata'])
    if metadata == {'metadataVersion': 1, 'games': {}, 'sources': {}}:
        metadata = None
    else:
        for kind in ('calendar', 'pbp'):
            metadata[f'{kind}_sha256'] = sorted({i['sha256'] for i in descriptors if i['kind'] == kind})
    recomputed = calculate(calendar_rows, plays, descriptors, metadata,
                           seasons=manifest['requested_seasons'])
    if recomputed != result:
        raise ValueError('Artifact semantic validation failed against original sources')
    # Immutable snapshot in memory: no rereading untrusted paths during SQL.
    file_hashes = {name: digest(data) for name, data in sorted(buffers.items())}
    sets = {kind: [d for d in descriptors if d['kind'] == kind] for kind in ('calendar', 'pbp')}
    return Plan(result, buffers, sources, identity(file_hashes), file_hashes, sets)


def validate_plan(plan, archive):
    """Reverify Python callers too; mutable nested structures are not a trust boundary."""
    with tempfile.TemporaryDirectory(prefix='nfl-e5b2-reverify-') as temporary:
        root = Path(temporary)
        artifact = root / 'artifact'
        artifact.mkdir()
        for name in (*FILES, 'COMPLETED.json'):
            (artifact / name).write_bytes(plan.artifact_bytes[name])
        paths = {'calendar': [], 'pbp': []}
        for kind, descriptors in plan.sets.items():
            for ordinal, descriptor in enumerate(descriptors):
                data, origin = plan.source_bytes[descriptor['sha256']]
                path = root / f"{kind}-{ordinal}{origin['source_format']}"
                path.write_bytes(data)
                paths[kind].append(path)
        verified = prepare(artifact, paths['calendar'], paths['pbp'], archive)
        if (verified.result != plan.result or verified.artifact_id != plan.artifact_id or
                verified.file_hashes != plan.file_hashes or verified.sets != plan.sets or
                set(verified.source_bytes) != set(plan.source_bytes)):
            raise ValueError('Persistence plan differs from verified artifact')
