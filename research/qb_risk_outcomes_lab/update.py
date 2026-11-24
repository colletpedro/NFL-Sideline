"""Explicit research fixed-model apply → validate → immutable package → atomic B2 activation."""
from pathlib import Path
import argparse,subprocess,sys,datetime
from package import publish,DEFAULT,SCIENTIFIC,M3_STORE,safe_store,read,sha,MODEL_SHA,ROOT
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--store',default=str(DEFAULT));a.add_argument('--sources',help='Pinned current acquisition directory; omission explicitly acquires new public copies');a.add_argument('--final',default=str(SCIENTIFIC/'final'));a.add_argument('--m3-store',default=str(M3_STORE));v=a.parse_args()
 store=safe_store(v.store);assert sha(Path(v.final)/'model.json')==MODEL_SHA
 dest=store/'applications'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 cmd=[sys.executable,str(ROOT/'research/qb_expected_interceptions/update.py'),'--final',v.final,'--out',str(dest)]
 if v.sources:cmd+=['--sources',v.sources]
 subprocess.run(cmd,check=True)
 # Research update intentionally produces but never activates. Activation below affects only B2.
 source=Path(v.sources) if v.sources else dest/'sources'
 print(publish(dest/'application',source,store,v.m3_store))
