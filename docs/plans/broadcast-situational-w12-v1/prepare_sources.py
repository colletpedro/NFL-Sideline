"""Verify preserved sources in full before any new situational calculation."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'etl-pipeline/src'))
sys.path.insert(0,str(ROOT/'docs/plans/broadcast-w12-expansion-v1'))
from nominal_selection import hashes
from nfl_sideline_etl.metrics_observations.lineage import load_source
from nfl_sideline_etl.metrics_observations.publication import read
from nfl_sideline_etl.situational import RAW_HASH, MATERIALIZATION, INPUT, digest, save

SOURCE=Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/20261019T024130Z-50e03b27')
BACKUP=SOURCE.parents[1]/'backups'/SOURCE.name
OLD=Path('/Users/pedrocollet/.codex/worktrees/broadcast-w12-expansion-v1/NFL Sideline/editorial/local-artifacts/broadcast-w12-expansion-v1/20261022-v1/bundle')
OUT=Path(sys.argv[1]); OUT.mkdir(parents=True,exist_ok=False)
a=hashes(SOURCE);assert a==hashes(BACKUP)
for path in (SOURCE,BACKUP):
 temporal,lineage=load_source(path/'materialized')
 assert lineage['materialization_id']==MATERIALIZATION and lineage['temporalInputId']==INPUT
 assert digest((path/'data/raw/pbp/season=2026/pbp.parquet').read_bytes())==RAW_HASH
_,manifest=read(OLD)
assert manifest['bundleId']=='sha256:05541d2703de6ad55e8858ebfbc17115a6d2747c01a2f73bad78d1eb7566876a'
provenance=dict(verifiedAt=datetime.now(timezone.utc).isoformat(),source=str(SOURCE),backup=str(BACKUP),rawRelativePath='data/raw/pbp/season=2026/pbp.parquet',rawHash=RAW_HASH,materializationId=MATERIALIZATION,inputId=INPUT,sourceHashes=a,backupHashes=a,oldBundlePath=str(OLD),oldBundleId=manifest['bundleId'],oldBundleHashes=hashes(OLD),fullOperationalReaders=3)
save(OUT/'provenance.json',provenance)
print('Verified',len(a),'source files; old bundle pinned; provenance:',OUT/'provenance.json')
