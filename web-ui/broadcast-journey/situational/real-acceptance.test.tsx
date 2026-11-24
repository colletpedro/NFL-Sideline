import {loadRealFixture} from './real-fixture.mjs';
import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {validateSnapshot,percent} from './model';
import {SituationalContent} from './SituationalReading';
// Explicit opt-in: real private artifacts stay outside the checkout and public build.
const fixture=loadRealFixture();
describe.skipIf(!fixture)('real preserved situational acceptance (operator configured)',()=>{
  it('reconciles all 384 rendered metric contexts and percentages with independent raw audit',()=>{
    if(!fixture) throw new Error('Operator fixture not configured');
    const s=validateSnapshot({transportVersion:'situational-response-v1',bundleId:fixture.bundleId,data:fixture.data});
    for(const d of s.data.documents)for(const [family,key] of [['third','third'],['redzone','redZone']] as const){
      const metric=d[key],formatted=percent(metric.ratio),expected=fixture.rounded[`${d.id}/${key}`];
      expect(formatted).toBe(expected);
      const html=renderToStaticMarkup(<SituationalContent d={d} snapshot={s} family={family}/>);
      expect(html).toContain(`data-situational="${d.id}"`);expect(html).toContain(`${metric.numerator} / ${metric.denominator}`);
      if(formatted)expect(html).toContain(formatted);else expect(html).toContain('Sem taxa');
      for(const g of d.games){expect(html).toContain(`${g.away} × ${g.home}`);expect(html).toContain(`Semana ${g.week}`);}
      expect(html).toContain(d.perspective==='def'?'permitido ao ataque adversário':'Ataque');
    }
  });
});
