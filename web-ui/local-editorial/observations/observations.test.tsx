import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import raw from './test-fixtures/session.json';
import { allowedObservationRequest, freezeSnapshot, PREFIX } from '../../build/observations';
import { validateDTO, validateCatalog } from './model';
import type { DTO } from './model';
import { observationDocument } from './client';
import { countText, formatRatio } from './format';
import { prepareSnapshot } from '../../build/observations-process.mjs';
import { ObservationReading } from './Observations';
import { chooseAvailable } from './selection';

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const sample = () => clone(raw.entries[0].documents.find(d => d.values.epa !== null)!) as DTO;
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
describe('observation restricted transport', () => {
  it('refuses configuration in the served root and never starts Python for incomplete configuration', async () => {
    vi.stubEnv('NFL_OBSERVATION_CONFIG', undefined); vi.stubEnv('NFL_OBSERVATION_PYTHON', undefined);
    await expect(prepareSnapshot()).resolves.toEqual({ errorCode: 'OBSERVATIONS_NOT_CONFIGURED' });
    vi.stubEnv('NFL_OBSERVATION_CONFIG', decodeURIComponent(new URL('../../package.json', import.meta.url).pathname));
    vi.stubEnv('NFL_OBSERVATION_PYTHON', '/unavailable/python');
    await expect(prepareSnapshot()).resolves.toEqual({ errorCode: 'OBSERVATION_CONFIGURATION_INVALID' });
  });
  it('validates operational synthetic DTOs and refuses missing scopes/limits/IDs/unknown versions', () => {
    for (const entry of raw.entries) for (const d of entry.documents) expect(validateDTO(d).observationId).toBe(d.observationId);
    for (const change of [
      (d: DTO) => { delete d.fieldScopes.unknownFilterFlagsN; },
      (d: DTO) => { d.limitations = d.limitations.filter(x => x.code !== 'UNKNOWN_FILTER_FLAGS_GAME_SCOPE'); },
      (d: DTO) => { d.guarantees.temporal.state = 'KNOWN_AT_CUTOFF'; },
      (d: DTO) => { d.guarantees.compatibility.state = 'CONFLICT'; },
      (d: DTO) => { d.observationId = 'bad'; },
      (d: DTO) => { d.observed.actualWeeks = []; },
      (d: DTO) => { d.limitations = d.limitations.filter(x => x.code !== 'AVAILABLE_AT_UNKNOWN'); },
      (d: DTO) => { d.dtoVersion = 'unknown' as DTO['dtoVersion']; },
      (d: DTO) => { d.values.epa!.denominator = '0'; },
    ]) { const d = sample(); change(d); expect(() => validateDTO(d)).toThrow(); }
    expect(() => validateDTO({ ...sample(), lineage: {} })).toThrow();
  });
  it('freezes response bytes independently of later input mutation', () => {
    const data = clone(raw); const frozen = freezeSnapshot(data);
    const before = [...frozen.documents.values()];
    data.entries[0].documents[0].totals!.epaSum = '999';
    expect([...frozen.documents.values()]).toEqual(before);
    const catalog = validateCatalog(JSON.parse(frozen.catalog));
    expect(catalog.bundles).toHaveLength(5);
    const bytes = frozen.catalog + before.join('');
    for (const forbidden of ['bytes_base64', 'archive_root', 'receipt_json', 'lineage.json', '/private/', '/Users/', 'context_json']) expect(bytes).not.toContain(forbidden);
  });
  it('allows only exact loopback GETs and rejects paths, origins, bodies and encoding', () => {
    const h = { host: '127.0.0.1:18083', origin: 'http://127.0.0.1:18083', 'x-local-observations': '1' };
    expect(allowedObservationRequest('GET', PREFIX, h)).toBe(true);
    expect(allowedObservationRequest('GET', `${PREFIX}synthetic/${'a'.repeat(64)}`, h)).toBe(true);
    for (const method of ['HEAD', 'POST', 'PUT', 'OPTIONS', 'DELETE']) expect(allowedObservationRequest(method, PREFIX, h)).toBe(false);
    for (const path of [PREFIX + '../x', PREFIX + '%2e%2e', PREFIX + '?path=/tmp', PREFIX + 'snapshot.json', PREFIX + 'synthetic/../../secret']) expect(allowedObservationRequest('GET', path, h)).toBe(false);
    for (const bad of [{ host: 'localhost:18083' }, { origin: 'http://evil.invalid' }, { 'content-length': '1' }, { 'transfer-encoding': 'chunked' }, { 'x-local-observations': '0' }]) expect(allowedObservationRequest('GET', PREFIX, { ...h, ...bad })).toBe(false);
  });
  it('matches session, entry, bundle, DTO and observation identities before returning data', async () => {
    const f = freezeSnapshot(raw); const c = validateCatalog(JSON.parse(f.catalog)); const entry = c.bundles[0]; const summary = entry.observations[0];
    const good = JSON.parse(f.documents.get(`${entry.entryId}/${summary.observationId.slice(7)}`)!);
    for (const mutate of [
      (e: typeof good) => { e.sessionId = `sha256:${'f'.repeat(64)}`; },
      (e: typeof good) => { e.document.entryId = 'other'; },
      (e: typeof good) => { e.document.observationId = `sha256:${'f'.repeat(64)}`; },
      (e: typeof good) => { e.document.bundleId = `sha256:${'f'.repeat(64)}`; },
      (e: typeof good) => { e.document.dtoId = `sha256:${'f'.repeat(64)}`; },
    ]) {
      const bad = clone(good); mutate(bad);
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => bad }));
      await expect(observationDocument(c, entry, summary)).rejects.toThrow();
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => good }));
    await expect(observationDocument(c, entry, summary)).resolves.toMatchObject({ observationId: summary.observationId });
  });
});
describe('exact single observation reading', () => {
  it('keeps period when available and permits teams/roles with only a different foundation', () => {
    const a = sample(); const b = { ...a, subject: { team: 'ZZZ', role: 'off' as const, foundation: 'general' as const } };
    const c = { ...a, subject: { team: 'ZZZ', role: 'def' as const, foundation: 'classified_rush' as const } };
    expect(chooseAvailable([c, b], a)).toBe(c);
    expect(chooseAvailable([b], a)).toBe(b);
    expect(chooseAvailable([], a)).toBeUndefined();
  });

  it('keeps rationals exact, HALF_UP, signs and tiny nonzero ranges without Number conversion', () => {
    expect(formatRatio({ numerator: '-0.0000000000000000000000000000001', denominator: '2' }, 3, false, true)).toBe('−<0,001');
    expect(formatRatio({ numerator: '1', denominator: '3' }, 1, true)).toBe('33,3%');
    expect(formatRatio({ numerator: '0', denominator: '2' }, 3, false, true)).toBe('0,000');
    expect(formatRatio({ numerator: '-0.0005', denominator: '1' }, 3, false, true)).toBe('−0,001');
    expect(formatRatio({ numerator: '0.000001', denominator: '1' }, 1, true)).toBe('<0,1%');
    expect(formatRatio({ numerator: '900719925474099300000', denominator: '1' }, 0)).toBe('900719925474099300000');
    expect(countText('900719925474099300000')).toBe('900.719.925.474.099.300.000');
  });
  it('shows defensive meaning, periods, unknowns, zero, denominator zero, absent source and complete empty distinctly', () => {
    const texts = raw.entries.flatMap(e => e.documents.map(d => renderToStaticMarkup(<ObservationReading d={validateDTO(d)} entry={{ label: e.label, dataKind: 'SYNTHETIC' }}/>)));
    expect(texts.some(t => t.includes('EPA permitido'))).toBe(true);
    for (const phrase of ['Desconhecido', 'Sem denominador', 'zero conhecido', 'Fonte ausente', 'Observação vazia sustentada', 'Referência histórica', 'modelo não identificado', 'Cobertura esperada desconhecida', 'contexto do jogo inteiro']) expect(texts.some(t => t.includes(phrase))).toBe(true);
    expect(texts.every(t => t.includes('Conhecimento no corte não demonstrado'))).toBe(true);
    expect(texts.every(t => t.match(/aria-label="Observação selecionada"/g)?.length === 1)).toBe(true);
  });
});
