import type { Plugin } from 'vite';
import { prepareComparison } from './matchup-process.mjs';
import { validateDocument, FOUNDATION_PIN, ENDPOINT } from '../broadcast-journey/matchup/model';
export function allowedMatchupRequest(method:string,url:string,headers:Record<string,string|string[]|undefined>,port:number,rawHeaders:string[] = []) {
  const single = ['host','origin','x-local-matchup','content-length'];
  return single.every(h => rawHeaders.filter((v,i) => i%2===0 && v.toLowerCase()===h).length <= 1) &&
    method==='GET' && url===ENDPOINT && headers.host===`127.0.0.1:${port}` && headers['x-local-matchup']==='1' &&
    (headers.origin===undefined || headers.origin===`http://127.0.0.1:${port}`) &&
    headers['transfer-encoding']===undefined && headers.expect===undefined && (headers['content-length']===undefined || headers['content-length']==='0');
}
export function matchupBoundary(port:number):Plugin {
  return {name:'private-matchup-reading-v1',async configureServer(server) {
    let frozen:string|null=null;
    try {const value=await prepareComparison();if(value.pin!==FOUNDATION_PIN)throw new Error('Pin mismatch');validateDocument(JSON.parse(value.bytes));frozen=value.bytes;}
    catch {console.error('Piloto: base comparável indisponível; sem substituição de fonte.');}
    server.middlewares.use((req,res,next) => {
      const incoming=req as unknown as {url?:string;method?:string;headers:Record<string,string|string[]|undefined>;rawHeaders:string[]};
      if (!incoming.url?.startsWith('/__matchup-reading')) {next();return;}
      res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
      if(!allowedMatchupRequest(incoming.method??'',incoming.url,incoming.headers,port,incoming.rawHeaders)) {res.statusCode=403;res.end('{"error":"MATCHUP_REQUEST_REFUSED"}');return;}
      if(frozen===null) {res.statusCode=503;res.end('{"error":"MATCHUP_SOURCE_UNAVAILABLE"}');return;}
      res.setHeader('X-Comparison-Bundle',FOUNDATION_PIN);res.end(frozen);
    });
  }};
}
