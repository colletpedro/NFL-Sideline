import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
const server=await createServer({configFile:fileURLToPath(new URL('../vite.hub-team.config.ts',import.meta.url)),envFile:false});await server.listen();console.info(`Hub e times W1–2 · PID ${process.pid}`);server.printUrls();for(const signal of ['SIGINT','SIGTERM'])process.once(signal,async()=>{await server.close();process.exit(0);});
