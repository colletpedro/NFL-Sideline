import type { Subject, Summary, Ratio } from './model';
export const foundationLabel = (s: Subject) => s.foundation === 'general' ? 'Passe + corrida' : s.foundation === 'classified_pass' ? (s.role === 'def' ? 'Contra passe' : 'Passe') : (s.role === 'def' ? 'Contra corrida' : 'Corrida');
export const readingPeriod = (s: Summary) => `${s.request.season} · ${s.request.phase === 'POST' ? 'Pós-temporada' : 'Temporada regular'} · ${s.request.period.weeks.length === 1 ? 'Semana' : 'Semanas'} ${s.request.period.weeks.join(', ')}${s.request.origin === 'HISTORICAL_REFERENCE' ? ' · Referência histórica' : ''}`;

// Geometry only: hundredths of a percent, computed with integer arithmetic.
// The exact numerator/denominator remain visible; tiny values are never relabelled zero.
export function proportionWidth(r: Ratio): string {
  const units = BigInt(r.numerator) * 10000n / BigInt(r.denominator);
  return `${units / 100n}.${(units % 100n).toString().padStart(2, '0')}%`;
}
