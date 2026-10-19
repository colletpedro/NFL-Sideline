import { prepareSnapshot } from './observations-process.mjs';
import type { Plugin } from 'vite';
import { UI_PORT } from './local-editorial';
import { check, HASH, validateCatalog, validateDTO } from '../local-editorial/observations/model';
import type { Catalog, DTO, Entry } from '../local-editorial/observations/model';

export const PREFIX = '/__observations/';
const origin = `http://127.0.0.1:${UI_PORT}`;
const EMPTY_ID = `sha256:${'0'.repeat(64)}`;
export function allowedObservationRequest(method: string, url: string, headers: Record<string, string | string[] | undefined>) {
  return method === 'GET' && headers.host === `127.0.0.1:${UI_PORT}` &&
    (headers.origin === undefined || headers.origin === origin) && headers['x-local-observations'] === '1' &&
    headers['transfer-encoding'] === undefined && (headers['content-length'] === undefined || headers['content-length'] === '0') &&
    (url === PREFIX || /^\/__observations\/[a-z0-9_-]{1,48}\/[0-9a-f]{64}$/.test(url));
}
export type Frozen = { catalog: string; documents: ReadonlyMap<string, string>; sessionId: string };
export function freezeSnapshot(value: unknown): Frozen {
  const s = value as { snapshotVersion: string; sessionId: string; entries: (Omit<Entry, 'observations'> & { documents: DTO[] })[] };
  check(s && s.snapshotVersion === 'metrics-lab-snapshot-v1' && HASH.test(s.sessionId) && Array.isArray(s.entries));
  const documents = new Map<string, string>();
  const bundles = s.entries.map(e => {
    check(Array.isArray(e.documents));
    const summaries = e.documents.map(value => {
      const d = validateDTO(value); check(d.entryId === e.entryId && d.bundleId === e.bundleId);
      const key = `${e.entryId}/${d.observationId.slice(7)}`;
      check(!documents.has(key));
      documents.set(key, JSON.stringify({ transportVersion: 'metrics-lab-response-v1', sessionId: s.sessionId, document: d }));
      return { observationId: d.observationId, dtoId: d.dtoId, subject: d.subject, request: d.request };
    });
    return { entryId: e.entryId, label: e.label, dataKind: e.dataKind, status: e.status,
      bundleId: e.bundleId, errorCode: e.errorCode, observations: summaries };
  });
  const catalog = validateCatalog({ transportVersion: 'metrics-lab-catalog-v1', sessionId: s.sessionId, errorCode: null, bundles });
  return { catalog: JSON.stringify(catalog), documents, sessionId: s.sessionId };
}
function unavailable(errorCode: string): Frozen {
  const catalog: Catalog = { transportVersion: 'metrics-lab-catalog-v1', sessionId: EMPTY_ID, errorCode, bundles: [] };
  return { catalog: JSON.stringify(catalog), documents: new Map(), sessionId: EMPTY_ID };
}
async function prepare(): Promise<Frozen> {
  try {
    const value = await prepareSnapshot();
    if (value && typeof value === 'object' && 'errorCode' in value) {
      const code = String(value.errorCode);
      return unavailable(['OBSERVATIONS_NOT_CONFIGURED', 'OBSERVATION_CONFIGURATION_INVALID'].includes(code) ? code : 'OBSERVATION_STARTUP_FAILED');
    }
    return freezeSnapshot(value);
  } catch { return unavailable('OBSERVATION_STARTUP_FAILED'); }
}
export function observationBoundary(): Plugin {
  return {
    name: 'local-validated-observations',
    async configureServer(server) {
      const frozen = await prepare();
      server.middlewares.use((req, res, next) => {
        const incoming = req as unknown as { headers: Record<string, string | string[] | undefined>; method?: string; url?: string };
        if (!incoming.url?.startsWith(PREFIX.slice(0, -1))) { next(); return; }
        res.setHeader('Content-Type', 'application/json'); res.setHeader('Cache-Control', 'no-store'); res.setHeader('X-Content-Type-Options', 'nosniff');
        const fail = (status: number, error: string) => { res.statusCode = status; res.end(JSON.stringify({ error })); };
        if (!allowedObservationRequest(incoming.method ?? '', incoming.url, incoming.headers)) { fail(403, 'OBSERVATION_REQUEST_REJECTED'); return; }
        if (incoming.url === PREFIX) { res.end(frozen.catalog); return; }
        if (incoming.headers['x-observation-session'] !== frozen.sessionId) { fail(409, 'OBSERVATION_SESSION_CHANGED'); return; }
        const key = incoming.url.slice(PREFIX.length);
        const bytes = frozen.documents.get(key);
        if (bytes === undefined) { fail(404, 'OBSERVATION_UNAVAILABLE'); return; }
        res.end(bytes);
      });
    },
  };
}
