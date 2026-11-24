from pathlib import Path
import os,subprocess,json,hashlib
root=Path(__file__).resolve().parents[3];out=root/'docs/plans/broadcast-reading-polish-v1/checks';web=root/'web-ui'
env={**os.environ,'PATH':'/opt/homebrew/opt/node@24/bin:'+os.environ['PATH']}
commands=[('lint',['npm','run','lint']),('typescript-journey',['npx','tsc','-p','tsconfig.journey.json']),('typescript-polish',['npx','tsc','-p','tsconfig.reading-polish.json'])]
for name in ['reading-polish','hub-team','journey','matchup','w12']:
 config='journey' if name=='journey' else name
 commands.extend([(f'typescript-{name}-config',['npx','tsc','-p',f'tsconfig.{config}.json']),(f'build-{name}',['npx','vite','build','--config',f'vite.{name}.config.ts'])])
commands.extend([('build-real',['npm','run','real:build']),('build-experience',['npm','run','experience:build']),('build-public',['npm','run','build'])])
records=[]
for name,cmd in commands:
 log=out/(name+'.log')
 with log.open('w') as f:p=subprocess.run(cmd,cwd=web,env=env,stdout=f,stderr=subprocess.STDOUT)
 records.append(dict(name=name,command=cmd,exit=p.returncode));print(name,p.returncode,flush=True)
 if p.returncode:raise SystemExit(log.read_text())
# Production selection remains fixed under hostile runtime-looking variables.
with (out/'build-public-hostile.log').open('w') as f:
 p=subprocess.run(['npm','run','build'],cwd=web,env={**env,'VITE_API_BASE_URL':'http://127.0.0.1:18106','VITE_RUNTIME_CLIENT':'development','VITE_DATA_SOURCE':'api'},stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==0
hashes={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (web/'dist/assets').glob('*') if p.suffix in {'.js','.css'}}
assert hashes=={'.js':'73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5','.css':'2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
(out/'builds.json').write_text(json.dumps(dict(commands=records,hostilePublicBuild=0,publicHashes=hashes),indent=2)+'\n')
print('PASS: eight builds, TypeScript, lint and fixed public hashes',flush=True)
