import type {Plugin} from 'vite';
import {prepareCurve} from './curve-process.mjs';
import {hash} from './w12-process.mjs';
import {CURVE_PIN,ENDPOINT,validateEvents} from '../broadcast-journey/score-curve/model';
export function allowedCurveRequest(method:string,url:string,headers:Record<string,string|string[]|undefined>,port:number,raw:string[]=[]){
 const unique=['host','origin','x-local-curve-events','x-curve-collection','content-length','expect','transfer-encoding'];
 return method==='GET'&&url===ENDPOINT&&unique.every(h=>raw.filter((v,i)=>i%2===0&&v.toLowerCase()===h).length<=1)&&headers.host===`127.0.0.1:${port}`&&headers['x-local-curve-events']==='1'&&(headers.origin===undefined||headers.origin===`http://127.0.0.1:${port}`)&&headers.expect===undefined&&headers['transfer-encoding']===undefined&&(headers['content-length']===undefined||headers['content-length']==='0');
}
export function freezeCurve(input:unknown){const s=input as {bundleId:string;payload:string};if(s.bundleId!==CURVE_PIN||typeof s.payload!=='string'||hash(s.payload)!==CURVE_PIN)throw new Error('Curve events pin mismatch');validateEvents(JSON.parse(s.payload));return s.payload;}
export function curveBoundary(port:number):Plugin{return {name:'private-curve-events',async configureServer(server){let frozen:string|null=null;try{frozen=freezeCurve(await prepareCurve());console.info('Curve events: 262 turnovers conferidos.');}catch{console.error('Curve events: fonte indisponível; sem fallback.');}
 server.middlewares.use((req,res,next)=>{const r=req as unknown as {url?:string;method?:string;headers:Record<string,string|string[]|undefined>;rawHeaders:string[]};if(!r.url?.startsWith('/__curve-events')){next();return;}res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');const fail=(status:number,error:string)=>{res.statusCode=status;res.end(JSON.stringify({error}));};if(!allowedCurveRequest(r.method??'',r.url,r.headers,port,r.rawHeaders)){fail(403,'CURVE_EVENTS_REQUEST_REFUSED');return;}if(!frozen){fail(503,'CURVE_EVENTS_SOURCE_UNAVAILABLE');return;}if(r.headers['x-curve-collection']!==CURVE_PIN){fail(409,'CURVE_EVENTS_COLLECTION_CHANGED');return;}res.setHeader('X-Curve-Collection',CURVE_PIN);res.end(frozen);});
 }};}
