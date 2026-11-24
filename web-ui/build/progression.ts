import type {Plugin} from 'vite';
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {allowedLabRequest} from './risk-lab';
import {validateIndex,validateDetail,type Index} from '../broadcast-journey/progression/model';
const sha=(b:Buffer)=>createHash('sha256').update(b).digest('hex');
export async function progressionFiles(store:string,id:string){
 if(!/^[a-f0-9]{24}$/.test(id))throw new Error('Invalid progression version');
 const base=join(store,'packages',id),manifest=JSON.parse(await readFile(join(base,'integrity.json'),'utf8')) as {schemaVersion:number;files:Record<string,string>},files:Record<string,Buffer>={};
 if(manifest.schemaVersion!==2)throw new Error('Incompatible progression schema');
 for(const [path,h] of Object.entries(manifest.files)){
  if(!/^(index|sources|history|reconciliation)\.json$|^classification-transition\.csv$|^plays\.parquet$|^players\/00-\d{7}\.json$/.test(path))throw new Error('Unsafe progression file');
  const b=await readFile(join(base,path));if(sha(b)!==h)throw new Error('Corrupt progression package');if(path==='index.json'||path.startsWith('players/'))files[path]=b;
 }
 const index=validateIndex(JSON.parse(files['index.json'].toString()));if(index.packageId!==id)throw new Error('Version mismatch');for(const p of index.players)validateDetail(JSON.parse(files[`players/${p.id}.json`].toString()),index,p.id);return {files,index};
}
export function progressionBoundary(store:string,port:number):Plugin{
 const cache=new Map<string,Promise<{files:Record<string,Buffer>;index:Index}>>();
 function version(id:string){if(!cache.has(id))cache.set(id,progressionFiles(store,id).catch(e=>{cache.delete(id);throw e;}));return cache.get(id)!;}
 return {name:'progression-local-package',configureServer(server){server.middlewares.use(async(req,res,next)=>{
  if(!req.url?.startsWith('/__progression/')){next();return;}
  res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
  try{
   if(!allowedLabRequest(req.method,req.headers.host,req.headers,port,req.rawHeaders)){res.statusCode=403;res.end('{"error":"REQUEST_REFUSED"}');return;}
   if(req.url==='/__progression/index.json'){const pointer=JSON.parse(await readFile(join(store,'current.json'),'utf8'));if(pointer.schemaVersion!==2)throw new Error();const {files,index}=await version(pointer.packageId);if(sha(files['index.json'])!==pointer.indexSha256)throw new Error();res.end(JSON.stringify({...index,checkedAt:pointer.checkedAt}));return;}
   const m=req.url.match(/^\/__progression\/packages\/([a-f0-9]{24})\/players\/(00-\d{7})\.json$/);if(!m){res.statusCode=404;res.end('{"error":"ABSENT"}');return;}const {files}=await version(m[1]);const b=files[`players/${m[2]}.json`];res.statusCode=b?200:404;res.end(b??'{"error":"PLAYER_ABSENT"}');
  }catch{res.statusCode=503;res.end('{"error":"PACKAGE_UNAVAILABLE"}');}
 });}};
}
