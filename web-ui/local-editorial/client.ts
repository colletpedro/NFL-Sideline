export interface Context {
  gameId: string; homeTeam: string; awayTeam: string; season: number; week: number;
  phase: string; gameday: string; asOfDate: string; sourceSha256: string;
}
export interface Attempt { attemptId: string; startedAt: string; resultIdentity: string; sourceSha256: string }
export interface History { attempts: Attempt[]; unavailableInStore: number }
export const sections = [
  ['fator_chave', 'Fator-chave'], ['vantagem_tatica', 'Leitura tática'],
  ['alerta_vermelho', 'Limites e contrapontos'], ['veredito', 'Síntese'],
] as const;
export interface Result {
  mode: 'LOCAL_RULES_DEVELOPMENT'; publicationApproved: false; gameId: string;
  attemptId: string; resultIdentity: string; analysis: Record<typeof sections[number][0], string>;
}
const id = /^[A-Za-z0-9_-]{1,128}$/;
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const hash = /^[0-9a-f]{64}$/;
function gamePath(game: string) {
  if (!id.test(game)) throw new Error('Contexto inválido.');
  return game;
}
export function validateResult(value: unknown, game: string, attempt?: string): Result {
  const r = value as Result | null;
  if (!r || r.mode !== 'LOCAL_RULES_DEVELOPMENT' || r.publicationApproved !== false || r.gameId !== game
    || !uuid.test(r.attemptId) || (attempt && r.attemptId !== attempt) || !hash.test(r.resultIdentity)
    || !r.analysis || Object.keys(r.analysis).length !== 4
    || !sections.every(([key]) => typeof r.analysis[key] === 'string')) throw new Error('Resposta local incompatível.');
  return r;
}
async function request(path: string, method = 'GET'): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`/__editorial/${path}`, {
      method, headers: { 'X-Local-Editorial': '1' }, cache: 'no-store', signal: controller.signal,
    });
    if (!response.ok) {
      if (response.status === 404) throw new Error('Contexto ou tentativa não encontrado. Atualize a lista.');
      if (response.status === 409) throw new Error('Tentativa incompleta ou indisponível. Consulte o histórico.');
      throw new Error(method === 'POST'
        ? 'Não foi possível confirmar a geração. Confira a API e atualize o histórico antes de tentar novamente.'
        : 'API local indisponível. Confira o servidor na porta 18081.');
    }
    return await response.json();
  } catch (error) {
    if (error instanceof SyntaxError) throw new Error('Resposta local incompatível.');
    if (error instanceof Error && error.name !== 'AbortError' && !(error instanceof TypeError)) throw error;
    throw new Error(method === 'POST'
      ? 'Não foi possível confirmar a geração. Atualize o histórico antes de tentar novamente: ela pode ter sido salva.'
      : 'Sem resposta da API local. Confira o servidor na porta 18081 e tente novamente.');
  } finally { clearTimeout(timeout); }
}
export async function catalog(): Promise<Context[]> {
  const value = await request('') as Context[];
  if (!Array.isArray(value) || !value.every(c => c && id.test(c.gameId)
    && typeof c.homeTeam === 'string' && typeof c.awayTeam === 'string'
    && Number.isInteger(c.season) && Number.isInteger(c.week)
    && typeof c.asOfDate === 'string' && hash.test(c.sourceSha256))) throw new Error('Catálogo local incompatível.');
  return value;
}
export async function history(game: string): Promise<History> {
  const value = await request(`${gamePath(game)}/attempts`) as History;
  if (!value || !Array.isArray(value.attempts) || !Number.isInteger(value.unavailableInStore)
    || value.unavailableInStore < 0 || !value.attempts.every(a => a && uuid.test(a.attemptId) && hash.test(a.resultIdentity)
      && hash.test(a.sourceSha256) && Number.isFinite(Date.parse(a.startedAt)))) throw new Error('Histórico local incompatível.');
  return value;
}
export async function generate(game: string) { return validateResult(await request(gamePath(game), 'POST'), game); }
export async function retrieve(game: string, attempt: string) {
  if (!uuid.test(attempt)) throw new Error('ID de tentativa inválido.');
  return validateResult(await request(`${gamePath(game)}/${attempt}`), game, attempt);
}
