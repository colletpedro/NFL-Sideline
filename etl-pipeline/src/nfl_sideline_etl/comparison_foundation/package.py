"""No-clobber physical package, full readers, deterministic reproduction."""
import json
from pathlib import Path
import shutil
import tempfile

from ..situational import read as read_situational, safe, digest, encoded, RAW_HASH, MATERIALIZATION, INPUT
from ..metrics_observations.publication import read as read_observations, exact_tree
from ..metrics_observations.lineage import load_source
from ..offline_metrics.artifact import rename_exclusive
from . import VERSION, SITUATIONAL_PIN, OBSERVATION_PIN, GAME
from .project import project

REQUEST = dict(requestVersion='broadcast-comparison-request-v1', gameId=GAME, season=2026, phase='REG', weeks=[1],
               offenses=['NYJ', 'TEN'], epaFoundations=['general', 'classified_pass', 'classified_rush'],
               league=dict(season=2026, phase='REG', weeks=[1], perspective='off', families=['third', 'redZone']),
               context='RETROSPECTIVE', situationalBundleId=SITUATIONAL_PIN, observationBundleId=OBSERVATION_PIN)


def hashes(root):
    root = safe(root)
    if not root.is_dir() or any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in root.rglob('*')):
        raise ValueError('Physical source directory required')
    return {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}


def verified_sources(situational, observations):
    s, sm = read_situational(situational)
    o, om = read_observations(observations)
    if sm['bundleId'] != SITUATIONAL_PIN or om['bundleId'] != OBSERVATION_PIN or len(o) != 588:
        raise ValueError('Preserved source identities differ')
    temporal = json.loads((observations/'shared-source/input.json').read_bytes())
    return s, json.loads((situational/'ledger.json').read_bytes()), o, temporal


def preflight(situational, observations, recovery, backup):
    before = {str(p): hashes(p) for p in (situational, observations, recovery, backup)}
    if before[str(recovery)] != before[str(backup)]:
        raise ValueError('Recovery/backup differ')
    for root in (recovery, backup):
        _, lineage = load_source(root/'materialized')
        if lineage['materialization_id'] != MATERIALIZATION or lineage['temporalInputId'] != INPUT:
            raise ValueError('Recovery lineage mismatch')
        if digest((root/'data/raw/pbp/season=2026/pbp.parquet').read_bytes()) != RAW_HASH:
            raise ValueError('Recovery PBP mismatch')
        _, marker = read_observations(root/'bundle')
        if not marker['bundleId']:
            raise ValueError('Recovery observation identity absent')
    verified_sources(situational, observations)
    if any(hashes(Path(p)) != h for p, h in before.items()):
        raise ValueError('Source changed during preflight')
    return dict(receiptVersion='broadcast-comparison-source-receipt-v1', sources=before,
                fullReaders=dict(situational=1, observations588=1, originalRecovery=1, backupRecovery=1),
                materializationId=MATERIALIZATION, temporalInputId=INPUT, pbpHash=RAW_HASH,
                claims='Operational integrity and derivation only; historical availability/completeness/model remain UNKNOWN')


def derive(root):
    request = json.loads((root/'request.json').read_bytes())
    if request != REQUEST:
        raise ValueError('Only the nominal retrospective pilot request is supported')
    s, ledger, obs, temporal = verified_sources(root/'sources/situational', root/'sources/observations')
    return project(s, ledger, obs, temporal, root/'sources/situational/pbp.parquet', request,
                   (root/'policy.md').read_text(), json.loads((root/'source-receipt.json').read_bytes()), (root/'definitions.md').read_text())


def generate(output, situational, observations, request, policy, receipt, definitions):
    output = safe(output)
    if output.exists():
        raise ValueError('New destination required; overwriting forbidden')
    if request != REQUEST:
        raise ValueError('Unsupported nominal request')
    verified_sources(situational, observations)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.'+output.name+'.pending-', dir=output.parent))
    try:
        (stage/'sources').mkdir()
        shutil.copytree(situational, stage/'sources/situational')
        shutil.copytree(observations, stage/'sources/observations')
        (stage/'request.json').write_bytes(encoded(request))
        (stage/'policy.md').write_text(policy)
        (stage/'definitions.md').write_text(definitions)
        (stage/'source-receipt.json').write_bytes(encoded(receipt))
        (stage/'comparison.json').write_bytes(encoded(derive(stage)))
        marker = dict(version=VERSION, bundleId=digest((stage/'comparison.json').read_bytes()), files=hashes(stage))
        (stage/'COMPLETED.json').write_bytes(encoded(marker))
        read(stage, marker['bundleId'])
        rename_exclusive(stage, output)
        return marker
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def read(root, expected_pin=None):
    root = safe(root)
    # Fixed source trees checked by their original readers, then the entire new tree.
    marker = json.loads((root/'COMPLETED.json').read_bytes())
    top = {'comparison.json', 'request.json', 'policy.md', 'source-receipt.json', 'definitions.md'}
    names = top | {'sources/'+name+'/'+f for name in ('situational', 'observations')
                   for f in hashes(root/'sources'/name)}
    exact_tree(root, names | {'COMPLETED.json'})
    if set(marker) != {'version', 'bundleId', 'files'} or marker['version'] != VERSION:
        raise ValueError('Invalid package marker')
    if marker['files'] != {n: digest((root/n).read_bytes()) for n in names}:
        raise ValueError('Package hash mismatch')
    if expected_pin is not None and marker['bundleId'] != expected_pin:
        raise ValueError('Configured bundle pin mismatch')
    b = (root/'comparison.json').read_bytes()
    if marker['bundleId'] != digest(b) or encoded(derive(root)) != b:
        raise ValueError('Comparison derivation mismatch')
    return json.loads(b), marker


def reproduce(source, output):
    _, original = read(source)
    marker = generate(output, source/'sources/situational', source/'sources/observations',
                      json.loads((source/'request.json').read_bytes()), (source/'policy.md').read_text(),
                      json.loads((source/'source-receipt.json').read_bytes()), (source/'definitions.md').read_text())
    if marker != original or hashes(source) != hashes(output):
        raise ValueError('Reproduction differs')
    return marker
