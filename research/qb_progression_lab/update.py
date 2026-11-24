"""Explicit refresh with v1 rules fixed, DES v2 projection, own pointer only."""
import argparse,sys,subprocess
from pathlib import Path
from package import publish,SCI,STORE,sha,read,write,CLASSIFICATION,SCHEMA
import package as fixed_package

def verify_fixed(index):
 if index.get("schemaVersion")!=SCHEMA or index.get("classificationVersion")!=CLASSIFICATION or index.get("codeSha256")!=sha(fixed_package.__file__):raise ValueError("Fixed v2 classification differs; review before updating")
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--store',default=str(STORE));a.add_argument('--frozen-science');a.add_argument('--sources');a.add_argument('--fixed-index');a.add_argument('--out',required=True);v=a.parse_args();out=Path(v.out)
 if out.exists():raise FileExistsError('Preserve previous update directory')
 fixed_index=Path(v.fixed_index) if v.fixed_index else Path(v.store)/'packages'/read(Path(v.store)/'current.json')['packageId']/'index.json'
 verify_fixed(read(fixed_index))
 out.mkdir(parents=True)
 if v.frozen_science:science=Path(v.frozen_science)
 else:
  cmd=[sys.executable,str(Path(__file__).parents[1]/'qb_structure_production/update.py'),'--fixed',str(SCI/'package-release/fixed.json'),'--previous',str(SCI/'package-release'),'--out',str(out/'scientific')]
  if v.sources:cmd+=['--frozen-sources',v.sources]
  subprocess.run(cmd,check=True);science=out/'scientific/package'
 prior=read(Path(v.store)/'current.json') if (Path(v.store)/'current.json').exists() else None
 root=publish(science,v.store);write(out/'receipt.json',dict(passed=True,classificationVersion='2.0.0',metricVersion='1.0.0',scientificManifestSha256=sha(science/'manifest.json'),previous=prior,packageId=root.name,onlyOwnPointer=True))
