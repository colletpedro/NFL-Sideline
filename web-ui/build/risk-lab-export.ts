import type {Plugin} from 'vite';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {freezeSeason} from './season';
import {freezeStory} from './story';
import {freezeCurve} from './curve';
import {prepareSeason} from './season-process.mjs';
import {prepareStory} from './story-process.mjs';
import {prepareCurve} from './curve-process.mjs';
import {PIN as SEASON_PIN} from '../broadcast-journey/season/model';
import {STORY_PIN} from '../broadcast-journey/game-story/model';
import {CURVE_PIN} from '../broadcast-journey/score-curve/model';
const sha=(b:Buffer|string)=>createHash('sha256').update(b).digest('hex');
export function labExport(store:string):Plugin{return {name:'export-isolated-lab-package',async closeBundle(){
 const out=decodeURIComponent(new URL('../risk-lab-dist',import.meta.url).pathname);const routes:Record<string,{file:string;sha256:string;headers:Record<string,string>}>= {};
 async function add(url:string,bytes:Buffer|string,headers:Record<string,string>={}){const file=`local-data/${sha(url).slice(0,24)}.json`;await mkdir(join(out,'local-data'),{recursive:true});await writeFile(join(out,file),bytes);routes[url]={file,sha256:sha(bytes),headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',...headers}};}
 const active=JSON.parse(await readFile(join(store,'current.json'),'utf8'));if(!/^[a-f0-9]{24}$/.test(active.packageId))throw new Error('Invalid active package');const base=join(store,'packages',active.packageId);const integrity=JSON.parse(await readFile(join(base,'integrity.json'),'utf8'));
 for(const [path,h] of Object.entries(integrity.files)){if(!/^(index|sources|funnel)\.json$|^players\/00-\d{7}\.json$/.test(path))throw new Error('Unsafe package path');const bytes=await readFile(join(base,path));if(sha(bytes)!==h)throw new Error('Corrupt lab package');if(path==='index.json'){if(sha(bytes)!==active.indexSha256)throw new Error('Active pointer mismatch');await add('/__risk-lab/index.json',JSON.stringify({...JSON.parse(bytes.toString()),checkedAt:active.checkedAt}));}else if(path.startsWith('players/'))await add(`/__risk-lab/packages/${active.packageId}/${path}`,bytes);}
 const season=freezeSeason(await prepareSeason());for(const [url,data] of Object.entries(season))await add(url,data.bytes,{'X-Season-Collection':SEASON_PIN,'X-Season-Document':data.hash});
 await add('/__game-story/',freezeStory(await prepareStory()),{'X-Game-Story-Collection':STORY_PIN});
 await add('/__curve-events/',freezeCurve(await prepareCurve()),{'X-Curve-Collection':CURVE_PIN});
 await writeFile(join(out,'local-routes.json'),JSON.stringify({schemaVersion:1,packageId:active.packageId,routes},null,2)+'\n');
 console.info(`Lab build: ${Object.keys(routes).length} frozen GET documents; public snapshots excluded.`);
}};}
