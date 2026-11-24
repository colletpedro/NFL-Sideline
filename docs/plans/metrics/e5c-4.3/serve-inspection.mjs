// Inspection-only port adapter: retain the accepted fixed-port boundaries unchanged.
// Use a new loopback port while the historical 18083 server remains running.
import { createServer } from '../../../../web-ui/node_modules/vite/dist/node/index.js';
import { fileURLToPath } from 'node:url';
const root = new URL('../../../../', import.meta.url);
const server = await createServer({
 configFile: fileURLToPath(new URL('web-ui/vite.editorial.config.ts', root)),
 envFile: false,
 plugins: [{ name: 'inspection-loopback-port', enforce: 'pre', configureServer(s) {
  s.middlewares.use((req,res,next) => {
   if(req.headers.host !== '127.0.0.1:18084' || (req.headers.origin && req.headers.origin !== 'http://127.0.0.1:18084')) { res.writeHead(403); res.end(); return; }
   req.headers.host='127.0.0.1:18083';
   if(req.headers.origin) req.headers.origin='http://127.0.0.1:18083';
   next();
  });
 }}],
 server: { host:'127.0.0.1',port:18084,strictPort:true },
});
await server.listen(); server.printUrls();
for(const signal of ['SIGINT','SIGTERM']) process.once(signal,async()=>{await server.close();process.exit(0)});
