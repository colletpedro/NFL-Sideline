import { games, type Game, type Period, type PlayType } from './fixtures';
export function readState(search: string) {
  const params = new URLSearchParams(search);
  const round = [6, 7, 8].includes(Number(params.get('round'))) ? Number(params.get('round')) : 7;
  const period: Period = params.get('period') === 'first' || params.get('period') === 'second' ? params.get('period') as Period : 'game';
  const play: PlayType = params.get('play') === 'pass' || params.get('play') === 'rush' ? params.get('play') as PlayType : 'all';
  return { round, period, play, details: params.get('details') === 'open' };
}
export function gameForId(id: string | undefined) { return games.find(g => g.id === id); }

export function matchupHref(game: Game, originRound: number, selection?: ReturnType<typeof readState>) {
  const query = new URLSearchParams({ round: String(originRound) });
  if (selection && game.status === 'final') {
    if (selection.period !== 'game') query.set('period', selection.period);
    if (selection.play !== 'all') query.set('play', selection.play);
    if (selection.details) query.set('details', 'open');
  }
  return `/confronto/${game.id}?${query}`;
}
export function navigationContext(pathname: string, search: string) {
  const state = readState(search), current = gameForId(pathname.match(/^\/confronto\/([^/]+)\/?$/)?.[1]);
  const requested = Number(new URLSearchParams(search).get('round'));
  const originRound = [6, 7, 8].includes(requested) ? requested : current?.round ?? state.round;
  const featured = games.find(g => g.round === originRound) ?? games[0];
  return { current, gameRound: current?.round ?? null, originRound, centralHref: `/?round=${originRound}`, analysisHref: matchupHref(current ?? featured, originRound, current ? state : undefined) };
}
