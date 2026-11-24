import {execFile} from 'node:child_process';
import {isAbsolute} from 'node:path';
const repo=decodeURIComponent(new URL('../../',import.meta.url).pathname);
export function prepareTeam(){
 const config=process.env.NFL_TEAM_CONFIG,python=process.env.NFL_OBSERVATION_PYTHON;
 if(!config||!python||!isAbsolute(config)||!isAbsolute(python))return Promise.reject(new Error('Explicit team source configuration required'));
 return new Promise((resolve,reject)=>{const child=execFile(python,['-B','-m','nfl_sideline_etl.team_w12','serve-snapshot','--config',config],{cwd:repo,shell:false,encoding:'utf8',timeout:120000,maxBuffer:64*1024*1024,env:{PATH:process.env.PATH,LANG:'C.UTF-8',PYTHONPATH:repo+'etl-pipeline/src',PYTHONDONTWRITEBYTECODE:'1'}},(error,stdout)=>{process.removeListener('exit',stop);if(error)reject(error);else{try{resolve(JSON.parse(stdout));}catch(e){reject(e);}}});const stop=()=>child.kill('SIGTERM');process.once('exit',stop);});
}
