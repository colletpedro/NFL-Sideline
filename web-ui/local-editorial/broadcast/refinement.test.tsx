import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import raw from '../observations/test-fixtures/session.json';
import { validateDTO } from '../observations/model';
import { exact, formatRatio } from '../observations/format';
import { RefinedBroadcastReading } from './RefinedBroadcastReading';
const docs = raw.entries.flatMap(e => e.documents.map(validateDTO));
const render = (d: typeof docs[number]) => renderToStaticMarkup(<RefinedBroadcastReading d={d} entry={{label:'Fixture', dataKind:'SYNTHETIC'}} controls={<button>Recorte</button>}/>);
describe('Refined broadcast reading contract', () => {
 it('preserves identity, original precision and synthetic identification for all fixtures', () => {
  for (const d of docs) {
   const html=render(d);
   expect(html).toContain(`data-observation-id="${d.observationId}"`);
   expect(html).toContain('Dados sintéticos');
   for (const ratio of Object.values(d.values)) if (ratio) expect(html).toContain(exact(ratio));
   if(d.values.epa) expect(html).toContain(formatRatio(d.values.epa,d.presentation.epaDecimals,false,true).replace(/</g,'&lt;'));
  }
 });
 it('never renders a proportion for absent source or zero denominator', () => {
  for(const d of docs.filter(d=>!d.values.successRate)) expect(render(d)).not.toContain('class="r43-track"');
  expect(render(docs.find(d=>!d.totals)!)).toContain('Ausência não é zero');
  expect(render(docs.find(d=>d.totals && d.totals.eligibleN!=='0' && !d.values.epa)!)).toContain('Denominador zero não é uma taxa de sucesso de 0%');
  expect(render(docs.find(d=>d.totals?.eligibleN==='0')!)).toContain('Amostra observada vazia');
 });
 it('does not draw a positive sliver for an exact zero rate',()=>{
  const d=docs.find(d=>d.totals?.successN==='0' && d.values.successRate)!;
  expect(render(d)).toContain('class="r43-track" aria-hidden="true"></div>');
 });
 it('keeps defensive semantics and labels the complement as zero or negative',()=>{
  const html=render(docs.find(d=>d.subject.role==='def' && d.values.successRate)!);
  expect(html).toContain('valores permitidos ao ataque adversário');
  expect(html).toContain('EPA zero ou negativo');
  expect(html).toContain('Sem comparação entre times ou previsão de vencedor');
 });
 it('preserves nonzero values too small to display as a normal decimal',()=>{
  const d=structuredClone(docs.find(d=>d.values.epa)!);
  d.values.epa={numerator:'-1',denominator:'1000000'};
  expect(render(d)).toContain('−&lt;0,001');
 });
});
