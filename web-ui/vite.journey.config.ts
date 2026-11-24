import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { situationalBoundary } from './build/situational';
import { observationBoundary, observationPort } from './build/observations';

export default defineConfig(({ command }) => {
  const raw = process.env.NFL_LOCAL_JOURNEY_PORT ?? '18092';
  if (!/^[1-9][0-9]{3,4}$/.test(raw)) throw new Error('Invalid loopback observation port');
  const port = observationPort(Number(raw));
  return {
    root: decodeURIComponent(new URL('./broadcast-journey', import.meta.url).pathname),
    envFile: false, envPrefix: [], publicDir: decodeURIComponent(new URL('./public', import.meta.url).pathname),
    plugins: [...(command === 'serve' ? [observationBoundary(port), situationalBoundary(port)] : []), react()],
    server: { host: '127.0.0.1', port, strictPort: true, cors: false,
      fs: { allow: [decodeURIComponent(new URL('.', import.meta.url).pathname)] } },
    build: { outDir: '../journey-dist', emptyOutDir: true, copyPublicDir: false },
  };
});
