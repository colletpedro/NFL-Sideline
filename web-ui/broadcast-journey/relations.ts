import type { Game } from '../src/services/types';
import type { DTO } from '../local-editorial/observations/model';
import { finalGameResult } from '../src/components/matchupResult';
export type Relation = 'individual' | 'includes' | 'gap' | 'other' | 'archive' | 'incompatible';
export const groups: Record<Exclude<Relation, 'incompatible'>, string> = {
  individual: 'Leituras do jogo', includes: 'Períodos que incluem o jogo', gap: 'Lacunas do jogo',
  other: 'Outros recortes arquivados', archive: 'Outra temporada ou fase',
};
export function relation(g: Game, d: DTO): Relation {
  if (![g.homeTeam.teamAbbr, g.awayTeam.teamAbbr].includes(d.subject.team)) return 'incompatible';
  const m = d.members.find(m => m.gameId === g.gameId);
  const samePeriod = d.request.season === g.season && d.request.phase === g.gameType;
  if (!samePeriod) return m ? 'incompatible' : 'archive';
  if (!m) return 'other';
  if (m.week !== g.week || !d.request.period.weeks.includes(g.week) ||
    (g.gameType === 'REG' ? m.round !== 'REG' : !['WC', 'DIV', 'CON', 'SB'].includes(m.round ?? ''))) return 'incompatible';
  const included = d.observed.includedGameIds.includes(g.gameId);
  if (m.sourceState === 'ABSENT') return !included && (d.scope.aggregation === 'NO_OBSERVATION' || d.members.length > 1 && d.scope.aggregation === 'MULTI_GAME') ? 'gap' : 'incompatible';
  if (!included) return 'incompatible';
  if (d.members.length === 1 && d.scope.aggregation === 'SINGLE_GAME') return 'individual';
  if (d.members.length > 1 && d.scope.aggregation === 'MULTI_GAME') return 'includes';
  return 'incompatible';
}
export function relationText(r: Relation, d: DTO) {
  const weeks = d.request.period.weeks.join('–');
  return {
    individual: 'Leitura arquivada deste jogo', includes: `Recorte de semanas ${weeks}, que inclui este jogo`,
    gap: d.members.length > 1 ? `Recorte de semanas ${weeks} com lacuna deste jogo; o agregado não oferece estatísticas desse jogo ausente` : 'Lacuna deste jogo · sem fonte para a amostra',
    other: `Outro recorte do time · semanas ${weeks}; não é uma leitura deste jogo`,
    archive: `Arquivo separado · ${d.request.season} ${d.request.phase} · semanas ${weeks}`,
    incompatible: 'Sem vínculo válido com este confronto',
  }[r];
}
export function gameState(g: Game, today = new Date()) {
  const result = finalGameResult(g);
  if (result) return { label: result.homeScore === result.awayScore ? 'Resultado disponível · empate' : 'Resultado disponível', score: `${g.awayTeam.teamAbbr} ${result.awayScore} × ${result.homeScore} ${g.homeTeam.teamAbbr}` };
  if ([g.homeScore, g.awayScore, g.result].some(v => v !== null)) return { label: 'Informação de resultado insuficiente · trio inválido', score: null };
  if (!g.gameday || !/^\d{4}-\d{2}-\d{2}$/.test(g.gameday) || !Number.isFinite(Date.parse(g.gameday)) || new Date(g.gameday).toISOString().slice(0,10) !== g.gameday) return { label: 'Informação de estado insuficiente', score: null };
  return { label: g.gameday > today.toISOString().slice(0,10) ? 'Jogo agendado conforme a data do arquivo' : 'Resultado não disponível neste arquivo', score: null };
}
export const title = (g: Game) => `${g.awayTeam.teamName} × ${g.homeTeam.teamName}`;
export const dateLabel = (day: string | null) => day && Number.isFinite(Date.parse(day)) ? new Date(day + 'T00:00:00Z').toLocaleDateString('pt-BR', { timeZone: 'UTC', day: 'numeric', month: 'long', year: 'numeric' }) : 'Data não disponível';
