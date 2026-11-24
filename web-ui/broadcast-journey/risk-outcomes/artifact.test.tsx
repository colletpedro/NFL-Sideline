// @vitest-environment jsdom
import {describe,it,expect} from 'vitest';
import {readFileSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {renderToStaticMarkup} from 'react-dom/server';
import {Calculation} from './Lab';
import {OutcomeMetrics} from './Metrics';
import {outcomePeriod,outcomeCounts,validateOutcomeIndex,validateOutcomeDetail,B2_SHA} from './model';
import {outcomeLayout,interceptionNumber} from './communication';
import {number} from '../risk-lab/communication';
describe('all pinned outcome players and periods through rendered presentation',()=>{
 it('reconciles all scientific pass probabilities, periods, two contributions, DOM numbers and chart units',()=>{
  const store=process.env.NFL_RISK_OUTCOMES_QA_STORE;expect(store,'Configure NFL_RISK_OUTCOMES_QA_STORE; do not skip source cases').toBeTruthy();expect(existsSync(join(store!,'current.json'))).toBe(true);
  const read=(p:string)=>JSON.parse(readFileSync(p,'utf8')),current=read(join(store!,'current.json')),base=join(store!,'packages',current.packageId),i=validateOutcomeIndex(read(join(base,'index.json')));
  for(const [path,digest] of Object.entries(read(join(base,'integrity.json')).files))expect(createHash('sha256').update(readFileSync(join(base,path))).digest('hex')).toBe(digest);
  expect(i.model.sha256).toBe(B2_SHA);expect(i.players).toHaveLength(66);expect(i.comparison.sameEligiblePasses).toBe(true);
  for(const player of i.players){const d=validateOutcomeDetail(read(join(base,'players',player.id+'.json')),i,player.id);
   for(const period of ['all',...i.coverage.weeks.map(String)]){const plays=d.plays.filter(p=>period==='all'||p.week===Number(period)),c=outcomeCounts(plays),p=outcomePeriod(player,period);
    for(const key of ['eligiblePasses','observedInterceptions','interceptionWorthyPasses','expectedInterceptions','expectedFromClassified','expectedFromNotClassified','differenceInterceptions'] as const)expect(p[key]).toBeCloseTo(c[key],10);
    const doc=new DOMParser().parseFromString(renderToStaticMarkup(<><OutcomeMetrics c={p}/><Calculation player={p} index={i}/></>),'text/html');
    if(p.eligiblePasses){expect(Number(doc.querySelector('[data-expected-total]')?.getAttribute('data-expected-total'))).toBe(p.expectedInterceptions);for(const [group,value,passes] of [['classified',p.expectedFromClassified,p.interceptionWorthyPasses],['not-classified',p.expectedFromNotClassified,p.eligiblePasses-p.interceptionWorthyPasses]] as const){const element=doc.querySelector(`[data-contribution-group="${group}"]`)!;expect(Number(element.getAttribute('data-contribution'))).toBe(value);expect(Number(element.getAttribute('data-passes'))).toBe(passes);}expect(doc.querySelector('[data-metric=expected-interceptions] dd')?.textContent).toBe(interceptionNumber(p.expectedInterceptions));}else expect(doc.querySelector('[data-metric=expected-interceptions] dd')?.textContent).toBe('—');
   }
  }
  for(const period of ['all',...i.coverage.weeks.map(String)])for(const scale of ['total','per100'] as const){const players=i.players.map(p=>outcomePeriod(p,period)).filter(p=>p.eligiblePasses);for(const width of [240,320,640,1100]){const l=outcomeLayout(players,scale,width);expect(l.points).toHaveLength(players.length);for(const pt of l.points){const den=scale==='total'?1:pt.player.eligiblePasses/100;expect(pt.x).toBeCloseTo(pt.player.expectedInterceptions/den,12);expect(pt.y).toBeCloseTo(pt.player.observedInterceptions/den,12);}}}
  for(const [id,obs,exp] of [['00-0035710',9,10.49],['00-0029604',5,5.08],['00-0034869',9,5.31],['00-0036264',6,8.50],['00-0023459',6,4.00],['00-0027973',1,.55]] as const){const p=i.players.find(p=>p.id===id)!;expect(p.observedInterceptions).toBe(obs);expect(number(p.expectedInterceptions,2)).toBe(number(exp,2));}
  const rodgers=validateOutcomeDetail(read(join(base,'players','00-0023459.json')),i,'00-0023459');expect(rodgers.plays.filter(p=>!p.ftnInterceptionWorthy&&p.observedInterception)).toHaveLength(5);
 });
});
