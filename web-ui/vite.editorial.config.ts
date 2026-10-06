import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { API_PORT, LOCAL_PREFIX, UI_PORT, localBoundary } from './build/local-editorial';

export default defineConfig(({ command, mode }) => {
  if (command !== 'serve' || mode === 'production') throw new Error('Editorial UI is development-only');
  return {
    root: decodeURIComponent(new URL('./local-editorial', import.meta.url).pathname),
    publicDir: false,
    envPrefix: [],
    plugins: [localBoundary(), react()],
    server: {
      host: '127.0.0.1', port: UI_PORT, strictPort: true, cors: false,
      fs: { allow: [decodeURIComponent(new URL('.', import.meta.url).pathname)] },
      proxy: {
        [LOCAL_PREFIX]: {
          target: `http://127.0.0.1:${API_PORT}`, changeOrigin: true,
          rewrite: path => path.replace(LOCAL_PREFIX, '/api/v1/local-analysis/'),
          configure(proxy) {
            // Only reached after the same-origin/Host/body/route checks above.
            proxy.on('proxyReq', request => {
              request.removeHeader('origin');
              request.removeHeader('x-local-editorial');
              request.removeHeader('cookie');
              request.removeHeader('authorization');
            });
            proxy.on('error', (_error, _request, response) => {
              if ('writeHead' in response && !response.headersSent) {
                response.writeHead(503, { 'Content-Type': 'application/json' });
                response.end(JSON.stringify({ error: 'LOCAL_API_UNAVAILABLE' }));
              }
            });
          },
        },
      },
    },
  };
});
