import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import snapshot from '../public/data/seasons/2026.json';
import type { Game } from '../src/services/types';
import type { Archive } from './sources';
import type { DTO } from '../local-editorial/observations/model';
import { availabilityDescription, availabilityLabel, gameAvailability, normalizeSearch, searchGames, selectGames } from './discoveryModel';
import { teamIdentities, teamIdentity } from '../broadcast-real/identity';
import { Logo } from '../broadcast-experience/TeamLogo';
import { Discovery } from './Discovery';
import { calendarChange, gameChange, journeyHref } from './state';
const games = snapshot.games.map(g => ({ ...g, homeTeam: snapshot.teams.find(t => t.teamAbbr === g.homeTeamAbbr)!, awayTeam: snapshot.teams.find(t => t.teamAbbr === g.awayTeamAbbr)! })) as Game[];
const bal = games.find(g => g.gameId === '2026_01_BAL_IND')!;
const doc = (g: Game, kind = 'individual') => ({ subject: { team: g.awayTeam.teamAbbr }, request: { season: g.season, phase: g.gameType, period: { weeks: [g.week] } }, members: [{ gameId: g.gameId, week: g.week, round: 'REG', sourceState: kind === 'gap' ? 'ABSENT' : 'PRESENT' }], observed: { includedGameIds: kind === 'gap' ? [] : [g.gameId] }, scope: { aggregation: kind === 'gap' ? 'NO_OBSERVATION' : 'SINGLE_GAME' } } as DTO);
const archive = (...docs: DTO[]) => ({ documents: docs.map(d => ({ d })) } as Archive);
describe('discovery of existing calendar games', () => {
  it('matches abbreviation, nickname, city, case, accents and whitespace consistently', () => {
    const expected = searchGames(games, 'DAL').map(g => g.gameId);
    for (const q of ['Cowboys', 'Dallas', '  DÁLLÁS   ', 'cowBOYS']) expect(searchGames(games, q).map(g => g.gameId)).toEqual(expected);
    expect(normalizeSearch('  São   Francisco ')).toBe('sao francisco');
    expect(searchGames(games, 'Báltimore')).toEqual(searchGames(games, 'BAL'));
  });
  it('intersects both participants without inventing pairings or treating short codes as substrings', () => {
    expect(searchGames(games, 'BAL × IND').map(g => g.gameId)).toEqual([bal.gameId]);
    expect(searchGames(games, 'Cowboys vs Giants').every(g => [g.homeTeam.teamAbbr, g.awayTeam.teamAbbr].includes('DAL') && [g.homeTeam.teamAbbr, g.awayTeam.teamAbbr].includes('NYG'))).toBe(true);
    expect(searchGames(games, 'DAL LAC')).toEqual([]);
    expect(searchGames(games, 'NE').every(g => [g.homeTeam.teamAbbr, g.awayTeam.teamAbbr].includes('NE'))).toBe(true);
    for (const q of ['', 'vs', '!!!', 'inexistente']) expect(searchGames(games, q)).toEqual([]);
  });
  it('limits aliases to presentation and still covers the literal 32 calendar identities', () => {
    const ids = [...new Set(games.flatMap(g => [g.homeTeam.teamAbbr, g.awayTeam.teamAbbr]))].sort();
    expect(Object.keys(teamIdentities).sort()).toEqual(ids); expect(ids).toHaveLength(32);
    expect(searchGames(games, 'LAR')).toEqual(searchGames(games, 'Rams'));
    expect(searchGames(games, 'WSH')).toEqual(searchGames(games, 'Commanders'));
    expect(teamIdentity('LAR').id).toBe('LAR'); expect(teamIdentity('LAR').logo).toBe('');
    for (const t of Object.values(teamIdentities)) { expect(t.logo).not.toMatch(/^https?:/); expect(t.logo).not.toBe(''); }
  });
  it('selects at most three available destinations and never repeats them in the archive', () => {
    const week = games.filter(g => g.week === 1), a = archive(doc(bal));
    const result = selectGames(week, a);
    expect(result.selected[0]).toBe(bal); expect(result.selected.length).toBeLessThanOrEqual(3);
    expect(new Set([...result.selected, ...result.remaining].map(g => g.gameId)).size).toBe(week.length);
    expect(result.selected.length + result.remaining.length).toBe(week.length);
    expect(selectGames([bal], a).selected).toEqual([bal]);
    expect(selectGames(week, null).selected).toEqual([week[0]]);
    expect(selectGames([], a).selected).toEqual([]);
  });
  it('prioritizes individual, inclusive and gap relationships without changing the DTO', () => {
    const gapGame = games.find(g => g.gameId === '2026_03_BAL_DAL')!;
    const includes = doc(bal); includes.members.push({ ...includes.members[0], gameId: '2026_02_NO_BAL', week: 2 }); includes.request.period.weeks = [1, 2]; includes.observed.includedGameIds.push('2026_02_NO_BAL'); includes.scope.aggregation = 'MULTI_GAME';
    const a = archive(includes, doc(gapGame, 'gap')); const before = structuredClone(a);
    expect(gameAvailability(bal, a)).toBe('includes'); expect(gameAvailability(gapGame, a)).toBe('gap');
    expect(availabilityLabel(gameAvailability(gapGame, a))).toBe('Lacuna deste jogo');
    expect(selectGames([gapGame, bal], a).selected[0]).toBe(bal); expect(a).toEqual(before);
  });
  it('preserves query, scope, origin week, filter and expansion through reading and return', () => {
    const q = new URLSearchParams('season=2026&week=3&filter=participants&q=BAL&scope=season&page=2&explore=open');
    const opened = new URLSearchParams(journeyHref(q, { game: bal.gameId, entry: 'real', observation: 'nominal' }).slice(2));
    for (const change of [gameChange, calendarChange]) {
      const returned = new URLSearchParams(journeyHref(opened, change).slice(2));
      for (const [key, value] of q) expect(returned.get(key)).toBe(value);
    }
  });
  it('shows the entire selected week and all weeks without a collapsed archive, and paginates searches', () => {
    const html = renderToStaticMarkup(<MemoryRouter><Discovery games={games} archive={archive(doc(bal))} archiveError="" q={new URLSearchParams()} season="2026" week={1} onChange={() => {}}/></MemoryRouter>);
    expect(html).not.toContain('discovery-archive'); expect(html).toContain('role="search"'); expect(html).toContain('Leitura deste jogo'); expect(html.match(/data-game=/g)).toHaveLength(16); expect(html.match(/aria-label="Semana [0-9]+"/g)).toHaveLength(18);
    const search = renderToStaticMarkup(<MemoryRouter><Discovery games={games} archive={null} archiveError="" q={new URLSearchParams('q=New&scope=season')} season="2026" week={1} onChange={() => {}}/></MemoryRouter>);
    expect(search.match(/data-game=/g)).toHaveLength(12); expect(search).toContain('Próxima página'); expect(search).not.toContain('discovery-stage');
  });
  it('does not label an unscored past game as scheduled', () => {
    const game = { ...bal, gameday: '2026-09-13', homeScore: null, awayScore: null, result: null };
    const html = renderToStaticMarkup(<MemoryRouter><Discovery games={[game]} archive={null} archiveError="" q={new URLSearchParams()} season="2026" week={1} onChange={() => {}}/></MemoryRouter>);
    expect(html).toContain('BAL IND'); expect(html).toContain('Resultado não disponível neste arquivo'); expect(html).not.toContain('Confronto agendado');
  });
  it('uses a reserved fallback without an img request for an empty source', () => {
    const html = renderToStaticMarkup(<Logo team={{ id: 'UNKNOWN', logo: '' }}/>);
    expect(html).not.toContain('<img'); expect(html).toContain('logo-fallback'); expect(html).toContain('UNKNOWN');
  });
});

it('names BAL by the search action for NO × BAL and makes no confirmed claim with an unavailable archive',()=>{
  const g=games.find(g=>g.gameId==='2026_02_NO_BAL')!;const d=doc(g);d.subject.team='BAL';
  expect(availabilityDescription(g,archive(d))).toBe('Leitura deste jogo · BAL');
  const props={games:[g],archive:archive(d),archiveError:'',q:new URLSearchParams('q=BAL&scope=season&week=3'),season:'2026',week:3,onChange:()=>{}};
  const html=renderToStaticMarkup(<MemoryRouter><Discovery {...props}/></MemoryRouter>);
  expect(html).toContain('Leitura deste jogo · BAL');expect(html).toContain('game=2026_02_NO_BAL');
  const unavailable=renderToStaticMarkup(<MemoryRouter><Discovery {...props} archive={null} archiveError="Falha"/></MemoryRouter>);
  expect(unavailable).toContain('Arquivo de leituras indisponível');expect(unavailable).not.toContain('Leitura deste jogo');
});
