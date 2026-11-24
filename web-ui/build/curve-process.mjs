import {execFile} from 'node:child_process';
import {isAbsolute} from 'node:path';
const repo=decodeURIComponent(new URL('../../',import.meta.url).pathname);
export function prepareCurve(){
 const config=process.env.NFL_CURVE_EVENTS_CONFIG,python=process.env.NFL_OBSERVATION_PYTHON;
 if(!config||!python||!isAbsolute(config)||!isAbsolute(python))return Promise.reject(new Error('Explicit game story configuration required'));
 return new Promise((resolve,reject)=>{const child=execFile(python,['-B','-m','nfl_sideline_etl.score_curve','serve-snapshot','--config',config],{cwd:repo,shell:false,encoding:'utf8',timeout:120000,maxBuffer:32*1024*1024,env:{PATH:process.env.PATH,LANG:'C.UTF-8',PYTHONPATH:repo+'etl-pipeline/src',PYTHONDONTWRITEBYTECODE:'1'}},(error,stdout)=>{process.removeListener('exit',stop);if(error)reject(error);else{try{resolve(JSON.parse(stdout));}catch(e){reject(e);}}});const stop=()=>child.kill('SIGTERM');process.once('exit',stop);});
}
