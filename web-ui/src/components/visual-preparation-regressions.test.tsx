import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { transpileModule, ScriptTarget, ModuleKind } from 'typescript';
import dashboardSource from '../pages/MatchupDashboard.tsx?raw';
import TacticalComparison from './TacticalComparison';
import type { TeamWeekMetrics } from '../services/types';

// Preparation only: exercise the actual legacy function without mounting the page
// or exporting a production helper solely for tests. Fail outside it.fails if extraction breaks.
const start = dashboardSource.indexOf('function metricForWeek(');
const end = dashboardSource.indexOf('/** Parse the cached', start);
if (start < 0 || end < start) throw new Error('Legacy extraction changed: migrate these regressions to the replacement API.');
const compiled = transpileModule(dashboardSource.slice(start, end), {
  compilerOptions: { target: ScriptTarget.ES2020, module: ModuleKind.None },
}).outputText;
const metricForWeek = new Function(`${compiled}; return metricForWeek;`)() as
  (series: TeamWeekMetrics[] | undefined, week: number) => TeamWeekMetrics | null;
const metric = (week: number, value = .1): TeamWeekMetrics => ({
  id: { season: 2026, week, teamAbbr: 'AAA' }, offEpaPlay: value,
  offEpaPass: null, offEpaRush: null, defEpaPass: null, defEpaRush: null,
  dropbackRate: null, playsOffense: null,
});
const team = (teamAbbr: string) => ({ teamAbbr, teamName: teamAbbr, conference: null, division: null, logoUrl: null });
const render = (away: number, home: number) => renderToStaticMarkup(<TacticalComparison
  awayTeam={team('AAA')} homeTeam={team('BBB')} awayMetric={metric(2, away)} homeMetric={metric(2, home)} week={3}/>);

// it.fails means KNOWN DEFECT, not a fix or skipped test. Vitest fails on unexpected success.
// On correction, remove .fails and keep the intended assertion. See visual-v1/known-defects.md.
describe('visual preparation: open legacy defects', () => {
  it('executes the legacy selection and actual component successfully', () => {
    expect(metricForWeek([metric(2)], 3)?.id.week).toBe(2);
    expect(metricForWeek(undefined, 3)).toBeNull();
    expect(render(-.4, .1)).toContain('tac-team');
  });
  it.fails('TIME-01: a pregame cannot fall forward to a future week', () => {
    expect(metricForWeek([metric(4)], 3)).toBeNull();
  });
  it.fails('TIME-02: a pregame excludes its own week', () => {
    expect(metricForWeek([metric(3)], 3)).toBeNull();
  });
  it.fails('TIME-03: latest prior week is invariant under input order', () => {
    expect(metricForWeek([metric(2), metric(1)], 3)?.id.week).toBe(2);
  });
  it.fails('TIME-04: heading identifies observed week, not target week', () => {
    // Both observations are week 2; a heading claiming Week 03 is false.
    expect(render(-.4, .1)).not.toContain('Week 03 · EPA per play');
  });
  it.fails('SIGN-01: flipping only the sign must change graphical geometry', () => {
    const geometry = (html: string) => [...html.matchAll(/<span class="fill" style="([^"]+)"/g)]
      .map(match => match[1].replace(/(?:background|opacity):[^;]+;?/g, ''));
    expect(geometry(render(-.4, .1))).not.toEqual(geometry(render(.4, .1)));
  });
});
