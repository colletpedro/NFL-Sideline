"""Focused isolation/HTTP receipt after the EPA copy edit; not a human reconfirmation."""
from http.client import HTTPConnection
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE='68eaf4179de72c6accc56749f9d4565666a23536'
REF=Path('/Users/pedrocollet/.codex/worktrees/broadcast-matchup-reading-v1/NFL Sideline')
PIN='sha256:b10a2028f26d6acc229f80bbd27269016dd2e6b2e4b432a6d8a9109f643e5ee4'
CHART='web-ui/broadcast-journey/matchup/Charts.tsx'
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd)
assert git('rev-parse','HEAD',cwd=REF).decode().strip()=='c5be5b0dbb525faea85fab350039d8a5c1c87af5'
assert not git('status','--porcelain',cwd=REF)
changed=set(git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines())
assert all(p==CHART or p.startswith('docs/plans/broadcast-comprehension-v1/') for p in changed)
# Scope check, not a test tied to the literal copy: only the first unit paragraph may differ.
def without_unit(text):return re.sub(r'<p className="mr-unit">[^<]*</p>','<EPA_UNIT_COPY/>',text,count=1)
assert without_unit((ROOT/CHART).read_text())==without_unit(git('show',BASE+':'+CHART).decode())
assert git('diff','--numstat',BASE,'--',CHART).decode().split()[:2]==['1','1']
assert not git('diff',BASE,'--','docs/plans/broadcast-comprehension-v1/PROTOCOL.md')
historic=git('ls-tree','-r','--name-only',BASE).decode().splitlines()
untouched=[p for p in historic if p!=CHART and not p.startswith('docs/plans/broadcast-comprehension-v1/')]
assert not git('diff',BASE,'--',*untouched).strip()
assert (ROOT/'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(')==5
public={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/dist/assets').iterdir() if p.suffix in ('.js','.css')}
assert public=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
config=json.loads((ROOT/'docs/plans/broadcast-matchup-reading-v1/source-config.json').read_bytes())
raw=(Path(config['path'])/'comparison.json').read_bytes()
assert PIN==config['expectedBundleId']=='sha256:'+hashlib.sha256(raw).hexdigest()
wire=[]
def get(port,method,path,headers,body=None,expected=200):
 c=HTTPConnection('127.0.0.1',port,timeout=15);c.request(method,path,body=body,headers=headers);r=c.getresponse();b=r.read()
 assert r.status==expected,(port,method,path,r.status)
 if expected==200:assert b==raw and r.getheader('X-Comparison-Bundle')==PIN
 wire.append(dict(port=port,method=method,path=path,status=r.status));c.close()
get(18102,'GET','/__matchup-reading/',{'X-Local-Matchup':'1'})
get(18103,'GET','/__matchup-reading/',{'X-Local-Matchup':'1'})
get(18103,'GET','/__matchup-reading/',{'X-Local-Matchup':'1','Origin':'http://127.0.0.1:18103'})
for method,path,extra,body in [
 ('POST','/__matchup-reading/',{},None),('GET','/__matchup-reading/',{'Origin':'http://127.0.0.1:18102'},None),
 ('GET','/__matchup-reading/',{'Origin':'https://example.com'},None),('GET','/__matchup-reading/',{'Host':'127.0.0.1:18102'},None),
 ('GET','/__matchup-reading/?path=/tmp/other',{},None),('GET','/__matchup-reading/',{'X-Local-Matchup':'0'},None),
 ('GET','/__matchup-reading/',{},'x')]:
 get(18103,method,path,{'X-Local-Matchup':'1',**extra},body,403)
listeners={}
for port,original in json.loads((HERE/'checks/listeners-before.json').read_bytes()).items():
 pid=original.splitlines()[1].split()[1]
 data=subprocess.check_output(['lsof','-nP','-a','-p',pid,f'-iTCP:{port}','-sTCP:LISTEN'],text=True)
 assert f'127.0.0.1:{port}' in data;listeners[port]=int(pid)
server=json.loads((HERE/'checks/closure/server.json').read_bytes())
assert f"127.0.0.1:{server['port']}" in subprocess.check_output(['lsof','-nP','-a','-p',str(server['pid']),f"-iTCP:{server['port']}",'-sTCP:LISTEN'],text=True)
for entry in json.loads((HERE/'results/provenance/manifest.json').read_bytes())['files']:
 assert hashlib.sha256((HERE/entry['preservedAs']).read_bytes()).hexdigest()==entry['sha256']
browser=json.loads((HERE/'evidence/closure/browser.json').read_bytes())
assert browser['humanReconfirmation'] is False and len(browser['cases'])==9
for case in browser['cases']:
 assert case['noPageOverflow'] and case['noParagraphClipping'] and case['noVerticalOverlap']
 assert case['paragraphCount']==1 and case['thirdMarks']==22 and case['campaigns']==4
 assert len(case['commonDomains'])==2 and case['commonDomains'][0]==case['commonDomains'][1]
assert browser['text200']['noPageOverflow'] and browser['text200']['noClipping'] and browser['text200']['noOverlap']
assert browser['restored']['font']=='16px' and not browser['consoleErrors']
subprocess.run(['git','diff','--check',BASE],cwd=ROOT,check=True)
report=dict(kind='TECHNICAL_CLOSURE_ONLY',humanParticipantCount=1,humanReconfirmation=False,base=BASE,
 referenceCleanAtOriginalHead=True,onlyApplicationChange='first EPA unit paragraph; one line replaced',unchangedHistoricalFilesOutsideStudyDocs=len(untouched),
 originalProtocolUnchanged=True,sourcePin=PIN,bytes=len(raw),referenceAndRefinedEqualArtifact=True,httpCases=wire,
 publicBuildHashes=public,fiveLegacyExpectedFailuresPreserved=True,oldListeners= listeners,refined=server,
 sourceRecordCopiesVerified=True,browserMatrixCases=9,text200Verified=True,rawHistoricalReconciliationRerun=False)
(HERE/'checks/closure/isolation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Focused closure PASS: one paragraph, original protocol/reference, exact pin/HTTP, Host/Origin refusals, public hashes and existing listeners preserved. No human reconfirmation claimed.')
