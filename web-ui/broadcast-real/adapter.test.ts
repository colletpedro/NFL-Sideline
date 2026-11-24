import { describe, expect, it } from 'vitest';
import raw from '../local-editorial/observations/test-fixtures/session.json';
import { validateDTO, type DTO } from '../local-editorial/observations/model';
import { presentObservation, chartWidth } from './adapter';
import { allowedObservationRequest, observationPort, PREFIX } from '../build/observations';
const samples = raw.entries.flatMap(e => e.documents.map(validateDTO));
const clone = (d: DTO) => structuredClone(d);
describe('single observation presentation boundary', () => {
  it('retains every identity, ratio, game, guarantee and limitation by exact source reference', () => {
    for (const d of samples) {
      const p = presentObservation(d);
      expect(p.source).toBe(d); expect(p.guarantees).toBe(d.guarantees); expect(p.limitations).toBe(d.limitations);
      expect(p.identity).toEqual({ entryId: d.entryId, bundleId: d.bundleId, observationId: d.observationId, dtoId: d.dtoId });
      if (d.values.successRate) {
        expect(BigInt(p.complement!.numerator) + BigInt(d.values.successRate.numerator)).toBe(BigInt(d.values.successRate.denominator));
        expect(p.complement!.denominator).toBe(d.values.successRate.denominator);
      } else expect(p.complement).toBeNull();
      if (d.subject.foundation === 'general') expect(p.frequency).toBeNull();
    }
  });
  it('distinguishes absent, present empty, zero value and zero denominator', () => {
    expect(samples.some(d => presentObservation(d).sourceState === 'absent')).toBe(true);
    expect(samples.some(d => presentObservation(d).sourceState === 'empty')).toBe(true);
    const zero = samples.find(d => d.values.epa?.numerator === '0')!;
    expect(presentObservation(zero).epa).toBe('0,000');
    expect(samples.some(d => d.totals && d.totals.epaN === '0' && presentObservation(d).epa === null && presentObservation(d).volume !== null)).toBe(true);
    for (const d of samples.filter(d => d.totals === null)) {
      const p = presentObservation(d); expect(p.volume).toBeNull(); expect(p.success).toBeNull(); expect(p.width).toBeNull();
    }
  });
  it('keeps defensive sign and positive-EPA counts, without inversion or opponent inference', () => {
    const d = clone(samples.find(d => d.subject.role === 'def' && d.values.epa)!);
    d.values.epa = { numerator: '-0.00000000000000000001', denominator: '3' };
    const p = presentObservation(d);
    expect(p.epa).toBe('−<0,001'); expect(p.epaLabel).toBe('EPA médio permitido');
    expect(p.factContext).toContain('permitidos ao ataque adversário');
    expect(p.successLabel).toBe('EPA positivo permitido');
  });
  it('uses epaN rather than eligibleN when EPA is missing/nonfinite', () => {
    const d = clone(samples.find(d => d.values.epa)!);
    d.totals = { eligibleN:'100', epaN:'4', successN:'1', epaMissingN:'95', epaNonfiniteN:'1', epaSum:'2', generalEligibleN:'100', unknownFilterFlagsN:'7' };
    d.values = { epa:{ numerator:'2', denominator:'4' }, successRate:{ numerator:'1', denominator:'4' }, volume:{ numerator:'100', denominator:'1' }, frequency:null };
    const p = presentObservation(d);
    expect(p.epa).toBe('+0,500'); expect(p.success).toBe('25,0%'); expect(p.volume).toBe('100');
    expect(p.fact).toBe('1 de 4 jogadas com EPA finito tiveram valor positivo.');
    expect(p.complement).toEqual({ numerator:'3', denominator:'4' });
  });
  it('handles unsafe Number counts and tiny values exactly, with bounded geometry only', () => {
    const d = clone(samples.find(d => d.values.epa)!);
    d.values.epa = { numerator:'0.000000000000000000000001', denominator:'9' };
    d.values.successRate = { numerator:'1', denominator:'900719925474099300000' };
    const p = presentObservation(d);
    expect(p.epa).toBe('+<0,001'); expect(p.success).toBe('<0,1%'); expect(p.tiny).toBe(true);
    expect(p.complement!.numerator).toBe('900719925474099299999');
    expect(chartWidth({ numerator:'900719925474099300000', denominator:'1801439850948198600000' })).toBe('50.00%');
    for (const r of [{ numerator:'2', denominator:'1' },{ numerator:'1', denominator:'0' },{ numerator:'-1', denominator:'2' },{ numerator:'NaN', denominator:'2' }]) expect(() => chartWidth(r)).toThrow();
  });
  it('never promotes unknown coverage/completeness to percent or confidence', () => {
    for (const d of samples.filter(d => d.guarantees.coverage.state === 'UNKNOWN')) {
      const p = presentObservation(d);
      expect(p.coverageNote).toBe('Cobertura esperada desconhecida');
      expect(p.guarantees.coverage.coverageRatio).toBeNull();
    }
  });
});
describe('explicit second loopback instance', () => {
  const headers = { host:'127.0.0.1:18090', origin:'http://127.0.0.1:18090', 'x-local-observations':'1' };
  it('keeps default laboratory closed to the new instance and validates the explicit port', () => {
    expect(allowedObservationRequest('GET',PREFIX,headers)).toBe(false);
    expect(allowedObservationRequest('GET',PREFIX,headers,18090)).toBe(true);
    for (const port of [0,80,1023,65536,NaN,18090.5]) expect(() => observationPort(port)).toThrow();
    expect(observationPort()).toBe(18083);
  });
  it('preserves exact origin, host, marker, method, path and body refusals', () => {
    for (const extra of [{ host:'localhost:18090' },{ host:'127.0.0.1:18083' },{ origin:'http://127.0.0.1:18083' },{ origin:'null' },{ origin:'http://evil.invalid' },{ 'x-local-observations':'0' },{ 'content-length':'2' },{ 'transfer-encoding':'chunked' }]) expect(allowedObservationRequest('GET',PREFIX,{ ...headers,...extra },18090)).toBe(false);
    for (const method of ['POST','PUT','HEAD','DELETE','OPTIONS']) expect(allowedObservationRequest(method,PREFIX,headers,18090)).toBe(false);
    for (const path of [PREFIX+'?x=1',PREFIX+'%2e%2e',PREFIX+'../x']) expect(allowedObservationRequest('GET',path,headers,18090)).toBe(false);
  });
});
