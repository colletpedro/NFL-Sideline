import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Independent entry. No public dir, API proxy, lab middleware or production alias.
export default defineConfig({
  root: decodeURIComponent(new URL('./broadcast-experience', import.meta.url).pathname),
  plugins: [react()],
  publicDir: false,
  server: {
    host: '127.0.0.1', port: 18086, strictPort: true,
    fs: { allow: [decodeURIComponent(new URL('.', import.meta.url).pathname)] },
  },
  build: { outDir: '../experience-dist', emptyOutDir: true },
});
