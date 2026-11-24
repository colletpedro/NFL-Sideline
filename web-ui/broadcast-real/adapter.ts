import type { DTO, Ratio } from '../local-editorial/observations/model';
import { countText, formatRatio } from '../local-editorial/observations/format';
import { foundationLabel, readingPeriod, proportionWidth } from '../local-editorial/observations/presentation';

export function chartWidth(r: Ratio) {
  if (!/^(0|[1-9][0-9]*)$/.test(r.numerator) || !/^[1-9][0-9]*$/.test(r.denominator) || BigInt(r.numerator) > BigInt(r.denominator)) throw new Error('Proporção fora da faixa.');
  return proportionWidth(r);
}
// Receives one validated DTO. Exact source context and reasons stay attached;
// no lookups, population reconstruction, float arithmetic or editorial thresholds.
export function presentObservation(d: DTO) {
  const t = d.totals, defensive = d.subject.role === 'def';
  const rate = d.values.successRate;
  const complement: Ratio | null = rate ? { numerator: (BigInt(rate.denominator) - BigInt(rate.numerator)).toString(), denominator: rate.denominator } : null;
  const format = (r: Ratio | null, percent = false) => r ? formatRatio(r, percent ? d.presentation.ratePercentDecimals : d.presentation.epaDecimals, percent, !percent) : null;
  const modelNote = d.guarantees.compatibility.epaModel.state === 'UNKNOWN' ? 'Modelo EPA não identificado' : `Modelo EPA: ${d.guarantees.compatibility.epaModel.id}`;
  const sourceState = t === null ? 'absent' : t.eligibleN === '0' ? 'empty' : 'available';
  const fact = t === null ? 'Sem fonte para este recorte.' : rate
    ? `${countText(rate.numerator)} de ${countText(rate.denominator)} jogadas com EPA finito tiveram valor positivo.`
    : t.eligibleN === '0' ? 'Fonte presente, sem jogadas elegíveis.' : `${countText(t.eligibleN)} jogadas elegíveis; nenhuma com EPA finito.`;
  return {
    source: d, identity: { entryId: d.entryId, bundleId: d.bundleId, observationId: d.observationId, dtoId: d.dtoId },
    guarantees: d.guarantees, limitations: d.limitations, sourceState, defensive,
    role: defensive ? 'Defesa' : 'Ataque', foundation: foundationLabel(d.subject), period: readingPeriod(d),
    fact, factContext: t === null ? 'Período solicitado; fonte de jogadas ausente.' : defensive ? 'Na amostra arquivada, valores permitidos ao ataque adversário.' : 'Na amostra arquivada do ataque.',
    volume: t ? countText(t.eligibleN) : null, epa: format(d.values.epa), success: format(rate, true),
    frequency: format(d.values.frequency, true), complement,
    complementPercent: format(complement, true),
    width: rate ? chartWidth(rate) : null,
    tiny: !!rate && rate.numerator !== '0' && chartWidth(rate) === '0.00%',
    modelNote, epaLabel: defensive ? 'EPA médio permitido' : 'EPA médio',
    successLabel: defensive ? 'EPA positivo permitido' : 'Jogadas com EPA positivo',
    completenessNote: d.guarantees.completeness.state === 'COMPLETE' ? 'Completude demonstrada' : d.guarantees.completeness.state === 'PARTIAL' ? 'Fonte parcial' : 'Completude não confirmada',
    coverageNote: d.guarantees.coverage.expectedCount === null ? 'Cobertura esperada desconhecida' : `${d.observed.includedGameIds.length} jogos com fonte de ${countText(d.guarantees.coverage.expectedCount)} esperados`,
  };
}
export type Reading = ReturnType<typeof presentObservation>;
