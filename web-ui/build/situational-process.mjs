// Operator process adapter; follows the existing local observation boundary.
import { execFile } from 'node:child_process';
import { isAbsolute } from 'node:path';
export async function prepareSituational() {
  const config=process.env.NFL_SITUATIONAL_CONFIG, python=process.env.NFL_OBSERVATION_PYTHON;
  if (!config && !python) return null;
  if (!config || !python || !isAbsolute(config) || !isAbsolute(python)) return null;
  const stdout=await new Promise((resolve,reject)=>{
    const child=execFile(python,['-B','-m','nfl_sideline_etl.situational','serve-snapshot','--config',config],{
      cwd:decodeURIComponent(new URL('../../',import.meta.url).pathname),shell:false,encoding:'utf8',timeout:120000,maxBuffer:4*1024*1024,
      env:{PATH:process.env.PATH,LANG:'C.UTF-8',PYTHONPATH:decodeURIComponent(new URL('../../etl-pipeline/src',import.meta.url).pathname),PYTHONDONTWRITEBYTECODE:'1'},
    },(error,output)=>{process.removeListener('exit',stop);error?reject(error):resolve(output)});
    const stop=()=>child.kill('SIGTERM');process.once('exit',stop);
  });
  return JSON.parse(stdout);
}
