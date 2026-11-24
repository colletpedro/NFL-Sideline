import type { SituationalDocument } from './model';

// Presentation only: counts are read from the validated document, never recomputed.
const distances = [
  ['long', '7 ou mais jardas'], ['medium', '4 a 6 jardas'], ['short', '1 a 3 jardas'],
] as const;
const endings = [
  ['FIELD_GOAL', 'field goal'], ['MISSED_FIELD_GOAL', 'field goal perdido ou bloqueado'],
  ['TURNOVER', 'turnover'], ['DOWNS', 'perda por descidas'], ['PUNT', 'punt'],
  ['END_HALF_GAME', 'fim de tempo ou de jogo'],
  ['OPPONENT_TOUCHDOWN', 'touchdown do time que defendia a campanha'], ['SAFETY', 'safety'],
] as const;
function conversions(n: number, converted: number) {
  if (n === 1) return converted === 1 ? 'ela foi convertida' : 'ela não foi convertida';
  if (converted === 0) return 'nenhuma foi convertida';
  return `${converted} dessas ${n} ${converted === 1 ? 'foi convertida' : 'foram convertidas'}`;
}
export function compositionFact(d: SituationalDocument, family: 'third' | 'redzone'): string | null {
  const defense = d.perspective === 'def';
  if (family === 'third') {
    const m = d.third;
    if (m.status !== 'AVAILABLE') return null;
    // Strict greater-than retains the explicit long/medium/short tie order.
    const band = distances.reduce((best, next) => m.byDistance[next[0]].denominator > m.byDistance[best[0]].denominator ? next : best);
    const selected = m.byDistance[band[0]], unknown = m.byDistance.unknown;
    const prefix = defense ? 'Nas tentativas do ataque adversário, ' : '';
    if (selected.denominator === 0) {
      return `${prefix}${defense ? 'a' : 'A'}${unknown.denominator === 1 ? ' única tentativa não tem' : `s ${unknown.denominator} tentativas não têm`} distância informada; ${conversions(unknown.denominator, unknown.numerator)}.`;
    }
    const subject = m.denominator === 1 ? (defense ? 'a única tentativa' : 'A única tentativa') : `${selected.denominator} das ${m.denominator} tentativas`;
    const missing = unknown.denominator > 0 ? ` Há ainda ${unknown.denominator} ${unknown.denominator === 1 ? 'tentativa' : 'tentativas'} sem distância informada (${unknown.numerator} ${unknown.numerator === 1 ? 'conversão' : 'conversões'}).` : '';
    return `${prefix}${subject} ${selected.denominator === 1 ? 'exigia' : 'exigiam'} ${band[1]}; ${conversions(selected.denominator, selected.numerator)}.${missing}`;
  }
  const m = d.redZone;
  if (m.status !== 'AVAILABLE') return null;
  // Future, unrecognised outcomes do not receive invented sports wording.
  if (Object.entries(m.outcomes).some(([key, n]) => n > 0 && key !== 'TOUCHDOWN' && !endings.some(([known]) => known === key))) return null;
  const others = endings.filter(([key]) => m.outcomes[key] > 0);
  const owner = defense ? ' do ataque adversário' : '';
  if (m.denominator === 1) return `A única campanha${owner} terminou em ${m.numerator === 1 ? 'touchdown ofensivo' : others[0]?.[1]}.`;
  if (!others.length) return m.numerator === m.denominator ? `As ${m.denominator} campanhas${owner} terminaram em touchdown ofensivo.` : null;
  const parts = others.map(([key, label]) => `${m.outcomes[key]} ${m.outcomes[key] === 1 ? 'campanha terminou' : 'campanhas terminaram'} em ${label}`);
  const list = parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(', ')} e ${parts[parts.length - 1]}`;
  const touchdowns = m.numerator > 0 ? `além ${m.numerator === 1 ? 'de' : 'dos'} ${m.numerator} ${m.numerator === 1 ? 'touchdown ofensivo' : 'touchdowns ofensivos'}, ` : '';
  const start = defense ? `Nas campanhas do ataque adversário, ${touchdowns}` : touchdowns ? touchdowns[0].toUpperCase() + touchdowns.slice(1) : 'No recorte, ';
  return `${start}${list}.`;
}
