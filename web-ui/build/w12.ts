import type {Plugin} from 'vite';
import {prepareW12,hash} from './w12-process.mjs';
import {COLLECTION_PIN,ENDPOINT,validateDocument,validateIndex} from '../broadcast-journey/w12/model';
export function allowedW12Request(method:string,url:string,headers:Record<string,string|string[]|undefined>,port:number,raw:string[]=[]){
  const single=['host','origin','x-local-matchup-w12','x-matchup-collection','content-length','expect','transfer-encoding'];
  return single.every(h=>raw.filter((v,i)=>i%2===0&&v.toLowerCase()===h).length<=1)&&method==='GET'&&
    (url===ENDPOINT||/^\/__matchup-w12\/2026_0[12]_[A-Z]{2,3}_[A-Z]{2,3}$/.test(url))&&headers.host===`127.0.0.1:${port}`&&headers['x-local-matchup-w12']==='1'&&
    (headers.origin===undefined||headers.origin===`http://127.0.0.1:${port}`)&&headers.expect===undefined&&headers['transfer-encoding']===undefined&&(headers['content-length']===undefined||headers['content-length']==='0');
}
export function freezeW12(value:unknown){
  const s=value as {bundleId:string;index:string;documents:Record<string,string>};
  if(s.bundleId!==COLLECTION_PIN||hash(s.index)!==COLLECTION_PIN)throw new Error('Collection identity mismatch');
  const i=validateIndex(JSON.parse(s.index));
  if(Object.keys(s.documents).length!==i.games.length)throw new Error('Document inventory mismatch');
  const docs=new Map<string,{bytes:string;hash:string}>();
  for(const e of i.games){const b=s.documents[e.gameId];if(typeof b!=='string'||hash(b)!==e.documentHash)throw new Error('Document identity mismatch');validateDocument(JSON.parse(b),e);docs.set(e.gameId,{bytes:b,hash:e.documentHash});}
  return {index:s.index,documents:docs};
}
export function w12Boundary(port:number):Plugin{return {name:'private-matchup-w12',async configureServer(server){
  let frozen:ReturnType<typeof freezeW12>|null=null;
  try{frozen=freezeW12(await prepareW12());console.info('W1–2: 32 documentos integralmente validados e congelados.');}catch{console.error('W1–2: fonte indisponível; sem fallback.');}
  server.middlewares.use((req,res,next)=>{
    const incoming=req as unknown as {url?:string;method?:string;headers:Record<string,string|string[]|undefined>;rawHeaders:string[]};
    if(!incoming.url?.startsWith('/__matchup-w12')){next();return;}
    res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
    const fail=(status:number,error:string)=>{res.statusCode=status;res.end(JSON.stringify({error}));};
    if(!allowedW12Request(incoming.method??'',incoming.url,incoming.headers,port,incoming.rawHeaders)){fail(403,'MATCHUP_REQUEST_REFUSED');return;}
    if(!frozen){fail(503,'MATCHUP_SOURCE_UNAVAILABLE');return;}
    if(incoming.headers['x-matchup-collection']!==COLLECTION_PIN){fail(409,'MATCHUP_COLLECTION_CHANGED');return;}
    const item=incoming.url===ENDPOINT?{bytes:frozen.index,hash:COLLECTION_PIN}:frozen.documents.get(incoming.url.slice(ENDPOINT.length));
    if(!item){fail(404,'MATCHUP_UNKNOWN');return;}
    res.setHeader('X-Matchup-Collection',COLLECTION_PIN);res.setHeader('X-Matchup-Document',item.hash);res.end(item.bytes);
  });
}};}
