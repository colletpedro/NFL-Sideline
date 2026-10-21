import { describe, expect, it } from 'vitest';
import { games, scoreboard, summarize, type Game } from './fixtures';
import { readSlice, recoverySlices } from './editorial';
import { epaScale } from './chartScale';
import { navigationContext, readState } from './state';

const scenario = (epa: [number, number], successes: [number, number] = [10, 10], counts: [number, number] = [20, 20]): Game => ({
  ...games[0], sides: games[0].sides.map((side, i) => ({ ...side, halves: [
    { ...side.halves![0], pass: { plays: counts[i], success: successes[i], epa: epa[i] * counts[i], yards: 120 } },
    side.halves![1],
  ] })) as Game['sides'],
});

describe('synthetic slice interpretation', () => {
  it('changes the decision, title and supporting values with the selected slice', () => {
    const first = readSlice(games[0], 'first', 'pass'), second = readSlice(games[0], 'second', 'pass');
    expect(first.decision).toBe('split');
    expect(second.decision).toBe('efficiency');
    expect(first.title).not.toBe(second.title);
    expect(first.context).toMatchObject({ period: 'first', play: 'pass' });
    expect(second.samples.map(s => s.plays)).toEqual([18, 20]);
    expect(second.samples[1].epa).toBeCloseTo(.23);
    const rush = readSlice(games[0], 'second', 'rush');
    expect(rush.decision).toBe('split');
    expect(rush.title).toContain('NE');
    expect(rush.context).toMatchObject({ period: 'second', play: 'rush' });
    expect(rush.samples.map(s => s.plays)).toEqual([12, 14]);
    expect(rush.samples[0].epa).toBeCloseTo(-.1);
    expect(rush.samples[1].success).toBeCloseTo(7 / 14);
    expect(rush.evidence[0].value).toBeCloseTo(.16);
  });
  it('describes opposing EPA and success directions, rather than picking an overall winner', () => {
    const game = games.find(g => g.id === 'baltimore-pittsburgh')!;
    const reading = readSlice(game, 'game', 'pass');
    expect(reading.decision).toBe('divergence');
    expect(reading.samples[0].epa).toBeGreaterThan(reading.samples[1].epa!);
    expect(reading.samples[0].success).toBeLessThan(reading.samples[1].success!);
    expect(reading.evidence.map(e => e.metric)).toEqual(['epaGap', 'successGap']);
    expect(reading.text).toContain('Baltimore');
    expect(reading.text).toContain('Pittsburgh');
    const oppositeSigns = readSlice(scenario([.15, -.1], [8, 12]), 'first', 'pass');
    expect(oppositeSigns.decision).toBe('divergence');
    expect(oppositeSigns.text).toContain('negativo');
    expect(oppositeSigns.evidence.map(e => e.metric)).toEqual(['epaGap', 'successGap']);
  });
  it('distinguishes a passing comparison from a rushing comparison in the overview', () => {
    const reading = readSlice(games[0], 'game', 'all');
    expect(reading.decision).toBe('cross');
    expect(reading.evidence.map(e => e.metric)).toEqual(['passGap', 'rushGap']);
  });
  it('does not rank averages equal at displayed precision, including negative zero', () => {
    const reading = readSlice(scenario([.1004, .1001]), 'first', 'pass');
    expect(reading.decision).toBe('precision');
    expect(reading.evidence[0].value).toBeCloseTo(.0003);
    expect(readSlice(scenario([.0001, -.0001]), 'first', 'pass').decision).toBe('precision');
    expect(readSlice(scenario([.101, .109]), 'first', 'pass').decision).toBe('close');
    expect(readSlice(scenario([.1, .1]), 'first', 'pass').decision).toBe('precision');
  });
  it('keeps missing coverage and zero denominators out of comparative claims', () => {
    const missing = games.find(g => g.id === 'kansas-city-buffalo')!;
    const reading = readSlice(missing, 'second', 'pass');
    expect(reading.decision).toBe('unavailable');
    expect(reading.samples[1]).toMatchObject({ team: 'BUF', plays: null, epa: null, success: null });
    expect(reading.evidence).toEqual([]);
    expect(summarize(missing.sides[1], 'game', 'pass')).toBeNull();
    expect(recoverySlices(missing, 'second', 'pass')).toContainEqual(['second', 'rush']);
    const zero = readSlice(scenario([0, .1], [0, 10], [0, 20]), 'first', 'pass');
    expect(zero.decision).toBe('insufficient');
    expect(zero.samples[0].epa).toBeNull();
    expect(zero.samples[0].success).toBeNull();
    expect(readSlice(scenario([.1, .2], [4, 10], [8, 20]), 'first', 'pass').decision).toBe('insufficient');
  });
  it('separates volume from the average when the larger sample belongs to the other attack', () => {
    const reading = readSlice(scenario([.15, .1], [10, 15], [20, 30]), 'first', 'pass');
    expect(reading.decision).toBe('efficiency');
    expect(reading.samples[1].plays).toBeGreaterThan(reading.samples[0].plays!);
    expect(reading.text).toContain('mais jogadas');
  });
  it('does not leak result or samples into pregame, even if result fields are attached accidentally', () => {
    const pregame = { ...games.find(g => g.status === 'pregame')!, sides: games[0].sides };
    expect(scoreboard(pregame)).toBeNull();
    const reading = readSlice(pregame, 'second', 'pass');
    expect(reading.decision).toBe('pregame');
    expect(reading.samples.every(s => s.epa === null && s.plays === null)).toBe(true);
  });
});

describe('current matchup versus return context', () => {
  it('keeps the archive matchup and the complete selection in the header destination', () => {
    const nav = navigationContext('/confronto/baltimore-dallas', '?round=7&period=second&play=rush&details=open');
    expect(nav.current?.id).toBe('baltimore-dallas');
    expect(nav.gameRound).toBe(6);
    expect(nav.originRound).toBe(7);
    expect(nav.centralHref).toBe('/?round=7');
    expect(nav.analysisHref).toBe('/confronto/baltimore-dallas?round=7&period=second&play=rush&details=open');
    expect(readState(nav.analysisHref.split('?')[1])).toMatchObject({ period: 'second', play: 'rush', details: true });
  });
  it('uses the feature on the central and the matchup round on direct navigation without origin', () => {
    expect(navigationContext('/', '?round=7').analysisHref).toBe('/confronto/dallas-new-england?round=7');
    expect(navigationContext('/confronto/baltimore-dallas', '').centralHref).toBe('/?round=6');
    expect(navigationContext('/confronto/green-bay-chicago', '?round=7&period=second&play=rush').analysisHref).toBe('/confronto/green-bay-chicago?round=7');
  });
});

describe('signed scale policy', () => {
  it('extends both ends explicitly and positions every synthetic value inside its selected domain', () => {
    expect(epaScale([.5]).max).toBe(.6);
    expect(epaScale([-.3]).min).toBe(-.4);
    expect(epaScale([null]).min).toBe(-.2);
    const samples = games.flatMap(g => g.sides.flatMap(s => (['first', 'second'] as const).flatMap(p => (['pass', 'rush'] as const).map(f => summarize(s, p, f)))));
    const means = samples.map(s => s?.plays ? s.epa / s.plays : null), scale = epaScale(means);
    for (const value of means) if (value !== null) {
      expect(scale.position(value)).toBeGreaterThanOrEqual(0);
      expect(scale.position(value)).toBeLessThanOrEqual(100);
    }
    expect(scale.position(0)).toBeGreaterThan(0);
  });
});

