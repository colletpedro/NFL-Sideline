// Decimal strings are the data. Number is used only for a finite SVG coordinate.
const decimal = /^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/;
export function decimalParts(value: string) {
  if (!decimal.test(value)) throw new Error('Decimal inválido.');
  const negative = value.startsWith('-');
  const unsigned = negative ? value.slice(1) : value;
  const [whole, fraction = ''] = unsigned.split('.');
  const digits = (whole + fraction).replace(/^0+/, '') || '0';
  const exponent = digits === '0' ? 0 : whole.length - 1 - (whole + fraction).search(/[1-9]/);
  return { sign: digits === '0' ? 0 : negative ? -1 : 1, digits, exponent };
}
export function compareMagnitude(a: string, b: string): number {
  const x = decimalParts(a), y = decimalParts(b);
  if (x.sign === 0) return y.sign === 0 ? 0 : -1;
  if (y.sign === 0) return 1;
  if (x.exponent !== y.exponent) return Math.sign(x.exponent - y.exponent);
  const size = Math.max(x.digits.length, y.digits.length);
  return (x.digits.padEnd(size, '0') > y.digits.padEnd(size, '0')) ? 1 :
    (x.digits.padEnd(size, '0') < y.digits.padEnd(size, '0')) ? -1 : 0;
}
export function signedDomain(values: string[]): string | null {
  if (!values.length) return null;
  let maximum = '0';
  for (const value of values) if (compareMagnitude(value, maximum) > 0) maximum = value;
  return decimalParts(maximum).sign === 0 ? '0.1' : maximum.replace(/^-/, '');
}
// Returns null when the SVG would collapse an exact nonzero value to zero.
export function coordinate(value: string, maximum: string): number | null {
  const v = decimalParts(value), m = decimalParts(maximum);
  if (v.sign === 0) return 50;
  if (m.sign === 0) return null;
  if (compareMagnitude(value, maximum) === 0) return v.sign < 0 ? 0 : 100;
  const leading = (digits: string) => Number(`${digits[0]}.${digits.slice(1, 17)}`);
  const ratio = (leading(v.digits) / leading(m.digits)) * 10 ** (v.exponent - m.exponent);
  if (!Number.isFinite(ratio) || ratio === 0) return null;
  const result = 50 + v.sign * 50 * ratio;
  return result === 50 ? null : Math.max(0, Math.min(100, result));
}
export function sign(value: string): -1 | 0 | 1 { return decimalParts(value).sign as -1 | 0 | 1; }

// Display only. The domain and coordinates still use the original decimal strings.
export function axisMagnitude(value: string): string {
  const { digits, exponent, sign: direction } = decimalParts(value);
  if (!direction) return '0';
  const leading = Number(`${digits[0]}.${digits.slice(1, 17)}`);
  if (exponent >= -3 && exponent <= 2)
    return (leading * 10 ** exponent).toPrecision(3).replace('.', ',').replace('e+', 'e');
  const rounded = leading.toPrecision(3);
  return `${rounded === '10.0' ? '1,00' : rounded.replace('.', ',')}e${exponent + (rounded === '10.0' ? 1 : 0)}`;
}
