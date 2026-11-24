import { describe, expect, it } from 'vitest';
import { relation, relationText, gameState } from './relations';
import { journeyHref, calendarChange, gameChange } from './state';
import type { DTO } from '../local-editorial/observations/model';
import type { Game } from '../src/services/types';
const game = { gameId: '2026_01_BAL_IND', season: 2026, week: 1, gameType: 'REG', gameday: '2026-09-13', homeTeam: { teamAbbr: 'IND' }, awayTeam: { teamAbbr: 'BAL' }, homeScore: null, awayScore: null, result: null } as Game;
// Relation unit fixtures only; operational documents always come from the full reader.
const sample = (): DTO => ({ subject: { team: 'BAL' }, request: { season: 2026, phase: 'REG', period: { weeks: [1] } }, members: [{ gameId: game.gameId, week: 1, round: 'REG', sourceState: 'PRESENT' }], observed: { includedGameIds: [game.gameId] }, scope: { aggregation: 'SINGLE_GAME' } } as DTO);
describe('document-proven game relationships', () => {
  it('requires exclusive membership for an individual game', () => expect(relation(game, sample())).toBe('individual'));
  it('keeps a multi-game sample inclusive even with a single source', () => {
    const d = sample(); d.members.push({ ...d.members[0], gameId: '2026_02_NO_BAL', week: 2, sourceState: 'ABSENT' }); d.request.period.weeks = [1,2]; d.scope.aggregation = 'MULTI_GAME';
    expect(relation(game, d)).toBe('includes'); expect(relationText('includes', d)).toContain('inclui este jogo');
    const absent = { ...game, gameId: '2026_02_NO_BAL', week: 2 };
    expect(relation(absent, d)).toBe('gap'); expect(relationText('gap', d)).toContain('não oferece estatísticas desse jogo');
  });
  it('never substitutes a week for a missing member', () => { const d = sample(); d.members = []; expect(relation(game,d)).toBe('other'); });
  it.each(['team','season','phase','week','requested','round','included','scope','multiple'])('rejects contradictory %s', key => {
    const d = sample();
    if(key==='team') d.subject.team='DAL'; if(key==='season') d.request.season=2025; if(key==='phase') d.request.phase='POST';
    if(key==='week') d.members[0].week=2; if(key==='requested') d.request.period.weeks=[2]; if(key==='round') d.members[0].round='WC';
    if(key==='included') d.observed.includedGameIds=[]; if(key==='scope') d.scope.aggregation='NO_OBSERVATION'; if(key==='multiple') d.members.push({...d.members[0], gameId:'other'});
    expect(relation(game,d)).toBe('incompatible');
  });
  it('separates historical phase/season archives only for participants', () => {
    const d=sample(); d.request.season=2025; d.request.phase='POST'; d.members[0].gameId='2025_19_BAL_IND';
    expect(relation(game,d)).toBe('archive'); d.subject.team='NE'; expect(relation(game,d)).toBe('incompatible');
  });
  it('shows an absent member as a gap rather than zero', () => { const d=sample(); d.members[0].sourceState='ABSENT'; d.observed.includedGameIds=[]; d.scope.aggregation='NO_OBSERVATION'; expect(relation(game,d)).toBe('gap'); });
});
describe('preserved calendar state', () => {
  const now=new Date('2026-10-22T12:00:00Z');
  it('does not label a past null result as future', () => expect(gameState(game,now).label).toBe('Resultado não disponível neste arquivo'));
  it('uses a future calendar date without live assumptions', () => expect(gameState({...game,gameday:'2026-12-01'},now).label).toContain('agendado conforme'));
  it.each([[1,null,null],[1,2,1],[-1,2,-3],[1.2,2,-.8],[NaN,2,0]])('refuses invalid score trio %s/%s/%s', (homeScore,awayScore,result) => {
    const s=gameState({...game,homeScore,awayScore,result},now);expect(s.score).toBeNull();expect(s.label).toContain('insuficiente');
  });
  it('shows only a valid atomic result', () => expect(gameState({...game,homeScore:10,awayScore:7,result:3},now).score).toBe('BAL 7 × 10 IND'));
  it.each([null,'garbage','2026-02-30'])('keeps insufficient dates explicit %s', gameday => expect(gameState({...game,gameday},now).label).toContain('insuficiente'));
  it('preserves calendar return and nominal IDs without a DTO', () => {
    const q=new URLSearchParams('season=2026&week=2&filter=participants&game=2026_02_NO_BAL&entry=real-recovery&observation=sha256:abc&details=open');
    expect(journeyHref(q,calendarChange)).toBe('/?season=2026&week=2&filter=participants');
    expect(journeyHref(q,gameChange)).toContain('game=2026_02_NO_BAL');expect(journeyHref(q,gameChange)).not.toContain('observation');
  });
});
