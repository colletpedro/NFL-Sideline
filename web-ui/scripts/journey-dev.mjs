import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
const server = await createServer({
  configFile: fileURLToPath(new URL('../vite.journey.config.ts', import.meta.url)), envFile: false,
});
await server.listen();
console.info(`Percurso local integrado · PID ${process.pid}`);
server.printUrls();
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, async () => {
  await server.close(); process.exit(0);
});
