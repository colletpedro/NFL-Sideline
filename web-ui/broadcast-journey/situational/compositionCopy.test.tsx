import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { compositionFact } from './compositionCopy';
import { SituationalContent } from './SituationalReading';
import type { Snapshot, SituationalDocument } from './model';
import { loadRealFixture } from './real-fixture.mjs';
import { validateSnapshot } from './model';

// Explicitly synthetic, presentation-only fixtures; never loaded by the application.
function synthetic(): SituationalDocument {
  const m = {status:'AVAILABLE' as const, numerator:5, denominator:12, denominatorState:'POSITIVE' as const,
    ratio:{numerator:5,denominator:12},unitIds:[],excludedIds:[],exclusions:{},ambiguousIds:[]};
  return {id:'SYNTHETIC',team:'NYJ',perspective:'off',season:2026,phase:'REG',weeks:[1],
    games:[{gameId:'SYNTHETIC',home:'TEN',away:'NYJ',opponent:'TEN',week:1}],
    third:{...structuredClone(m),byDistance:{short:{numerator:1,denominator:2},medium:{numerator:1,denominator:3},long:{numerator:3,denominator:7},unknown:{numerator:0,denominator:0}},byType:{pass:{numerator:5,denominator:12},run:{numerator:0,denominator:0}},penaltyFirstDowns:{included:0,excluded:0},sacks:0,scrambles:0},
    redZone:{...structuredClone(m),numerator:2,denominator:3,ratio:{numerator:2,denominator:3},outcomes:{TOUCHDOWN:2,FIELD_GOAL:1},observedEntries:3}};
}
const snapshot: Snapshot={transportVersion:'situational-response-v1',bundleId:'sha256:test-only',data:{contractVersion:'situational-v1',documents:[],definitionsVersion:'1.0.0',calculationVersion:'1.0.0',ledgerHash:'sha256:ledger',provenance:{rawHash:'sha256:raw',materializationId:'sha256:materialization',inputId:'sha256:input'},guarantees:{completeness:'UNKNOWN',expectedCoverage:'UNKNOWN',epaModel:'UNKNOWN',temporalKnowledge:'UNKNOWN'}}};
function describedThird(text: string) {
  const m=text.match(/(\d+) das (\d+) tentativas exigiam ([^;]+); (\d+) dessas (\d+)/);
  if (!m) throw new Error('Expected count-bearing distance description');
  return {attempts:Number(m[1]),total:Number(m[2]),distance:m[3],converted:Number(m[4]),conversionBase:Number(m[5])};
}
describe('local situational composition copy — synthetic cases',()=>{
  it('selects by attempts, binds every count to that band, and does not mutate its document',()=>{
    const d=synthetic(),before=structuredClone(d),f=describedThird(compositionFact(d,'third')!);
    expect(f).toEqual({attempts:7,total:12,distance:'7 ou mais jardas',converted:3,conversionBase:7});
    d.third.byDistance.medium={denominator:8,numerator:4};d.third.byDistance.long={denominator:2,numerator:0};
    const changed=describedThird(compositionFact(d,'third')!);
    expect(changed).toMatchObject({attempts:8,total:12,distance:'4 a 6 jardas',converted:4,conversionBase:8});
    const original=synthetic();compositionFact(original,'third');compositionFact(original,'redzone');expect(original).toEqual(before);
  });
  it('keeps long/medium/short tie priority without claiming a sole most frequent band',()=>{
    const d=synthetic();for(const k of ['short','medium','long'])d.third.byDistance[k]={numerator:2,denominator:4};
    const first=compositionFact(d,'third')!;expect(describedThird(first).distance).toBe('7 ou mais jardas');
    d.third.byDistance=Object.fromEntries(Object.entries(d.third.byDistance).reverse());
    expect(compositionFact(d,'third')).toBe(first);expect(first).not.toMatch(/mais frequente|predominante|isoladamente|maior faixa/i);
    d.third.byDistance.long={denominator:2,numerator:1};d.third.byDistance.short={denominator:5,numerator:2};d.third.byDistance.medium={denominator:5,numerator:2};
    expect(describedThird(compositionFact(d,'third')!).distance).toBe('4 a 6 jardas');
  });
  it('retains unknown distances even when they outnumber the selected known band',()=>{
    const d=synthetic();d.third.byDistance.unknown={numerator:2,denominator:11};d.third.denominator=23;
    const text=compositionFact(d,'third')!,f=describedThird(text);
    expect(f.total).toBe(23);expect(f.attempts).toBe(7);
    expect(text).toMatch(/11 tentativas sem distância informada \(2 conversões\)/);
  });
  it('handles all-unknown distance and a single attempt without inventing a distance',()=>{
    const d=synthetic();for(const k of ['short','medium','long'])d.third.byDistance[k]={denominator:0,numerator:0};
    d.third.byDistance.unknown={denominator:12,numerator:5};let text=compositionFact(d,'third')!;
    expect(text).toMatch(/12 tentativas não têm distância informada/);expect(text).toMatch(/5 dessas 12/);expect(text).not.toMatch(/jardas/);
    d.third.denominator=1;d.third.byDistance.unknown={denominator:1,numerator:0};text=compositionFact(d,'third')!;
    expect(text).toMatch(/única tentativa/);expect(text).toMatch(/não foi convertida/);
    d.third.byDistance.unknown={denominator:0,numerator:0};d.third.byDistance.short={denominator:1,numerator:1};
    expect(compositionFact(d,'third')).toMatch(/única tentativa exigia 1 a 3 jardas; ela foi convertida/);
  });
  it('describes zero conversions in a selected nonempty band without a causal claim',()=>{
    const d=synthetic();d.third.byDistance.long.numerator=0;
    const text=compositionFact(d,'third')!;expect(text).toMatch(/7 das 12/);expect(text).toMatch(/nenhuma foi convertida/);expect(text).not.toMatch(/porque|causou|explica|levou/);
  });
  it('reads each non-TD outcome distinctly and keeps a stable order',()=>{
    const d=synthetic();d.redZone.outcomes={TOUCHDOWN:2,FIELD_GOAL:1,MISSED_FIELD_GOAL:1,TURNOVER:2,DOWNS:3,PUNT:4,END_HALF_GAME:5,OPPONENT_TOUCHDOWN:6,SAFETY:7};d.redZone.denominator=31;
    const text=compositionFact(d,'redzone')!;
    const pairs=[...text.matchAll(/(\d+) campanhas? (?:terminou|terminaram) em (.*?)(?=, | e \d+ campanhas? |\.$)/g)];
    expect(pairs.map(p=>Number(p[1]))).toEqual([d.redZone.outcomes.FIELD_GOAL,d.redZone.outcomes.MISSED_FIELD_GOAL,d.redZone.outcomes.TURNOVER,d.redZone.outcomes.DOWNS,d.redZone.outcomes.PUNT,d.redZone.outcomes.END_HALF_GAME,d.redZone.outcomes.OPPONENT_TOUCHDOWN,d.redZone.outcomes.SAFETY]);
    const labels=pairs.map(p=>p[2]);expect(new Set(labels).size).toBe(8);
    expect(labels[0]).toBe('field goal');expect(labels[1]).toMatch(/perdido ou bloqueado/);expect(labels[2]).toBe('turnover');expect(labels[3]).toMatch(/perda por descidas/);expect(labels[4]).toBe('punt');expect(labels[5]).toMatch(/fim de tempo ou de jogo/);expect(labels[6]).toMatch(/time que defendia/);expect(labels[7]).toBe('safety');
    d.redZone.outcomes=Object.fromEntries(Object.entries(d.redZone.outcomes).reverse());expect(compositionFact(d,'redzone')).toBe(text);
  });
  it('binds a changed field-goal count and a single touchdown without awkward pluralisation',()=>{
    const d=synthetic();d.redZone.numerator=1;d.redZone.outcomes={TOUCHDOWN:1,FIELD_GOAL:2};
    const text=compositionFact(d,'redzone')!;expect(text).toMatch(/de 1 touchdown ofensivo/);
    expect(text).toMatch(new RegExp(`${d.redZone.outcomes.FIELD_GOAL} campanhas terminaram em field goal`));
  });
  it('attributes defense to the opposing offense in both families',()=>{
    const d=synthetic();d.perspective='def';
    expect(compositionFact(d,'third')).toMatch(/^Nas tentativas do ataque adversário,/);
    expect(compositionFact(d,'redzone')).toMatch(/^Nas campanhas do ataque adversário,/);
    expect(compositionFact(d,'redzone')).toMatch(/2 touchdowns ofensivos/);
  });
  it('keeps a single campaign and TD-only samples factual in either perspective',()=>{
    for(const side of ['off','def'] as const){
      const d=synthetic();d.perspective=side;d.redZone.denominator=1;d.redZone.numerator=0;d.redZone.outcomes={DOWNS:1};
      expect(compositionFact(d,'redzone')).toMatch(/única campanha.*terminou em perda por descidas/);
      d.redZone.numerator=1;d.redZone.outcomes={TOUCHDOWN:1};expect(compositionFact(d,'redzone')).toMatch(/única campanha.*terminou em touchdown ofensivo/);
      d.redZone.denominator=4;d.redZone.numerator=4;d.redZone.outcomes={TOUCHDOWN:4};
      const text=compositionFact(d,'redzone')!;expect(text).toMatch(/4 campanhas.*terminaram em touchdown ofensivo/);expect(text).not.toMatch(/perfeit|dominan|eficien|100%/i);
      if(side==='def')expect(text).toContain('do ataque adversário');
    }
  });
  it('does not invent wording for an unknown outcome',()=>{
    const d=synthetic();d.redZone.outcomes={TOUCHDOWN:2,UNRECOGNISED:1};expect(compositionFact(d,'redzone')).toBeNull();
  });
  it.each(['NO_OPPORTUNITIES','INSUFFICIENT'] as const)('does not synthesise %s, even if partial counts exist',status=>{
    const d=synthetic();d.third.status=status;d.redZone.status=status;d.third.ratio=null;d.redZone.ratio=null;
    for(const family of ['third','redzone'] as const){expect(compositionFact(d,family)).toBeNull();
      const html=renderToStaticMarkup(<SituationalContent d={d} snapshot={snapshot} family={family}/>);
      expect(html).not.toContain('sit-fact">');expect(html).toContain('role="status"');
    }
  });
  it('keeps rule notes next to the result and EPA/UNKNOWN information in the existing details only',()=>{
    for(const family of ['third','redzone'] as const){
      const html=renderToStaticMarkup(<SituationalContent d={synthetic()} snapshot={snapshot} family={family}/>);
      const [main,details]=html.split('<details class="sit-method">');
      expect(main).not.toMatch(/EPA|UNKNOWN|sha256:/);expect(details.match(/UNKNOWN/g)).toHaveLength(4);
      expect(main.indexOf('sit-rule-note')).toBeGreaterThan(main.indexOf('data-sit-value="ratio"'));
      expect(main.indexOf('sit-rule-note')).toBeLessThan(main.indexOf('sit-fact'));
      for(const value of ['sha256:raw','sha256:ledger','sha256:test-only','1.0.0'])expect(details).toContain(value);
      expect((html.match(/<details/g)||[])).toHaveLength(1);
      if(family==='third')expect(main).toMatch(/regras do projeto.*ajoelhadas.*spikes.*anuladas.*abortadas.*oficial da NFL/);
      else expect(main).toMatch(/campanha.*20 jardas.*incluída.*ajoelhada/);
    }
  });
});
const fixture=loadRealFixture();
describe.skipIf(!fixture)('composition copy tied to the real preserved documents',()=>{
  it('reads all 384 contexts without altering a count, ratio, guarantee or state',()=>{
    if(!fixture)throw new Error('Operator fixture required');
    const s=validateSnapshot({transportVersion:'situational-response-v1',bundleId:fixture.bundleId,data:fixture.data}),before=structuredClone(s);
    for(const d of s.data.documents)for(const [family,key] of [['third','third'],['redzone','redZone']] as const){
      const text=compositionFact(d,family),m=d[key];
      expect(text===null).toBe(m.status!=='AVAILABLE');
      if(family==='third' && text){const counts=['long','medium','short'].map(k=>d.third.byDistance[k].denominator);const max=Math.max(...counts);expect(text).toContain(`${max} das ${m.denominator}`);}
      if(text && d.perspective==='def')expect(text).toContain('ataque adversário');
    }
    expect(s).toEqual(before);
    const nyj=s.data.documents.find(d=>d.id==='NYJ/off/1')!;
    const f=describedThird(compositionFact(nyj,'third')!);
    expect(f).toMatchObject({attempts:nyj.third.byDistance.long.denominator,total:nyj.third.denominator,converted:nyj.third.byDistance.long.numerator});
    expect(compositionFact(nyj,'redzone')).toMatch(new RegExp(`${nyj.redZone.outcomes.FIELD_GOAL} campanha terminou em field goal`));
  });
});
