import { describe, expect, it } from 'vitest';
import type { DTO, Entry } from '../local-editorial/observations/model';
import type { Game } from '../src/services/types';
import type { Archive } from './sources';
import { choiceGroups, readChoice, type Choice } from './choice';
import { calendarChange, gameChange, journeyHref } from './state';

const game = { gameId: '2026_01_BAL_IND', season: 2026, week: 1, gameType: 'REG', awayTeam: { teamAbbr: 'BAL' }, homeTeam: { teamAbbr: 'IND' } } as Game;
// Small fixtures test selection only. DTO validation and arithmetic remain in the reader.
const sample = (): DTO => ({ subject: { team: 'BAL', role: 'off', foundation: 'general' }, request: { season: 2026, phase: 'REG', period: { weeks: [1] } }, members: [{ gameId: game.gameId, week: 1, round: 'REG', sourceState: 'PRESENT' }], observed: { includedGameIds: [game.gameId] }, scope: { aggregation: 'SINGLE_GAME' } } as DTO);
const archive = (...documents: DTO[]) => ({ documents: documents.map(d => ({ d, entry: { entryId: 'test' } as Entry })) } as Archive);
const defaultChoice: Choice = { team: 'BAL', side: 'off', play: 'general' };
describe('explicit choice without changing the nominal observation', () => {
  it('uses only participants and known dimensions from the URL', () => {
    expect(readChoice(game, new URLSearchParams('team=NE&side=invalid&play=invalid'))).toEqual(defaultChoice);
    expect(readChoice(game, new URLSearchParams('team=IND&side=def&play=classified_rush'))).toEqual({ team: 'IND', side: 'def', play: 'classified_rush' });
  });
  it('starts a direct reading chooser from the named document without mutating it', () => {
    const d = sample(); d.subject.role = 'def'; d.subject.foundation = 'classified_pass';
    const before = structuredClone(d);
    expect(readChoice(game, new URLSearchParams(), d)).toEqual({ team: 'BAL', side: 'def', play: 'classified_pass' });
    expect(readChoice(game, new URLSearchParams('team=IND&side=off'), d).team).toBe('IND');
    expect(d).toEqual(before);
  });
  it('offers only the selected dimensions, retaining original document references', () => {
    const documents: DTO[] = [];
    for (const role of ['off', 'def'] as const) for (const foundation of ['general', 'classified_pass', 'classified_rush'] as const) {
      const d = sample(); d.subject = { ...d.subject, role, foundation }; documents.push(d);
    }
    const a = archive(...documents);
    for (const d of documents) {
      const result = choiceGroups(game, a, { team: 'BAL', side: d.subject.role, play: d.subject.foundation });
      expect(result.primary).toHaveLength(1); expect(result.primary[0].d).toBe(d);
    }
    expect(choiceGroups(game, a, { ...defaultChoice, team: 'IND' }).primary).toEqual([]);
  });
  it('keeps an inclusive period secondary even with a single source', () => {
    const d = sample(); d.members.push({ ...d.members[0], gameId: '2026_02_NO_BAL', week: 2, sourceState: 'ABSENT' });
    d.request.period.weeks = [1, 2]; d.scope.aggregation = 'MULTI_GAME';
    const result = choiceGroups(game, archive(d), defaultChoice);
    expect(result.primary).toEqual([]); expect(result.includes[0].d).toBe(d);
  });
  it('shows a missing game as a gap without replacing it with another week', () => {
    const gap = sample(); gap.members[0].sourceState = 'ABSENT'; gap.observed.includedGameIds = []; gap.scope.aggregation = 'NO_OBSERVATION';
    const other = sample(); other.members[0].gameId = '2026_02_NO_BAL'; other.members[0].week = 2; other.observed.includedGameIds = ['2026_02_NO_BAL']; other.request.period.weeks = [2];
    const result = choiceGroups(game, archive(gap, other), defaultChoice);
    expect(result.primary.map(x => x.d)).toEqual([gap]); expect(result.other[0].d).toBe(other);
  });
  it('keeps another season separate and excludes contradictory associations', () => {
    const historical = sample(); historical.request.season = 2025; historical.request.phase = 'POST'; historical.members[0].gameId = '2025_19_BAL_IND';
    const contradictory = sample(); contradictory.members[0].week = 2;
    const result = choiceGroups(game, archive(historical, contradictory), defaultChoice);
    expect(result.primary).toEqual([]); expect(result.archive.map(x => x.d)).toEqual([historical]); expect(result.other).toEqual([]);
  });
  it('preserves choices, week and filter on return while removing nominal reading IDs', () => {
    const q = new URLSearchParams('season=2026&week=2&filter=participants&game=2026_02_NO_BAL&team=BAL&side=def&play=classified_pass&entry=real&observation=sha256:abc&details=open');
    const returned = new URLSearchParams(journeyHref(q, gameChange).slice(2));
    expect(returned.get('game')).toBe('2026_02_NO_BAL'); expect(returned.get('observation')).toBeNull(); expect(returned.get('side')).toBe('def');
    const calendar = new URLSearchParams(journeyHref(q, calendarChange).slice(2));
    expect(calendar.get('game')).toBeNull(); expect(calendar.get('week')).toBe('2'); expect(calendar.get('filter')).toBe('participants'); expect(calendar.get('play')).toBe('classified_pass');
  });
});

describe('available participant orientation, independent of calendar position', () => {
  const noBal = { ...game, gameId: '2026_02_NO_BAL', week: 2, awayTeam: { teamAbbr: 'NO' }, homeTeam: { teamAbbr: 'BAL' } } as Game;
  const inGame = (team: string, g: Game = noBal) => { const d = sample(); d.subject.team = team; d.members[0].gameId = g.gameId; d.members[0].week = g.week; d.request.period.weeks = [g.week]; d.observed.includedGameIds = [g.gameId]; return d; };
  it('orients NO × BAL to the only participant with an individual document', () => {
    expect(readChoice(noBal, new URLSearchParams(), undefined, archive(inGame('BAL'))).team).toBe('BAL');
  });
  it('orients to an available visitor too', () => {
    expect(readChoice(game, new URLSearchParams(), undefined, archive(inGame('BAL', game))).team).toBe('BAL');
  });
  it('breaks equal availability by literal abbreviation, independent of home/away or document order', () => {
    const a = archive(inGame('NO'),inGame('BAL'));
    expect(readChoice(noBal, new URLSearchParams(), undefined, a).team).toBe('BAL');
    expect(readChoice({ ...noBal, homeTeam: noBal.awayTeam, awayTeam: noBal.homeTeam },new URLSearchParams(),undefined,a).team).toBe('BAL');
    expect(a.documents[0].d.subject.team).toBe('NO');
  });
  it('respects an explicit participant without a reading and retains dimensions', () => {
    expect(readChoice(noBal, new URLSearchParams('team=NO&side=def&play=classified_rush'),undefined,archive(inGame('BAL')))).toEqual({team:'NO',side:'def',play:'classified_rush'});
  });
  it('does not establish availability from an unavailable archive', () => {
    const c=readChoice(noBal,new URLSearchParams(),undefined,null);
    expect(c.team).toBe('BAL'); // lexical fallback only, no document opened
    expect(choiceGroups(noBal,archive(),c)).toEqual({primary:[],includes:[],other:[],archive:[]});
  });
  it('prefers an individual relation over inclusive and never promotes the latter', () => {
    const inclusive=inGame('NO'); inclusive.members.push({...inclusive.members[0],gameId:'another',week:1});inclusive.scope.aggregation='MULTI_GAME';inclusive.request.period.weeks=[1,2];
    const a=archive(inclusive,inGame('BAL'));
    expect(readChoice(noBal,new URLSearchParams(),undefined,a).team).toBe('BAL');
    const groups=choiceGroups(noBal,a,{team:'NO',side:'off',play:'general'});
    expect(groups.primary).toHaveLength(0);expect(groups.includes[0].d).toBe(inclusive);
  });
  it('keeps gap, another period and incompatible nominal IDs separate', () => {
    const gap=inGame('BAL');gap.members[0].sourceState='ABSENT';gap.observed.includedGameIds=[];gap.scope.aggregation='NO_OBSERVATION';
    const incompatible=inGame('IND');
    const a=archive(gap,incompatible);
    expect(readChoice(noBal,new URLSearchParams(),incompatible,a).team).toBe('BAL');
    expect(choiceGroups(noBal,a,{team:'BAL',side:'off',play:'general'}).primary.map(x=>x.d)).toEqual([gap]);
    expect(incompatible.subject.team).toBe('IND');
  });
  it('preserves search origin in another week through nominal reading and return, including media selection', () => {
    const q=new URLSearchParams('season=2026&week=3&scope=season&q=BAL&filter=participants&page=2&explore=open&media=helmets');
    const reading=new URLSearchParams(journeyHref(q,{game:noBal.gameId,entry:'real',observation:'nominal'}).slice(2));
    const returned=new URLSearchParams(journeyHref(reading,calendarChange).slice(2));
    for(const [key,value] of q)expect(returned.get(key)).toBe(value);
  });
});
