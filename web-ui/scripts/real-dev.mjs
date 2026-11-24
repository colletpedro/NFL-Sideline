import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
const server = await createServer({
  configFile: fileURLToPath(new URL('../vite.real.config.ts', import.meta.url)), envFile: false,
});
await server.listen();
console.info(`Leitura local de arquivo real · PID ${process.pid}`);
server.printUrls();
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, async () => {
  await server.close(); process.exit(0);
});
