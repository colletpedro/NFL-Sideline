import type {Plugin} from 'vite';
import {prepareTeam} from './team-process.mjs';
import {hash} from './w12-process.mjs';
import {TEAM_PIN,TEAM_ENDPOINT,validateTeamDocument,validateTeamIndex} from '../broadcast-journey/hub-team/model';
export function allowedTeamRequest(method:string,url:string,headers:Record<string,string|string[]|undefined>,port:number,raw:string[]=[]){
 const single=['host','origin','x-local-team-w12','x-team-collection','content-length','expect','transfer-encoding'];
 return single.every(h=>raw.filter((v,i)=>i%2===0&&v.toLowerCase()===h).length<=1)&&method==='GET'&&(url===TEAM_ENDPOINT||/^\/__team-w12\/[A-Z]{2,3}$/.test(url))&&headers.host===`127.0.0.1:${port}`&&headers['x-local-team-w12']==='1'&&(headers.origin===undefined||headers.origin===`http://127.0.0.1:${port}`)&&headers.expect===undefined&&headers['transfer-encoding']===undefined&&(headers['content-length']===undefined||headers['content-length']==='0');
}
export function freezeTeam(value:unknown){
 const s=value as {bundleId:string;index:string;documents:Record<string,string>};if(s.bundleId!==TEAM_PIN||hash(s.index)!==TEAM_PIN)throw new Error('Team pin mismatch');const i=validateTeamIndex(JSON.parse(s.index));if(Object.keys(s.documents).length!==32)throw new Error('Team inventory mismatch');
 const docs=new Map<string,{bytes:string;hash:string}>();for(const e of i.teams){const b=s.documents[e.team];if(typeof b!=='string'||hash(b)!==e.documentHash)throw new Error('Team document mismatch');validateTeamDocument(JSON.parse(b),e);docs.set(e.team,{bytes:b,hash:e.documentHash});}return {index:s.index,documents:docs};
}
export function teamBoundary(port:number):Plugin{return {name:'private-team-w12',async configureServer(server){let frozen:ReturnType<typeof freezeTeam>|null=null;try{frozen=freezeTeam(await prepareTeam());console.info('Times: 32 documentos W1–2 validados e congelados.');}catch{console.error('Times: fonte indisponível; sem fallback.');}
 server.middlewares.use((req,res,next)=>{const r=req as unknown as {url?:string;method?:string;headers:Record<string,string|string[]|undefined>;rawHeaders:string[]};if(!r.url?.startsWith('/__team-w12')){next();return;}res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');const fail=(status:number,error:string)=>{res.statusCode=status;res.end(JSON.stringify({error}));};if(!allowedTeamRequest(r.method??'',r.url,r.headers,port,r.rawHeaders)){fail(403,'TEAM_REQUEST_REFUSED');return;}if(!frozen){fail(503,'TEAM_SOURCE_UNAVAILABLE');return;}if(r.headers['x-team-collection']!==TEAM_PIN){fail(409,'TEAM_COLLECTION_CHANGED');return;}const item=r.url===TEAM_ENDPOINT?{bytes:frozen.index,hash:TEAM_PIN}:frozen.documents.get(r.url.slice(TEAM_ENDPOINT.length));if(!item){fail(404,'TEAM_UNKNOWN');return;}res.setHeader('X-Team-Collection',TEAM_PIN);res.setHeader('X-Team-Document',item.hash);res.end(item.bytes);});
 }};}
