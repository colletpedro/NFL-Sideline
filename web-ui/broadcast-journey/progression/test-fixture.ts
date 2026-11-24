import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {type Index,type Detail} from './model';
export function artifact(){const store=process.env.NFL_PROGRESSION_QA_STORE??'/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-progression-improvisation-lab-v1',pointer=JSON.parse(readFileSync(join(store,'current.json'),'utf8')),base=join(store,'packages',pointer.packageId),index=JSON.parse(readFileSync(join(base,'index.json'),'utf8')) as Index;return {index,detail:(id:string)=>JSON.parse(readFileSync(join(base,'players',id+'.json'),'utf8')) as Detail};}
