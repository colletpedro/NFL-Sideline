import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import raw from './test-fixtures/session.json';
import { validateDTO } from './model';
import { DirectionReading } from './DirectionReading';
import { successParts } from './directionData';
import { exact, formatRatio } from './format';
const docs = raw.entries.flatMap(e => e.documents.map(validateDTO));
const entry = { label: 'Fixture existente', dataKind: 'SYNTHETIC' as const };
const render = (d: typeof docs[number], direction: 'A' | 'B' | 'C') => renderToStaticMarkup(<DirectionReading d={d} entry={entry} direction={direction} controls={<button>Recorte</button>}/>);
describe('E5c-4.1 shared data across art directions', () => {
  it('retains observation identity, exact fractions and synthetic provenance in every direction', () => {
    for (const d of docs) for (const direction of ['A','B','C'] as const) {
      const html = render(d, direction);
      expect(html).toContain(`data-observation-id="${d.observationId}"`);
      expect(html).toContain('Dados sintéticos');
      for (const ratio of Object.values(d.values)) if (ratio) expect(html).toContain(exact(ratio));
      if (d.values.epa) expect(html).toContain(formatRatio(d.values.epa, d.presentation.epaDecimals, false, true).replace(/</g, '&lt;'));
      expect(html).toContain('Sem comparação entre times ou previsão de vencedor');
    }
  });
  it('computes the zero-or-negative remainder exactly, never from a rounded percentage', () => {
    const d = structuredClone(docs.find(d => d.values.successRate)!);
    d.totals!.epaN = '900719925474099312345'; d.totals!.successN = '900719925474099312344';
    d.values.successRate = { numerator: d.totals!.successN, denominator: d.totals!.epaN };
    expect(successParts(d)?.other).toBe('1');
    expect(render(d,'B')).toContain('EPA zero ou negativo');
  });
  it('distinguishes source gaps, positive volume without EPA and observed empty populations', () => {
    const gap = docs.find(d => d.totals === null)!;
    const noEpa = docs.find(d => d.totals && d.totals.eligibleN !== '0' && d.values.epa === null)!;
    const empty = docs.find(d => d.totals?.eligibleN === '0')!;
    for (const direction of ['A','B','C'] as const) {
      expect(render(gap,direction)).toContain('Ausência não é zero');
      expect(render(gap,direction)).not.toContain('class="data-track');
      expect(render(noEpa,direction)).toContain('Sem denominador EPA');
      expect(render(empty,direction)).toContain('Nenhuma jogada elegível observada');
    }
  });
  it('keeps defensive semantics and never labels the frequency complement as rushing', () => {
    const d = docs.find(d => d.subject.role === 'def' && d.values.frequency)!;
    for (const direction of ['A','B','C'] as const) {
      const html = render(d,direction);
      expect(html).toContain('Valores permitidos ao ataque adversário');
      expect(html).toContain('EPA permitido');
      expect(html).toContain('Outras jogadas classificadas');
      expect(html).toContain('Distribuição da amostra, não qualidade');
    }
  });
});
