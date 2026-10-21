import { describe, expect, it } from 'vitest';
import { countPair, games, score, scoreboard, summarize, rate, signed, type Period, type PlayType } from './fixtures';
import { gameForId, readState } from './state';

describe('synthetic broadcast scenarios', () => {
  it('reconciles periods, play types and counts without turning absence into zero', () => {
    for (const game of games) for (const side of game.sides) {
      if (game.status === 'pregame') {
        expect(side.quarters).toBeNull();
        expect(side.halves).toBeNull();
        expect(scoreboard(game)).toBeNull();
      } else expect(side.quarters?.every(n => Number.isInteger(n) && n >= 0)).toBe(true);
      for (const period of ['game', 'first', 'second'] as Period[]) {
        for (const situation of ['third', 'redzone'] as const) {
          const counts = countPair(side, period, situation);
          if (counts) {
            expect(counts.every(n => Number.isInteger(n) && n >= 0)).toBe(true);
            expect(counts[0]).toBeLessThanOrEqual(counts[1]);
          }
        }
        const all = summarize(side, period, 'all');
        const pass = summarize(side, period, 'pass'), rush = summarize(side, period, 'rush');
        if (pass && rush) for (const key of ['plays', 'success', 'epa', 'yards'] as const) expect(all![key]).toBeCloseTo(pass[key] + rush[key]);
        else expect(all).toBeNull();
        for (const play of ['all', 'pass', 'rush'] as PlayType[]) {
          const stat = summarize(side, period, play);
          if (!stat) continue;
          expect(Object.values(stat).every(Number.isFinite)).toBe(true);
          expect(Number.isInteger(stat.plays)).toBe(true);
          expect(Number.isInteger(stat.success)).toBe(true);
          expect(stat.plays).toBeGreaterThanOrEqual(0);
          expect(stat.success).toBeLessThanOrEqual(stat.plays);
          expect(stat.success).toBeGreaterThanOrEqual(0);
        }
      }
      for (const play of ['all', 'pass', 'rush'] as PlayType[]) {
        const total = summarize(side, 'game', play), first = summarize(side, 'first', play), second = summarize(side, 'second', play);
        if (!first || !second) expect(total).toBeNull();
        else for (const key of ['plays', 'success', 'epa', 'yards'] as const) expect(total![key]).toBeCloseTo(first[key] + second[key]);
      }
    }
    expect(countPair(games[1].sides[0], 'game', 'redzone')).toBeNull();
    expect(rate({ plays: 0, success: 0, epa: 0, yards: 0 })).toBe('Sem amostra');
    expect(countPair(games[0].sides[0], 'game', 'third')).toEqual([7, 13]);
  });
  it('keeps the approved score and passing total, and exposes negative EPA truthfully', () => {
    expect(games[0].sides.map(score)).toEqual([27, 24]);
    expect(summarize(games[0].sides[0], 'game', 'pass')!.yards).toBe(312);
    expect(rate(summarize(games[0].sides[0], 'game', 'all'))).toBe('50,0%');
    expect(signed(summarize(games[0].sides[0], 'game', 'rush')!.epa / 26)).toBe('−0,078');
    expect(signed(-.0001)).toBe('0,000');
  });
  it('does not schedule the same team twice in a demonstration round', () => {
    for (const round of [6, 7, 8]) {
      const members = games.filter(g => g.round === round).flatMap(g => g.sides.map(s => s.team));
      expect(new Set(members).size).toBe(members.length);
    }
    const round = games.filter(g => g.round === 7);
    expect(round.length).toBeGreaterThanOrEqual(4);
    expect(round.some(g => g.status === 'pregame')).toBe(true);
    expect(round.some(g => g.status === 'final')).toBe(true);
    expect(round.some(g => g.status === 'final' && g.sides.some(s => summarize(s, 'second', 'pass') === null))).toBe(true);
  });
});

describe('shareable navigation state', () => {
  it('restores relevant selections and sanitizes invalid query parameters', () => {
    expect(readState('?round=6&period=second&play=rush&details=open')).toEqual({ round: 6, period: 'second', play: 'rush', details: true });
    expect(readState('?round=900&period=invalid&play=invalid&details=no')).toEqual({ round: 7, period: 'game', play: 'all', details: false });
    expect(gameForId('baltimore-dallas')?.round).toBe(6);
    expect(gameForId('unknown')).toBeUndefined();
  });
});
