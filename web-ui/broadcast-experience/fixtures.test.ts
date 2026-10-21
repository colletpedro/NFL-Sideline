import { describe, expect, it } from 'vitest';
import { countPair, games, score, summarize, rate, signed, type Period, type PlayType } from './fixtures';
import { gameForId, readState } from './state';

describe('synthetic broadcast scenarios', () => {
  it('reconciles periods, play types and counts without turning absence into zero', () => {
    for (const game of games) for (const side of game.sides) {
      expect(side.quarters.every(n => Number.isInteger(n) && n >= 0)).toBe(true);
      for (const period of ['game', 'first', 'second'] as Period[]) {
        const all = summarize(side, period, 'all');
        const pass = summarize(side, period, 'pass'), rush = summarize(side, period, 'rush');
        for (const key of ['plays', 'success', 'epa', 'yards'] as const) expect(all[key]).toBeCloseTo(pass[key] + rush[key]);
        for (const play of ['all', 'pass', 'rush'] as PlayType[]) {
          const stat = summarize(side, period, play);
          expect(stat.plays).toBeGreaterThan(0);
          expect(stat.success).toBeLessThanOrEqual(stat.plays);
          expect(stat.success).toBeGreaterThanOrEqual(0);
          expect(stat.epa / stat.plays).toBeGreaterThanOrEqual(-.2);
          expect(stat.epa / stat.plays).toBeLessThanOrEqual(.4);
        }
      }
      for (const play of ['all', 'pass', 'rush'] as PlayType[]) {
        for (const key of ['plays', 'success', 'epa', 'yards'] as const) {
          expect(summarize(side, 'game', play)[key]).toBeCloseTo(summarize(side, 'first', play)[key] + summarize(side, 'second', play)[key]);
        }
      }
    }
    expect(countPair(games[1].sides[0], 'game', 'redzone')).toBeNull();
    expect(rate({ plays: 0, success: 0, epa: 0, yards: 0 })).toBe('Sem amostra');
    expect(countPair(games[0].sides[0], 'game', 'third')).toEqual([7, 13]);
  });
  it('keeps the approved score and passing total, and exposes negative EPA truthfully', () => {
    expect(games[0].sides.map(score)).toEqual([27, 24]);
    expect(summarize(games[0].sides[0], 'game', 'pass').yards).toBe(312);
    expect(rate(summarize(games[0].sides[0], 'game', 'all'))).toBe('50,0%');
    expect(signed(summarize(games[0].sides[0], 'game', 'rush').epa / 26)).toBe('−0,078');
  });
  it('does not schedule the same team twice in a demonstration round', () => {
    for (const round of [6, 7, 8]) {
      const members = games.filter(g => g.round === round).flatMap(g => g.sides.map(s => s.team));
      expect(new Set(members).size).toBe(members.length);
    }
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
