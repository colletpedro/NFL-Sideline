import {execFile} from 'node:child_process';
import {isAbsolute} from 'node:path';
const repo=decodeURIComponent(new URL('../../',import.meta.url).pathname);
export function prepareSeason(){const config=process.env.NFL_SEASON_ANALYSIS_CONFIG,python=process.env.NFL_OBSERVATION_PYTHON;if(!config||!python||!isAbsolute(config)||!isAbsolute(python))return Promise.reject(new Error('Explicit season source config required'));
 return new Promise((resolve,reject)=>{const child=execFile(python,['-B','-m','nfl_sideline_etl.season_analysis','serve-snapshot','--config',config],{cwd:repo,shell:false,encoding:'utf8',timeout:120000,maxBuffer:128*1024*1024,env:{PATH:process.env.PATH,LANG:'C.UTF-8',PYTHONPATH:repo+'etl-pipeline/src',PYTHONDONTWRITEBYTECODE:'1'}},(error,out)=>{process.removeListener('exit',stop);if(error)reject(error);else try{resolve(JSON.parse(out));}catch(e){reject(e);}});const stop=()=>child.kill('SIGTERM');process.once('exit',stop);});}
