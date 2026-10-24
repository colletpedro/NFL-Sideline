import {createHash} from 'node:crypto';
export const hash=b=>'sha256:'+createHash('sha256').update(b).digest('hex');
import {execFile} from 'node:child_process';
import {isAbsolute} from 'node:path';
const repo=decodeURIComponent(new URL('../../',import.meta.url).pathname);
export async function prepareW12(){
  const config=process.env.NFL_W12_CONFIG,python=process.env.NFL_OBSERVATION_PYTHON;
  if(!config||!python||!isAbsolute(config)||!isAbsolute(python))throw new Error('Explicit operator configuration required');
  return new Promise((resolve,reject)=>{
    const child=execFile(python,['-B','-m','nfl_sideline_etl.matchup_w12','serve-snapshot','--config',config],{cwd:repo,shell:false,encoding:'utf8',timeout:120000,maxBuffer:24*1024*1024,
      env:{PATH:process.env.PATH,LANG:'C.UTF-8',PYTHONPATH:repo+'etl-pipeline/src',PYTHONDONTWRITEBYTECODE:'1'}},(err,stdout)=>{process.removeListener('exit',stop);if(err)reject(err);else{try{resolve(JSON.parse(stdout));}catch(e){reject(e);}}});
    const stop=()=>child.kill('SIGTERM');process.once('exit',stop);
  });
}
