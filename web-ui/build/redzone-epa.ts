import type {Plugin} from 'vite';
import {prepareRedzoneEpa} from './redzone-epa-process.mjs';
import {hash} from './w12-process.mjs';
import {EPA_PIN,EPA_ENDPOINT,validateEpaData} from '../broadcast-journey/redzone-epa/model';
export function allowedRedzoneRequest(method:string,url:string,headers:Record<string,string|string[]|undefined>,port:number,raw:string[]=[]){
 const unique=['host','origin','x-local-redzone-epa','x-redzone-epa-collection','content-length','expect','transfer-encoding'];
 return method==='GET'&&url===EPA_ENDPOINT&&unique.every(h=>raw.filter((v,i)=>i%2===0&&v.toLowerCase()===h).length<=1)&&headers.host===`127.0.0.1:${port}`&&headers['x-local-redzone-epa']==='1'&&(headers.origin===undefined||headers.origin===`http://127.0.0.1:${port}`)&&headers.expect===undefined&&headers['transfer-encoding']===undefined&&(headers['content-length']===undefined||headers['content-length']==='0');
}
export function freezeRedzoneEpa(input:unknown){const s=input as {bundleId:string;payload:string};if(s.bundleId!==EPA_PIN||typeof s.payload!=='string'||hash(s.payload)!==EPA_PIN)throw new Error('Red zone EPA pin mismatch');validateEpaData(JSON.parse(s.payload));return s.payload;}
export function redzoneEpaBoundary(port:number):Plugin{return {name:'private-redzone-epa',async configureServer(server){let frozen:string|null=null;try{frozen=freezeRedzoneEpa(await prepareRedzoneEpa());console.info('EPA red zone: 64 ataques e 64 agregados validados.');}catch{console.error('EPA red zone: fonte indisponível; sem fallback.');}
 server.middlewares.use((req,res,next)=>{const r=req as unknown as {url?:string;method?:string;headers:Record<string,string|string[]|undefined>;rawHeaders:string[]};if(!r.url?.startsWith('/__redzone-epa')){next();return;}res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');const fail=(status:number,error:string)=>{res.statusCode=status;res.end(JSON.stringify({error}));};if(!allowedRedzoneRequest(r.method??'',r.url,r.headers,port,r.rawHeaders)){fail(403,'REDZONE_EPA_REQUEST_REFUSED');return;}if(!frozen){fail(503,'REDZONE_EPA_SOURCE_UNAVAILABLE');return;}if(r.headers['x-redzone-epa-collection']!==EPA_PIN){fail(409,'REDZONE_EPA_COLLECTION_CHANGED');return;}res.setHeader('X-Redzone-Epa-Collection',EPA_PIN);res.end(frozen);});
 }};}
