import { games, type Period, type PlayType } from './fixtures';
export function readState(search: string) {
  const params = new URLSearchParams(search);
  const round = [6, 7, 8].includes(Number(params.get('round'))) ? Number(params.get('round')) : 7;
  const period: Period = params.get('period') === 'first' || params.get('period') === 'second' ? params.get('period') as Period : 'game';
  const play: PlayType = params.get('play') === 'pass' || params.get('play') === 'rush' ? params.get('play') as PlayType : 'all';
  return { round, period, play, details: params.get('details') === 'open' };
}
export function gameForId(id: string | undefined) { return games.find(g => g.id === id); }
