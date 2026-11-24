import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
const server=await createServer({configFile:fileURLToPath(new URL('../vite.risk-lab.config.ts',import.meta.url)),envFile:false});await server.listen();console.info(`NFL Sideline · laboratório de risco · PID ${process.pid}`);server.printUrls();for(const signal of ['SIGINT','SIGTERM'])process.once(signal,async()=>{await server.close();process.exit(0);});
