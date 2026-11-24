import type { Ratio } from './model';
// Exact rational HALF_UP; Number/SVG helpers are deliberately unsuitable here.
export function formatRatio(value: Ratio, places: number, percent = false, signed = false): string {
  const negative = value.numerator.startsWith('-');
  const [whole, fractional = ''] = value.numerator.replace('-', '').split('.');
  const n = BigInt(whole + fractional) * (percent ? 100n : 1n);
  const d = BigInt(value.denominator) * 10n ** BigInt(fractional.length);
  if (d <= 0n || !Number.isInteger(places) || places < 0 || places > 12) throw new Error('Fração inválida.');
  const scale = 10n ** BigInt(places);
  const rounded = (2n * n * scale + d) / (2n * d);
  const prefix = n === 0n ? '' : negative ? '−' : signed ? '+' : '';
  if (rounded === 0n && n !== 0n) {
    const bound = places === 0 ? '1' : `0,${'0'.repeat(places - 1)}1`;
    return `${prefix}<${bound}${percent ? '%' : ''}`;
  }
  const wholePart = rounded / scale;
  const rest = places ? `,${(rounded % scale).toString().padStart(places, '0')}` : '';
  return `${prefix}${wholePart}${rest}${percent ? '%' : ''}`;
}
export const exact = (v: Ratio) => `${v.numerator} / ${v.denominator}`;
export const countText = (v: string) => v.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
