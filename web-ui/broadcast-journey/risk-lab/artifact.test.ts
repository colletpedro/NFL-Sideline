import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {validateIndex,playerPeriod,validateDetail,counts} from './model';
import {scatterLayout} from './communication';
const store=process.env.NFL_RISK_LAB_QA_STORE;
describe.skipIf(!store)('frozen local artifact: collective coordinates and totals',()=>{
 it('reconciles every player in every available week and both units, including coincident and low volume points',()=>{const active=JSON.parse(readFileSync(join(store!,'current.json'),'utf8')),base=join(store!,'packages',active.packageId),index=validateIndex(JSON.parse(readFileSync(join(base,'index.json'),'utf8')));expect(index.players.filter(p=>p.positionClass==='qb')).toHaveLength(57);
 for(const period of ['all',...index.coverage.weeks.map(String)])for(const scale of ['total','per100'] as const){const players=index.players.filter(p=>p.positionClass==='qb').map(p=>playerPeriod(p,period)).filter(p=>p.passes>0);for(const width of [260,640,1000]){const l=scatterLayout(players,scale,width);expect(l.points).toHaveLength(players.length);expect(l.points.map(p=>p.player.id)).toEqual(players.map(p=>p.id));for(const pt of l.points){const den=scale==='total'?1:pt.player.passes/100;expect(pt.x).toBeCloseTo(pt.player.expected/den,12);expect(pt.y).toBeCloseTo(pt.player.observed/den,12);expect(pt.x).toBeLessThanOrEqual(l.domain.max);expect(pt.y).toBeLessThanOrEqual(l.domain.max);}}}
 for(const p of index.players){const detail=validateDetail(JSON.parse(readFileSync(join(base,'players',p.id+'.json'),'utf8')),index,p.id);for(const period of ['all',...index.coverage.weeks.map(String)]){const c=counts(detail.plays.filter(p=>period==='all'||p.week===Number(period))),summary=playerPeriod(p,period);expect(c.passes).toBe(summary.passes);expect(c.observed).toBe(summary.observed);expect(c.interceptions).toBe(summary.interceptions);expect(c.expected).toBeCloseTo(summary.expected,10);}}
 const daniel=index.players.find(p=>p.id==='00-0035710')!;expect([daniel.passes,daniel.games,daniel.observed,daniel.interceptions]).toEqual([267,8,17,9]);expect(daniel.expected).toBeCloseTo(8.660127799064037,12);
 });
});
