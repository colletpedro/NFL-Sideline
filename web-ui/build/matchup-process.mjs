// Operator-only adapter. Reuses the unmodified full Python reader, no shell/env file.
import { execFile } from 'node:child_process';
import { isAbsolute } from 'node:path';
import { createHash } from 'node:crypto';
const repo = decodeURIComponent(new URL('../../',import.meta.url).pathname);
export function matchupPort() {
  const raw=process.env.NFL_LOCAL_JOURNEY_PORT??'18102';
  if(!/^[1-9][0-9]{3,4}$/.test(raw)||Number(raw)>65535)throw new Error('Invalid strict pilot port');
  return Number(raw);
}
const code = `import json,sys
from pathlib import Path
from nfl_sideline_etl.comparison_foundation.package import read
from nfl_sideline_etl.situational import safe,digest
c=json.loads(safe(Path(sys.argv[1])).read_bytes())
assert set(c)=={'configVersion','path','expectedBundleId'} and c['configVersion']=='broadcast-matchup-source-v1'
p=safe(Path(c['path']));d,m=read(p,c['expectedBundleId'])
b=(p/'comparison.json').read_bytes();assert digest(b)==m['bundleId']
sys.stdout.buffer.write(b)
`;
export async function prepareComparison() {
  const config = process.env.NFL_MATCHUP_CONFIG, python = process.env.NFL_OBSERVATION_PYTHON;
  if (!config || !python || !isAbsolute(config) || !isAbsolute(python)) throw new Error('Explicit operator configuration required');
  const bytes = await new Promise((resolve,reject) => {
    const child = execFile(python,['-B','-c',code,config], {cwd:repo,shell:false,encoding:'utf8',timeout:120000,maxBuffer:2*1024*1024,
      env:{PATH:process.env.PATH,LANG:'C.UTF-8',PYTHONPATH:repo+'etl-pipeline/src',PYTHONDONTWRITEBYTECODE:'1'}},
    (err,stdout) => { process.removeListener('exit',stop);err ? reject(err) : resolve(stdout); });
    const stop=()=>child.kill('SIGTERM');process.once('exit',stop);
  });
  return {bytes,pin:'sha256:'+createHash('sha256').update(bytes).digest('hex')};
}
