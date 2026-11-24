import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import raw from '../local-editorial/observations/test-fixtures/session.json';
import { validateDTO, type Entry } from '../local-editorial/observations/model';
import { Reading } from './Reading';

// Only the existing, explicitly synthetic session is used for states absent from
// the real archive. These fixtures are never exposed by the real entry/catalog.
const samples=raw.entries.flatMap(e=>e.documents.map(value=>({d:validateDTO(value),entry:{...e,observations:[]} as Entry})));
const visibleText=(sample:typeof samples[number])=>renderToStaticMarkup(<Reading {...sample}/>).split('id="real-details"')[0];
describe('single archive interpretation',()=>{
 it('keeps essential unknowns visible before disclosure on every source state',()=>{
  for(const sample of samples.filter(s=>s.d.guarantees.completeness.state==='UNKNOWN')){
   const text=visibleText(sample);
   expect(text).toContain('Completude não confirmada');
   expect(text).toContain('Conhecimento anterior ao jogo não demonstrado');
   if(sample.d.guarantees.compatibility.epaModel.state==='UNKNOWN')expect(text).toContain('Modelo EPA não identificado');
  }
 });
 it('distinguishes a source gap from observed zero and refuses a manufactured zero bar',()=>{
  const missing=samples.find(s=>s.d.totals===null)!;
  expect(visibleText(missing)).toContain('Ausência de fonte não é zero');
  expect(visibleText(missing)).not.toContain('Na amostra arquivada');
  expect(visibleText(missing)).not.toContain('Amostra do arquivo');
  expect(visibleText(missing)).not.toContain('data-value');
  expect(visibleText(missing)).not.toContain('real-track');
  const zero=samples.find(s=>s.d.values.epa?.numerator==='0')!;
  expect(visibleText(zero)).toContain('0,000');
 });
 it('describes present empty and complete empty without calling undefined efficiency zero',()=>{
  for(const sample of samples.filter(s=>s.d.totals?.eligibleN==='0')){
   const text=visibleText(sample);
   expect(text).toContain('Fonte presente, sem jogadas elegíveis');
   expect(text).toContain('Denominador EPA zero');
   expect(text).toContain('não significa 0%');
   expect(text).toContain(sample.d.guarantees.completeness.state==='COMPLETE'?'População declarada completa sem jogadas elegíveis':'Zero jogadas elegíveis nos bytes observados');
  }
 });
 it('describes the defensive positive-EPA complement using its original counts',()=>{
  const sample=samples.find(s=>s.d.subject.role==='def'&&s.d.values.successRate)!;
  const d=sample.d,text=visibleText(sample);
  expect(text).toContain('EPA médio permitido');
  expect(text).toContain('valores permitidos ao ataque adversário');
  expect(text).toContain('com EPA zero ou negativo');
  const complement=(BigInt(d.totals!.epaN)-BigInt(d.totals!.successN)).toString();
  expect(text).toContain(`${complement} / ${d.totals!.epaN}`);
 });
});
