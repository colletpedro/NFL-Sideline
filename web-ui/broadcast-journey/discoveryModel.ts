import type { Game, Team } from '../src/services/types';
import { teamIdentity } from '../broadcast-real/identity';
import { relation, type Relation } from './relations';
import type { Archive } from './sources';
export const normalizeSearch = (text: string) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
function words(team: Team) {
  const visual = teamIdentity(team.teamAbbr);
  return normalizeSearch([team.teamAbbr, team.teamName, visual.city, visual.name, ...(visual.aliases ?? [])].join(' ')).split(' ');
}
export function searchGames(games: Game[], query: string) {
  const raw = normalizeSearch(query).split(' ').filter(Boolean);
  const tokens = raw.length > 1 ? raw.filter(t => !['x', 'vs', 'v', 'versus', 'contra', 'at'].includes(t)) : raw.filter(t => !['x', 'vs', 'versus', 'contra', 'at'].includes(t));
  if (!tokens.length) return [];
  const codes = new Set(games.flatMap(g => [g.awayTeam.teamAbbr.toLowerCase(),g.homeTeam.teamAbbr.toLowerCase()]));
  return games.filter(game => {
    const terms = [...words(game.awayTeam), ...words(game.homeTeam)];
    return tokens.every(token => terms.some(term => codes.has(token) ? term === token : term.startsWith(token)));
  });
}
export function suggestGames(games: Game[], query: string, week: number | null, limit = 4) {
  if (!normalizeSearch(query)) return [];
  return searchGames(games, query).map((game,index) => ({game,index}))
    .sort((a,b) => Number(b.game.week === week) - Number(a.game.week === week) || a.index-b.index)
    .slice(0,limit).map(({game}) => {
      const matched = [game.awayTeam,game.homeTeam].filter(team => searchGames([{...game,awayTeam:team,homeTeam:team}],query).length > 0);
      return {game,team:matched.length === 1 ? matched[0].teamAbbr : null};
    });
}
const priority: Relation[] = ['individual', 'includes', 'gap', 'other', 'archive'];
export function gameAvailability(game: Game, archive: Archive | null): Relation | null {
  const relations = archive?.documents.map(({ d }) => relation(game, d)) ?? [];
  return priority.find(kind => relations.includes(kind)) ?? null;
}
// Literal abbreviation order is stable and carries no sporting meaning.
export function availabilityTeams(game: Game, archive: Archive | null): string[] {
  const kind = gameAvailability(game, archive);
  return kind ? [...new Set(archive?.documents.filter(({ d }) => relation(game, d) === kind).map(({ d }) => d.subject.team))].sort() : [];
}
export function availabilityDescription(game: Game, archive: Archive | null) {
  const label = availabilityLabel(gameAvailability(game, archive));
  const teams = availabilityTeams(game, archive);
  return teams.length === 1 ? `${label} · ${teams[0]}` : label;
}
export function selectGames(games: Game[], archive: Archive | null) {
  // Calendar order breaks ties. Availability is not sporting merit.
  const ranked = games.map((game, index) => ({ game, index, kind: gameAvailability(game, archive) }))
    .sort((a, b) => (a.kind ? priority.indexOf(a.kind) : 99) - (b.kind ? priority.indexOf(b.kind) : 99) || a.index - b.index);
  const useful = ranked.filter(x => x.kind);
  const selected = (useful.length ? useful.slice(0, 3) : ranked.slice(0, 1)).map(x => x.game);
  const ids = new Set(selected.map(x => x.gameId));
  return { selected, remaining: games.filter(x => !ids.has(x.gameId)) };
}
export const availabilityLabel = (kind: Relation | null) => kind === 'individual' ? 'Leitura deste jogo' : kind === 'includes' ? 'Período que inclui o jogo' : kind === 'gap' ? 'Lacuna deste jogo' : kind === 'other' || kind === 'archive' ? 'Outros recortes do participante' : 'Sem leitura dos participantes';
export const availabilityAction = (kind: Relation | null) => kind === 'individual' ? 'Escolher leitura' : kind === 'includes' ? 'Explorar período' : kind === 'gap' ? 'Ver lacuna' : kind === 'other' || kind === 'archive' ? 'Explorar outros recortes' : 'Abrir confronto';
