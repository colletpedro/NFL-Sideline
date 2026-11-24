import type {Plugin} from 'vite';
import {readFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
const digest=(b:Buffer)=>createHash('sha256').update(b).digest('hex');
export function allowedLabRequest(method:string|undefined,host:string|undefined,headers:Record<string,string|string[]|undefined>,port:number,raw:string[]=[]){return method==='GET'&&host===`127.0.0.1:${port}`&&(headers.origin===undefined||headers.origin===`http://127.0.0.1:${port}`)&&headers['x-risk-lab']==='1'&&headers.expect===undefined&&headers['transfer-encoding']===undefined&&(headers['content-length']===undefined||headers['content-length']==='0')&&['host','origin','x-risk-lab','content-length','expect','transfer-encoding'].every(h=>raw.filter((v,i)=>i%2===0&&v.toLowerCase()===h).length<=1);}
export function labBoundary(store:string,port:number):Plugin{
 const cache=new Map<string,Promise<Record<string,Buffer>>>();
 async function packageFiles(id:string){if(!cache.has(id))cache.set(id,(async()=>{const base=join(store,'packages',id),manifest=JSON.parse(await readFile(join(base,'integrity.json'),'utf8')) as {files:Record<string,string>},files:Record<string,Buffer>={};for(const [p,h] of Object.entries(manifest.files)){if(!/^(?:index|sources|funnel)\.json$|^players\/00-\d{7}\.json$/.test(p))throw new Error('Package path invalid');const bytes=await readFile(join(base,p));if(digest(bytes)!==h)throw new Error('Package hash invalid');files[p]=bytes;}return files;})());return cache.get(id)!;}
 return {name:'risk-lab-local-package',configureServer(server){server.middlewares.use(async(req,res,next)=>{
  if(!req.url?.startsWith('/__risk-lab/')){next();return;}
  res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
  try{
   if(!allowedLabRequest(req.method,req.headers.host,req.headers,port,req.rawHeaders)) {res.statusCode=403;res.end('{"error":"REQUEST_REFUSED"}');return;}
   if(req.url==='/__risk-lab/index.json'){const current=JSON.parse(await readFile(resolve(store,'current.json'),'utf8')) as {packageId:string;indexSha256:string;checkedAt:string};if(!/^[a-f0-9]{24}$/.test(current.packageId))throw new Error('Invalid active ID');const files=await packageFiles(current.packageId);if(digest(files['index.json'])!==current.indexSha256)throw new Error('Index corrupt');res.end(JSON.stringify({...JSON.parse(files['index.json'].toString()),checkedAt:current.checkedAt}));return;}
   const m=req.url.match(/^\/__risk-lab\/packages\/([a-f0-9]{24})\/players\/(00-\d{7})\.json$/);
   if(!m){res.statusCode=404;res.end('{"error":"ABSENT"}');return;}
   const bytes=(await packageFiles(m[1]))[`players/${m[2]}.json`];if(!bytes){res.statusCode=404;res.end('{"error":"PLAYER_ABSENT"}');return;}res.end(bytes);
  }catch{res.statusCode=503;res.end('{"error":"PACKAGE_UNAVAILABLE"}');}
 });}};
}
