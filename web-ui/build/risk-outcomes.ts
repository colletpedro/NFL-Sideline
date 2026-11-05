import type {Plugin} from 'vite';
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {allowedLabRequest} from './risk-lab';
import {validateOutcomeIndex,validateOutcomeDetail,type OutcomeIndex} from '../broadcast-journey/risk-outcomes/model';
const sha=(b:Buffer)=>createHash('sha256').update(b).digest('hex');
export async function outcomeFiles(store:string,id:string){
 if(!/^[a-f0-9]{24}$/.test(id))throw new Error('Invalid B2 version');
 const base=join(store,'packages',id),manifest=JSON.parse(await readFile(join(base,'integrity.json'),'utf8')) as {files:Record<string,string>},files:Record<string,Buffer>={};
 for(const [path,digest] of Object.entries(manifest.files)){
  if(!/^(index|sources)\.json$|^players\/00-\d{7}\.json$/.test(path))throw new Error('Unsafe B2 package path');
  const bytes=await readFile(join(base,path));if(sha(bytes)!==digest)throw new Error('B2 package corrupt');files[path]=bytes;
 }
 const index=validateOutcomeIndex(JSON.parse(files['index.json'].toString()));if(index.packageId!==id)throw new Error('B2 version mismatch');
 for(const p of index.players)validateOutcomeDetail(JSON.parse(files[`players/${p.id}.json`].toString()),index,p.id);
 return {files,index};
}
export async function activeOutcome(store:string){
 const current=JSON.parse(await readFile(join(store,'current.json'),'utf8')) as {packageId:string;indexSha256:string;checkedAt:string};
 const result=await outcomeFiles(store,current.packageId);if(sha(result.files['index.json'])!==current.indexSha256)throw new Error('B2 active pointer corrupt');return {current,...result};
}
export function outcomesBoundary(store:string,port:number):Plugin{
 const cache=new Map<string,Promise<{files:Record<string,Buffer>;index:OutcomeIndex}>>();
 function version(id:string){if(!cache.has(id))cache.set(id,outcomeFiles(store,id).catch(e=>{cache.delete(id);throw e;}));return cache.get(id)!;}
 return {name:'risk-outcomes-local-package',configureServer(server){server.middlewares.use(async(req,res,next)=>{
  if(!req.url?.startsWith('/__risk-outcomes/')){next();return;}
  res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
  try{
   if(!allowedLabRequest(req.method,req.headers.host,req.headers,port,req.rawHeaders)){res.statusCode=403;res.end('{"error":"REQUEST_REFUSED"}');return;}
   if(req.url==='/__risk-outcomes/index.json'){
    const current=JSON.parse(await readFile(join(store,'current.json'),'utf8'));const {files,index}=await version(current.packageId);
    if(sha(files['index.json'])!==current.indexSha256)throw new Error('B2 pointer mismatch');res.end(JSON.stringify({...index,checkedAt:current.checkedAt}));return;
   }
   const m=req.url.match(/^\/__risk-outcomes\/packages\/([a-f0-9]{24})\/players\/(00-\d{7})\.json$/);
   if(!m){res.statusCode=404;res.end('{"error":"ABSENT"}');return;}
   const {files}=await version(m[1]);const bytes=files[`players/${m[2]}.json`];if(!bytes){res.statusCode=404;res.end('{"error":"PLAYER_ABSENT"}');return;}res.end(bytes);
  }catch{res.statusCode=503;res.end('{"error":"PACKAGE_UNAVAILABLE"}');}
 });}};
}
