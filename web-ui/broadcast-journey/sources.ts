import { order } from '../local-editorial/observations/selection';
import { errorText, observationCatalog, observationDocument } from '../local-editorial/observations/client';
import type { Catalog, DTO, Entry } from '../local-editorial/observations/model';
export type Archive = { catalog: Catalog; documents: { d: DTO; entry: Entry }[] };
// One frozen session, separate from the calendar publication/cache. No partial
// session is advertised as a completed availability check.
export async function loadArchive(signal: AbortSignal): Promise<Archive> {
  const catalog = await observationCatalog(signal);
  if (catalog.errorCode) throw new Error(errorText[catalog.errorCode] ?? 'Arquivo indisponível.');
  const entries = catalog.bundles.filter(e => e.dataKind === 'REAL_ARCHIVE');
  if (entries.some(e => e.status !== 'READY')) throw new Error(errorText[entries.find(e => e.status !== 'READY')!.errorCode ?? ''] ?? 'Arquivo indisponível.');
  const documents = await Promise.all(entries.flatMap(entry => entry.observations.map(async s => ({ entry, d: await observationDocument(catalog, entry, s, signal) }))));
  documents.sort((a, b) => a.entry.entryId.localeCompare(b.entry.entryId) || order(a.d, b.d));
  return { catalog, documents };
}
