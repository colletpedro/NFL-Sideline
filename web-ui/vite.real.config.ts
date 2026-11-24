import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { observationBoundary, observationPort } from './build/observations';

export default defineConfig(({ command }) => {
  const raw = process.env.NFL_REAL_OBSERVATION_PORT ?? '18090';
  if (!/^[1-9][0-9]{3,4}$/.test(raw)) throw new Error('Invalid loopback observation port');
  const port = observationPort(Number(raw));
  return {
    root: decodeURIComponent(new URL('./broadcast-real', import.meta.url).pathname),
    envFile: false, envPrefix: [], publicDir: false,
    plugins: [...(command === 'serve' ? [observationBoundary(port)] : []), react()],
    server: { host: '127.0.0.1', port, strictPort: true, cors: false,
      fs: { allow: [decodeURIComponent(new URL('.', import.meta.url).pathname)] } },
    build: { outDir: '../real-dist', emptyOutDir: true },
  };
});
