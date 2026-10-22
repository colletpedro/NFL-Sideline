import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import raw from '../local-editorial/observations/test-fixtures/session.json';
import { validateDTO, type Entry } from '../local-editorial/observations/model';
import { Reading } from '../broadcast-real/Reading';
const samples = raw.entries.flatMap(e => e.documents.map(value => ({ d: validateDTO(value), entry: { ...e, observations: [] } as Entry })));
const numeric = (html: string) => [...html.matchAll(/data-value="([^"]+)">([^<]+)/g)].map(m => [m[1], m[2]]);
describe('guided presentation retains the reading boundary', () => {
  it('retains all displayed numbers, chart descriptions and original ratios across source states', () => {
    for (const sample of samples) {
      const before = renderToStaticMarkup(<Reading {...sample}/>), guided = renderToStaticMarkup(<Reading {...sample} guided/>);
      expect(numeric(guided)).toEqual(numeric(before));
      expect([...guided.matchAll(/role="img" aria-label="([^"]+)"/g)].map(m => m[1])).toEqual([...before.matchAll(/role="img" aria-label="([^"]+)"/g)].map(m => m[1]));
      expect(guided.slice(guided.indexOf('id="real-details"'))).toBe(before.slice(before.indexOf('id="real-details"')));
    }
  });
  it('keeps essential guarantees visible, plus absent and empty explanations', () => {
    for (const sample of samples) {
      const text = renderToStaticMarkup(<Reading {...sample} guided/>).split('id="real-details"')[0];
      if (sample.d.guarantees.completeness.state === 'UNKNOWN') expect(text).toContain('Completude não confirmada');
      expect(text).toContain('Conhecimento anterior ao jogo não demonstrado');
      if (sample.d.guarantees.compatibility.epaModel.state === 'UNKNOWN') expect(text).toContain('Modelo EPA não identificado');
      if (sample.d.totals === null) { expect(text).toContain('Ausência de fonte não é zero'); expect(numeric(text)).toEqual([]); }
      if (sample.d.totals?.eligibleN === '0') { expect(text).toContain('Fonte presente, sem jogadas elegíveis'); expect(text).toContain('Denominador EPA zero'); }
    }
  });
});
