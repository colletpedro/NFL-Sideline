// Prepared artifact preview. No source processing, external calls or public-build access.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {join,extname} from 'node:path';
import {createHash} from 'node:crypto';
const base=fileURLToPath(new URL('../risk-outcomes-dist/',import.meta.url));
const map=JSON.parse(await readFile(join(base,'local-routes.json'),'utf8'));
const port=Number(process.env.NFL_RISK_OUTCOMES_PREVIEW_PORT??18126);
if(!Number.isInteger(port)||port<1024||port>65535)throw new Error('Invalid preview port');
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf','.json':'application/json'};
const server=createServer(async(req,res)=>{try{
 if(req.method!=='GET'||req.headers.host!==`127.0.0.1:${port}`||(req.headers.origin&&req.headers.origin!==`http://127.0.0.1:${port}`)){res.writeHead(403).end();return;}
 const url=new URL(req.url,`http://127.0.0.1:${port}`);const route=map.routes[url.pathname];
 if(route){const bytes=await readFile(join(base,route.file));if(createHash('sha256').update(bytes).digest('hex')!==route.sha256)throw new Error('Artifact hash mismatch');res.writeHead(200,{...route.headers,'X-Content-Type-Options':'nosniff'}).end(bytes);return;}
 const path=decodeURIComponent(url.pathname);if(path.includes('..')||path.startsWith('/__')||!/^\/(?:assets\/[a-zA-Z0-9_.-]+|index.html)?$/.test(path)){res.writeHead(404).end();return;}
 const file=path==='/'?'index.html':path.slice(1);res.writeHead(200,{'Content-Type':types[extname(file)]??'application/octet-stream','X-Content-Type-Options':'nosniff'}).end(await readFile(join(base,file)));
 }catch{res.writeHead(503,{'Content-Type':'application/json'}).end('{"error":"ARTIFACT_UNAVAILABLE"}');}});
server.on('error',e=>{console.error(e.message);process.exitCode=1;});server.listen(port,'127.0.0.1',()=>console.info(`Built outcomes lab · PID ${process.pid} · http://127.0.0.1:${port}/?view=risk-lab&season=2026`));
for(const signal of ['SIGTERM','SIGINT'])process.once(signal,()=>server.close(()=>process.exit(0)));
