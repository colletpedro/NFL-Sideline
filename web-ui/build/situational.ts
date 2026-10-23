import { prepareSituational } from './situational-process.mjs';
import type { Plugin } from 'vite';
import { validateSnapshot } from '../broadcast-journey/situational/model';
export function allowedSituationalRequest(method:string,url:string,headers:Record<string,string|string[]|undefined>,port:number) {
  return method==='GET' && url==='/__situational/' && headers.host===`127.0.0.1:${port}` &&
    (headers.origin===undefined || headers.origin===`http://127.0.0.1:${port}`) && headers['x-local-situational']==='1' &&
    headers['transfer-encoding']===undefined && (headers['content-length']===undefined || headers['content-length']==='0');
}
export function situationalBoundary(port:number):Plugin {
  return {name:'local-situational-v1',async configureServer(server) {
    let frozen:string|null=null;
    try { const value=await prepareSituational(); if(value!==null) frozen=JSON.stringify(validateSnapshot(value)); }
    catch { console.error('Situacional: validação local recusada; nenhum dado alternativo.'); }
    server.middlewares.use((req,res,next)=>{
      const incoming=req as unknown as {url?:string;method?:string;headers:Record<string,string|string[]|undefined>};
      if (!incoming.url?.startsWith('/__situational')) {next();return;}
      res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
      if (!allowedSituationalRequest(incoming.method??'',incoming.url,incoming.headers,port)) {res.statusCode=403;res.end(JSON.stringify({error:'SITUATIONAL_REQUEST_REJECTED'}));return;}
      if (!frozen) {res.statusCode=503;res.end(JSON.stringify({error:'SITUATIONAL_UNAVAILABLE'}));return;}
      res.end(frozen);
    });
  }};
}
