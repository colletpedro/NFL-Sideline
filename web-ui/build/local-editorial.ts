import type { Plugin } from 'vite';

export const UI_PORT = 18083;
export const API_PORT = 18081;
export const LOCAL_PREFIX = '/__editorial/';
const origin = `http://127.0.0.1:${UI_PORT}`;

export function allowedLocalRequest(method: string, url: string, host: string | undefined,
  requestOrigin: string | undefined, marker: string | undefined, length: string | undefined,
  transfer: string | undefined): boolean {
  if (host !== `127.0.0.1:${UI_PORT}` || (requestOrigin !== undefined && requestOrigin !== origin)) return false;
  if (!url.startsWith(LOCAL_PREFIX)) return method === 'GET' || method === 'HEAD';
  if (marker !== '1' || transfer !== undefined || (length !== undefined && length !== '0')) return false;
  const suffix = url.slice(LOCAL_PREFIX.length);
  if (method === 'POST') return requestOrigin === origin && /^[A-Za-z0-9_-]{1,128}$/.test(suffix);
  return method === 'GET' && (suffix === '' || /^[A-Za-z0-9_-]{1,128}\/(attempts|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/.test(suffix));
}

export function localBoundary(): Plugin {
  return {
    name: 'local-editorial-boundary',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        // Structural adapter: the frontend does not depend on the Node type package.
        const incoming = req as unknown as { headers: Record<string, string | string[] | undefined>; method?: string; url?: string };
        const header = (name: string) => typeof incoming.headers[name] === 'string' ? incoming.headers[name] : undefined;
        if (!allowedLocalRequest(incoming.method ?? '', incoming.url ?? '', header('host'), header('origin'),
          header('x-local-editorial'), header('content-length'), header('transfer-encoding'))) {
          res.writeHead(403, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
          res.end(JSON.stringify({ error: 'LOCAL_UI_REQUEST_REJECTED' }));
          return;
        }
        res.setHeader('Cache-Control', 'no-store');
        next();
      });
    },
  };
}
