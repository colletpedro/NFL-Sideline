import type {Plugin} from 'vite';
import {prepareStory} from './story-process.mjs';
import {hash} from './w12-process.mjs';
import {STORY_PIN,STORY_ENDPOINT,validateStory} from '../broadcast-journey/game-story/model';
export function allowedStoryRequest(method:string,url:string,headers:Record<string,string|string[]|undefined>,port:number,raw:string[]=[]){
 const unique=['host','origin','x-local-game-story','x-game-story-collection','content-length','expect','transfer-encoding'];
 return method==='GET'&&url===STORY_ENDPOINT&&unique.every(h=>raw.filter((v,i)=>i%2===0&&v.toLowerCase()===h).length<=1)&&headers.host===`127.0.0.1:${port}`&&headers['x-local-game-story']==='1'&&(headers.origin===undefined||headers.origin===`http://127.0.0.1:${port}`)&&headers.expect===undefined&&headers['transfer-encoding']===undefined&&(headers['content-length']===undefined||headers['content-length']==='0');
}
export function freezeStory(input:unknown){const s=input as {bundleId:string;payload:string};if(s.bundleId!==STORY_PIN||typeof s.payload!=='string'||hash(s.payload)!==STORY_PIN)throw new Error('Game story pin mismatch');validateStory(JSON.parse(s.payload));return s.payload;}
export function storyBoundary(port:number):Plugin{return {name:'private-game-story',async configureServer(server){let frozen:string|null=null;try{frozen=freezeStory(await prepareStory());console.info('Game story: 107 placares e referências W1–7 validados.');}catch{console.error('Game story: fonte indisponível; sem fallback.');}
 server.middlewares.use((req,res,next)=>{const r=req as unknown as {url?:string;method?:string;headers:Record<string,string|string[]|undefined>;rawHeaders:string[]};if(!r.url?.startsWith('/__game-story')){next();return;}res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');const fail=(status:number,error:string)=>{res.statusCode=status;res.end(JSON.stringify({error}));};if(!allowedStoryRequest(r.method??'',r.url,r.headers,port,r.rawHeaders)){fail(403,'GAME_STORY_REQUEST_REFUSED');return;}if(!frozen){fail(503,'GAME_STORY_SOURCE_UNAVAILABLE');return;}if(r.headers['x-game-story-collection']!==STORY_PIN){fail(409,'GAME_STORY_COLLECTION_CHANGED');return;}res.setHeader('X-Game-Story-Collection',STORY_PIN);res.end(frozen);});
 }};}
