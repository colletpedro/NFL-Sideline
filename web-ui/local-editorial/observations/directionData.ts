import type { DTO } from './model';
import { formatRatio } from './format';
export type Direction = 'A' | 'B' | 'C' | 'original';
export const directionNames = { A: 'Estádio', B: 'Transmissão', C: 'Prancheta' };
export function successParts(d: DTO) {
  if (!d.values.successRate || !d.totals) return null;
  return { positive: d.totals.successN, other: (BigInt(d.totals.epaN) - BigInt(d.totals.successN)).toString(), total: d.totals.epaN, ratio: d.values.successRate, percent: formatRatio(d.values.successRate, d.presentation.ratePercentDecimals, true) };
}
