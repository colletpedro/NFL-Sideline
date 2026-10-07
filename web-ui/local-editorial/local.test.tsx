import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { allowedLocalRequest } from '../build/local-editorial';
import { generate, history, retrieve, retrieveVisual, validateResult, VisualUnavailableError } from './client';
import type { Result } from './client';
import { Analysis } from './App';

const attempt = '12345678-1234-1234-1234-123456789abc';
const result: Result = { mode: 'LOCAL_RULES_DEVELOPMENT', publicationApproved: false,
  gameId: 'BAL_DAL', attemptId: attempt, resultIdentity: 'a'.repeat(64),
  analysis: { fator_chave: '<script>alert(1)</script>', vantagem_tatica: 'Passe\n+0,120 EPA', alerta_vermelho: 'Amostra curta', veredito: 'Inconclusivo' } };
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
describe('local browser boundary', () => {
  const allow = (method: string, path: string, origin: string | undefined = 'http://127.0.0.1:18083',
    host = '127.0.0.1:18083', marker: string | undefined = '1', length?: string, transfer?: string) =>
    allowedLocalRequest(method, `/__editorial/${path}`, host, origin, marker, length, transfer);
  it('allows only the intended methods and paths with a same-origin POST', () => {
    expect(allow('POST', 'BAL_DAL')).toBe(true);
    expect(allow('GET', '')).toBe(true);
    expect(allow('GET', 'BAL_DAL/attempts')).toBe(true);
    expect(allow('GET', `BAL_DAL/${attempt}`)).toBe(true);
    expect(allow('GET', `BAL_DAL/${attempt}/insights`)).toBe(true);
    expect(allow('POST', `BAL_DAL/${attempt}/insights`)).toBe(false);
    expect(allow('GET', `BAL_DAL/${attempt}/insights/extra`)).toBe(false);
    expect(allow('GET', `BAL_DAL/${attempt}/insights?x=1`)).toBe(false);
    expect(allowedLocalRequest('POST', '/__editorial/BAL_DAL', '127.0.0.1:18083', undefined, '1', undefined, undefined)).toBe(false);
    for (const path of ['../private', 'BAL_DAL?x=1', '%2e%2e', 'BAL_DAL/attempts', '']) expect(allow('POST', path)).toBe(false);
    expect(allow('OPTIONS', '')).toBe(false);
    expect(allow('POST', 'BAL_DAL', 'https://evil.example')).toBe(false);
    expect(allow('POST', 'BAL_DAL', 'null')).toBe(false);
    expect(allow('POST', 'BAL_DAL', undefined, 'evil.example:18083')).toBe(false);
    expect(allow('POST', 'BAL_DAL', undefined, undefined, '')).toBe(false);
    expect(allow('POST', 'BAL_DAL', undefined, undefined, undefined, '8')).toBe(false);
    expect(allow('POST', 'BAL_DAL', undefined, undefined, undefined, undefined, 'chunked')).toBe(false);
  });
  it('refuses a production/foreign-game envelope and renders text without executing markup', () => {
    expect(validateResult(result, 'BAL_DAL')).toEqual(result);
    expect(() => validateResult({ ...result, publicationApproved: true }, 'BAL_DAL')).toThrow();
    expect(() => validateResult(result, 'SEA_WAS')).toThrow();
    expect(() => validateResult(result, 'BAL_DAL', 'other')).toThrow();
    const html = renderToStaticMarkup(<Analysis result={result}/>);
    expect(html).toContain('&lt;script&gt;');
    expect(html).not.toContain('<script>');
    expect(html).toContain('Passe\n+0,120 EPA');
  });
  it('only generates on an explicit POST and retrieves by identity', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => result });
    vi.stubGlobal('fetch', fetch);
    await generate('BAL_DAL');
    expect(fetch).toHaveBeenCalledWith('/__editorial/BAL_DAL', expect.objectContaining({ method: 'POST', headers: { 'X-Local-Editorial': '1' } }));
    await retrieve('BAL_DAL', attempt);
    expect(fetch).toHaveBeenLastCalledWith(`/__editorial/BAL_DAL/${attempt}`, expect.objectContaining({ method: 'GET' }));
    await expect(retrieve('../outside', attempt)).rejects.toThrow();
    await expect(retrieve('BAL_DAL', '../outside')).rejects.toThrow();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it('reports unavailable/corrupt results and does not retry POST on lost responses', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: false, status: 409 });
    vi.stubGlobal('fetch', fetch);
    await expect(retrieve('BAL_DAL', attempt)).rejects.toThrow('incompleta');
    fetch.mockRejectedValue(new TypeError('Network error'));
    await expect(generate('BAL_DAL')).rejects.toThrow('pode ter sido salva');
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it('keeps a legacy v3 attempt textual when insights are unavailable', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ error: 'VISUAL_DOCUMENT_NOT_AVAILABLE' }) });
    vi.stubGlobal('fetch', fetch);
    const context = { gameId: 'BAL_DAL', homeTeam: 'DAL', awayTeam: 'BAL', season: 2026, week: 4, phase: 'REG', gameday: '', asOfDate: '', sourceSha256: 'b'.repeat(64) };
    await expect(retrieveVisual(context, result)).rejects.toBeInstanceOf(VisualUnavailableError);
    expect(fetch).toHaveBeenCalledWith(`/__editorial/BAL_DAL/${attempt}/insights`, expect.objectContaining({ method: 'GET' }));
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('rejects malformed history before displaying it', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ attempts: [{ attemptId: '../' }], unavailableInStore: 0 }) }));
    await expect(history('BAL_DAL')).rejects.toThrow('incompatível');
  });
});
