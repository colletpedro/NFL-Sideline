import { check, HASH, SLUG, validateCatalog, validateDTO } from './model';
import type { Catalog, DTO, Entry, Summary } from './model';
export const metaKey = (s: Summary) => [s.subject.team, s.subject.role, s.subject.foundation, s.request.season, s.request.phase, s.request.origin, ...s.request.period.weeks].join('|');
async function get(path: string, signal: AbortSignal | undefined, session?: string) {
  let response: Response;
  try { response = await fetch(`/__observations/${path}`, { method: 'GET', cache: 'no-store', signal,
    headers: { 'X-Local-Observations': '1', ...(session ? { 'X-Observation-Session': session } : {}) } }); }
  catch { throw new Error('Sem resposta do laboratório. Verifique a sessão local e tente novamente.'); }
  if (response.status === 409) throw new Error('A sessão mudou. Recarregue o catálogo antes de abrir o recorte.');
  if (!response.ok) throw new Error('Observação indisponível nesta sessão. Recarregue o catálogo.');
  try { return await response.json() as unknown; } catch { throw new Error('Transporte de observações incompatível.'); }
}
export async function observationCatalog(signal?: AbortSignal) { return validateCatalog(await get('', signal)); }
export async function observationDocument(catalog: Catalog, entry: Entry, selected: Summary, signal?: AbortSignal): Promise<DTO> {
  check(SLUG.test(entry.entryId) && HASH.test(selected.observationId));
  const value = await get(`${entry.entryId}/${selected.observationId.slice(7)}`, signal, catalog.sessionId) as { transportVersion: string; sessionId: string; document: unknown };
  check(value && Object.keys(value).sort().join('|') === 'document|sessionId|transportVersion' && value.transportVersion === 'metrics-lab-response-v1' && value.sessionId === catalog.sessionId);
  const d = validateDTO(value.document);
  check(d.entryId === entry.entryId && d.bundleId === entry.bundleId && d.observationId === selected.observationId && d.dtoId === selected.dtoId && metaKey(d) === metaKey(selected));
  return d;
}
export const errorText: Record<string, string> = {
  OBSERVATIONS_NOT_CONFIGURED: 'Catálogo não configurado. O operador precisa configurar os bundles e reiniciar o laboratório.',
  OBSERVATION_CONFIGURATION_INVALID: 'Configuração local inválida. O operador precisa corrigi-la e reiniciar o laboratório.',
  OBSERVATION_STARTUP_FAILED: 'Não foi possível preparar o catálogo. Verifique a configuração do operador e reinicie o laboratório.',
  BUNDLE_VALIDATION_FAILED: 'Bundle indisponível ou inválido. Corrija a entrada e reinicie para revalidar. Nenhum outro bundle foi usado.',
  BUNDLE_ID_MISMATCH: 'A identidade do bundle diverge da entrada configurada. Nenhum dado desta entrada foi carregado.',
  SYNTHETIC_KIND_MISMATCH: 'Uma fixture sintética foi declarada como arquivo real. Corrija a classificação e reinicie.',
};
