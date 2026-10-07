import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { axisMagnitude, coordinate, signedDomain } from './decimal';
import { validateDocument, validateVisualEnvelope } from './validate';
import { VisualAnalysis } from './VisualAnalysis';
import type { VisualAnalysisDocument } from './model';

const valid = import.meta.glob('../../../../contracts/visual-analysis/v1/fixtures/valid/*.json', { eager: true, import: 'default' });
const invalid = import.meta.glob('../../../../contracts/visual-analysis/v1/fixtures/invalid/*.json', { eager: true, import: 'default' });
const fixture = (name: string) => valid[Object.keys(valid).find(path => path.endsWith(`/${name}.json`))!];

const real = import.meta.glob('../../../../editorial/evaluations/2026-10-06-visual-e2/documents/*.json', { eager: true, import: 'default' });

describe('E2 documents consumed by E3', () => {
  it('has the complete backend evaluation batch', () => expect(Object.keys(real)).toHaveLength(17));
  it.each(Object.entries(real))('validates and renders %s without fixture provenance', (_path, value) => {
    const doc = validateDocument(value, 'real');
    const html = renderToStaticMarkup(<VisualAnalysis document={doc}/>);
    expect(html).toContain('RESULTADO LOCAL · NÃO PUBLICADO');
    expect(html).not.toContain('FIXTURE SINTÉTICA');
    expect((html.match(/class="visual-card-head"/g) ?? []).length).toBe(6);
  });
});

describe('frozen visual contract', () => {
  it.each(Object.keys(valid).map(path => path.split('/').pop()!))('accepts and renders %s as synthetic', file => {
    const doc = validateDocument(valid[Object.keys(valid).find(path => path.endsWith(`/${file}`))!], 'fixture');
    const html = renderToStaticMarkup(<VisualAnalysis document={doc}/>);
    expect(html).toContain('FIXTURE SINTÉTICA');
    expect((html.match(/class="visual-card-head"/g) ?? []).length).toBe(6);
    expect(html).toContain('Limites do documento');
    expect(html).toContain('Tabela de evidências');
  });
  it.each(Object.keys(invalid).map(path => path.split('/').pop()!))('refuses %s', file => {
    expect(() => validateDocument(invalid[Object.keys(invalid).find(path => path.endsWith(`/${file}`))!], 'fixture')).toThrow();
  });
  it('keeps absence, unilateral evidence, zero, historical labels and equivalent highlights', () => {
    const partial = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('partial'), 'fixture')}/>);
    expect(partial).toContain('Sem observações da defesa');
    expect(partial).toContain('+0,100');
    expect(partial).not.toContain('0 jogadas observadas');
    const missing = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('missing'), 'fixture')}/>);
    expect(missing).toContain('Ausência não é zero');
    const zero = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('zero'), 'fixture')}/>);
    expect(zero).toContain('0,000');
    const historical = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('historical'), 'fixture')}/>);
    expect(historical).toContain('Referência histórica');
    const gap = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('coverage-gap'), 'fixture')}/>);
    expect(gap).toContain('Sem observação em S2; motivo não identificado.');
    const tie = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('tie'), 'fixture')}/>);
    expect(tie).toContain('Destaques equivalentes');
    expect((tie.match(/visual-card-highlight/g) ?? []).length).toBe(2);
  });
  it('rejects fixture provenance and divergent attempt/document identities on the live route', () => {
    const doc = structuredClone(fixture('complete-matchup')) as VisualAnalysisDocument;
    expect(() => validateDocument(doc, 'real')).toThrow('origem');
    doc.source = { kind: 'VALIDATED_LOCAL_RESULT', resultIdentity: 'a'.repeat(64), contextSha256: 'b'.repeat(64), claimsContractVersion: 5, selectorVersion: '2.0.0' };
    const attemptId = '12345678-1234-1234-1234-123456789abc';
    const expected = { ...doc.game, attemptId, resultIdentity: 'a'.repeat(64) };
    const envelope = { mode: 'LOCAL_RULES_DEVELOPMENT', publicationApproved: false, gameId: doc.game.gameId,
      attemptId, resultIdentity: 'a'.repeat(64), visualIdentity: 'c'.repeat(64), document: doc };
    expect(validateVisualEnvelope(envelope, expected).document).toEqual(doc);
    expect(() => validateVisualEnvelope({ ...envelope, attemptId: 'bad' }, expected)).toThrow();
    expect(() => validateVisualEnvelope({ ...envelope, document: { ...doc, game: { ...doc.game, homeTeam: 'OTHER' } } }, expected)).toThrow();
    expect(() => validateVisualEnvelope({ ...envelope, document: { ...doc, source: { ...doc.source, resultIdentity: 'd'.repeat(64) } } }, expected)).toThrow();
    expect(() => validateVisualEnvelope({ ...envelope, visualIdentity: 'bad' }, expected)).toThrow();
    expect(() => validateVisualEnvelope({ ...envelope, extra: true }, expected)).toThrow();
  });
});

describe('signed shared geometry', () => {
  it('shortens axis labels without changing the exact domain or collapsing tiny values', () => {
    const exact = '0.7068532854290454';
    expect(axisMagnitude(exact)).toBe('0,707');
    expect(signedDomain([exact])).toBe(exact);
    expect(coordinate(exact, exact)).toBe(100);
    expect(axisMagnitude(`0.${'0'.repeat(330)}1`)).toBe('1,00e-331');
    expect(axisMagnitude('99999')).toBe('1,00e5');
  });
  it('places negative, zero and positive on distinct sides', () => {
    expect(coordinate('-0.4', '0.4')).toBe(0);
    expect(coordinate('0', '0.4')).toBe(50);
    expect(coordinate('0.4', '0.4')).toBe(100);
    expect(coordinate('-0.1', '0.4')).toBeLessThan(50);
    expect(coordinate('0.1', '0.4')).toBeGreaterThan(50);
  });
  it('includes all extrema from both teams and the general panorama', () => {
    const doc = validateDocument(fixture('outlier'), 'fixture');
    const max = signedDomain(doc.evidence.map(row => row.value));
    expect(max).toBe('1.06');
    expect(doc.evidence.every(row => { const x = coordinate(row.value, max!); return x === null || x >= 0 && x <= 100; })).toBe(true);
  });
  it('uses a drawing-only scale for all zero, and refuses false zero from underflow', () => {
    expect(signedDomain(['0', '0.000'])).toBe('0.1');
    expect(signedDomain([])).toBeNull();
    expect(coordinate(`0.${'0'.repeat(330)}1`, '1')).toBeNull();
    expect(coordinate('0', '0.1')).toBe(50);
  });
  it('preserves tiny signs without reclassification or rounding', () => {
    expect(coordinate('0.00001', '0.1')).toBeGreaterThan(50);
    expect(coordinate('-0.00001', '0.1')).toBeLessThan(50);
    const html = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('negative-tiny-sign'), 'fixture')}/>);
    expect(html).toContain('-0,0005 &lt; EPA &lt; 0');
  });
});

describe('E4 presentation preserves interpretation and geometry', () => {
  it('puts both roles, foundation and observed period in the quick reading, with the limit before points', () => {
    const html = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('opposition'), 'fixture')}/>);
    const quick = html.slice(html.indexOf('visual-highlights'), html.indexOf('visual-legend'));
    expect(quick).toContain('AAA ataque × BBB defesa · Passe');
    expect(quick).toContain('Ataque e defesa: Temporada atual · 2026 · semanas 1, 2, 3');
    expect(quick).toContain('Esta análise não estima vencedor');
    expect(quick).toContain('a quantidade de cartões não é um placar');
    const card = html.slice(html.indexOf('<article'), html.indexOf('</article>'));
    expect(card.indexOf('Limitação principal')).toBeLessThan(card.indexOf('visual-plot'));
    expect(card).toContain('tabindex="0" role="region" aria-labelledby=');
    expect(card).toContain('scope="col"');
    expect(card).toContain('scope="row"');
  });
  it('keeps distinct observed windows and historical references in the quick reading', () => {
    const doc = validateDocument(fixture('uneven-weeks'), 'fixture');
    const html = renderToStaticMarkup(<VisualAnalysis document={doc}/>);
    const quick = html.slice(html.indexOf('visual-highlights'), html.indexOf('visual-legend'));
    const encounter = doc.encounters.find(e => e.id === doc.findings[0].encounterId)!;
    for (const id of [encounter.attackSeriesId, encounter.defenseSeriesId]) {
      const series = doc.series.find(s => s.id === id)!;
      const rows = series.evidenceIds.map(id => doc.evidence.find(e => e.id === id)!);
      expect(quick).toContain(`semanas ${rows.map(e => e.week).join(', ')}`);
    }
    const historical = renderToStaticMarkup(<VisualAnalysis document={validateDocument(fixture('historical'), 'fixture')}/>);
    expect(historical.slice(historical.indexOf('visual-highlights'), historical.indexOf('visual-legend'))).toContain('Referência histórica');
  });
  it('includes a hidden general extreme in every rendered series scale', () => {
    const raw = structuredClone(fixture('general-represented')) as VisualAnalysisDocument;
    const general = raw.evidence.find(e => e.metric === 'OFF_EPA_PLAY' && Number(e.value) > 0)!;
    general.value = '3.0000001'; general.displayValue = '+3,000';
    const doc = validateDocument(raw, 'fixture');
    const html = renderToStaticMarkup(<VisualAnalysis document={doc}/>);
    expect(html).toContain('≈ +3,00');
    expect(html).not.toContain('≈ +0,400');
    const pass = doc.evidence.find(e => e.metric === 'OFF_EPA_PASS')!;
    expect(html).toContain(`left:${coordinate(pass.value, general.value)}%`);
    expect(html).toContain('<details class="visual-general">');
  });
  it.each(['opposition', 'zero', 'tiny-sign', 'negative-tiny-sign', 'partial', 'outlier'])('renders the original coordinates and exact evidence for %s', name => {
    const doc = validateDocument(fixture(name), 'fixture');
    const original = structuredClone(doc);
    const html = renderToStaticMarkup(<VisualAnalysis document={doc}/>);
    const max = signedDomain(doc.evidence.map(e => e.value))!;
    for (const row of doc.evidence) {
      const position = coordinate(row.value, max);
      if (position !== null) expect(html).toContain(`left:${position}%`);
      expect(html).toContain(`<code>${row.value}</code>`);
    }
    expect(doc).toEqual(original);
  });
});
