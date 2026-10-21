import type { ReactNode } from 'react';
import type { DTO, Entry, Ratio } from './model';
import { countText, formatRatio } from './format';
import { foundationLabel, proportionWidth, readingPeriod } from './presentation';
import { ObservationInspection } from './ObservationReading';

import { successParts, type Direction } from './directionData';
const teams: Record<string, { city: string; name: string }> = {
  BAL: { city: 'Baltimore', name: 'Ravens' }, DAL: { city: 'Dallas', name: 'Cowboys' }, NE: { city: 'New England', name: 'Patriots' },
};
function FractionBar({ ratio, className = '' }: { ratio: Ratio; className?: string }) {
  const width = proportionWidth(ratio);
  if (ratio.numerator !== '0' && width === '0.00%') return <p className="chart-tiny">Proporção positiva menor que 0,01%; sem área mínima inventada.</p>;
  return <div className={`data-track ${className}`} aria-hidden="true"><span style={{ width }}/></div>;
}
function SuccessGraphic({ d, broadcast = false }: { d: DTO; broadcast?: boolean }) {
  const parts = successParts(d);
  if (!parts) return <div className="chart-unavailable"><strong>Sem base para a taxa</strong><p>Nenhuma jogada com EPA disponível. Denominador zero não é sucesso zero.</p></div>;
  const { positive, other, total, ratio, percent } = parts;
  return <figure className={`success-graphic ${broadcast ? 'two-lanes' : 'split-area'}`} aria-label={`${countText(positive)} de ${countText(total)} jogadas com EPA positivo (${percent}); ${countText(other)} com EPA zero ou negativo.`}>
    <figcaption><span>{d.subject.role === 'def' ? 'Sucesso permitido ao adversário' : 'Jogadas com EPA positivo'}</span><strong>{percent}</strong></figcaption>
    {broadcast ? <div className="broadcast-lanes">
      <div><span>EPA positivo</span><strong>{countText(positive)}</strong><FractionBar ratio={ratio}/></div>
      <div><span>EPA zero ou negativo</span><strong>{countText(other)}</strong><FractionBar ratio={{ numerator: other, denominator: total }} className="other-track"/></div>
      <p className="chart-axis">0 <span>Escala: {countText(total)} jogadas com EPA</span> {countText(total)}</p>
    </div> : <><FractionBar ratio={ratio} className="area-track"/><div className="composition-labels"><p><i/><strong>{countText(positive)}</strong><span>EPA positivo</span></p><p><i/><strong>{countText(other)}</strong><span>EPA zero ou negativo</span></p></div></>}
    <p className="chart-denominator">{countText(positive)} de {countText(total)} jogadas com EPA. O restante inclui valores zero e negativos.</p>
  </figure>;
}
export function MembersGraphic({ d }: { d: DTO }) {
  const total = d.totals?.eligibleN;
  return <figure className="members-graphic" aria-label="Volume observado por jogo">
    <figcaption><strong>Jogadas por jogo</strong><span>Volume observado, não eficiência</span></figcaption>
    <ul>{d.members.map(m => <li key={m.gameId}>
      <div className="member-label"><span>Semana {m.week}{m.round && m.round !== 'REG' ? ` · ${m.round}` : ''}</span><small>{m.gameId}</small></div>
      <div className="member-amount">{m.sourceState === 'ABSENT' || !m.statistics ? <span className="missing-source">Fonte ausente — quantidade desconhecida</span> : <><strong>{countText(m.statistics.eligibleN)}</strong><span>jogadas</span>{total && total !== '0' ? <FractionBar ratio={{ numerator: m.statistics.eligibleN, denominator: total }}/> : <p className="chart-tiny">Zero observado; sem proporção com base zero.</p>}</>}</div>
    </li>)}</ul>
    <p className="chart-denominator">{total ? `Cada barra usa ${countText(total)} jogadas observadas neste recorte como base.` : 'Não há fonte para contar as jogadas deste recorte.'} Sem inferência de ritmo ou tendência. Jogos sem fonte não entram na soma.</p>
  </figure>;
}
function Frequency({ d }: { d: DTO }) {
  if (d.subject.foundation === 'general' || !d.totals) return null;
  const r = d.values.frequency;
  return <section className="direction-frequency" aria-label="Frequência do fundamento"><div><h3>Participação {d.subject.foundation === 'classified_pass' ? 'do passe' : 'da corrida'}{d.subject.role === 'def' ? (d.subject.foundation === 'classified_pass' ? ' enfrentado' : ' enfrentada') : ''}</h3><p>Distribuição da amostra, não qualidade.</p></div><div><strong>{r ? formatRatio(r, d.presentation.ratePercentDecimals, true) : 'Sem denominador'}</strong><p>{countText(d.totals.eligibleN)} de {countText(d.totals.generalEligibleN)} jogadas classificadas.</p></div>{r && <div role="img" aria-label={`${d.totals.eligibleN} de ${d.totals.generalEligibleN}; complemento: outras jogadas classificadas.`}><FractionBar ratio={r}/><p className="frequency-key">Fundamento selecionado <span>Outras jogadas classificadas</span></p></div>}</section>;
}
function Metrics({ d }: { d: DTO }) {
  const parts = successParts(d); const t = d.totals; const def = d.subject.role === 'def';
  return <aside className="direction-metrics" aria-label="Números de apoio">
    <section><h3>{def ? 'EPA permitido' : 'EPA por jogada'}</h3><strong className="epa-number">{d.values.epa ? formatRatio(d.values.epa, d.presentation.epaDecimals, false, true) : '—'}</strong><p>{d.values.epa ? 'Pontos esperados / jogada' : 'EPA indisponível'}</p><p>{t ? `${countText(t.epaN)} jogadas com EPA` : 'Sem fonte de jogadas'}</p><p className="metric-explain">{d.values.epa ? 'EPA é a mudança nos pontos esperados. Zero é a referência numérica.' : t ? 'Denominador EPA zero; não equivale a valor zero.' : 'O período foi preservado, sem usar outra fonte.'}</p></section>
    <section className="support-success"><h3>{def ? 'Sucesso permitido' : 'Taxa de sucesso'}</h3><strong>{parts?.percent ?? '—'}</strong><p>{parts ? `${countText(parts.positive)} de ${countText(parts.total)} com EPA positivo` : 'Sem denominador EPA'}</p></section>
    <section className="sample-support"><h3>Amostra deste recorte</h3><p><strong>{t ? countText(t.eligibleN) : '—'}</strong> {t ? 'jogadas observadas' : 'quantidade desconhecida'}</p><p>{d.observed.includedGameIds.length} {d.observed.includedGameIds.length === 1 ? 'jogo com fonte' : 'jogos com fonte'} · {d.observed.actualWeeks.length} {d.observed.actualWeeks.length === 1 ? 'semana observada' : 'semanas observadas'}</p><p>Não é o total da temporada.</p></section>
  </aside>;
}
function EssentialLimits({ d }: { d: DTO }) {
  const t = d.totals;
  return <aside className="direction-limits" aria-label="Limites essenciais"><strong>Como ler esta amostra</strong><p>{d.guarantees.completeness.state === 'COMPLETE' ? 'A população declarada está completa.' : d.guarantees.completeness.state === 'PARTIAL' ? 'A fonte contém uma amostra parcial.' : 'Não sabemos se todas as jogadas estão na fonte.'} {d.guarantees.coverage.expectedCount === null ? 'O total de jogos esperado não foi confirmado.' : `Jogos esperados: ${countText(d.guarantees.coverage.expectedCount)}.`} Este arquivo não comprova o que era conhecido antes dos jogos. Sem comparação entre times ou previsão de vencedor.</p>{t && (t.epaMissingN !== '0' || t.epaNonfiniteN !== '0') && <p>Fora da base EPA: {countText(t.epaMissingN)} valores ausentes e {countText(t.epaNonfiniteN)} não finitos.</p>}</aside>;
}
function FieldScene() {
  return <div className="field-scene" aria-hidden="true"><span/><span/><span/><span/><span/><span/><span/></div>;
}
export function DirectionReading({ d, entry, direction, controls }: { d: DTO; entry: Pick<Entry, 'label' | 'dataKind'>; direction: Exclude<Direction, 'original' | 'D' | 'E'>; controls: ReactNode }) {
  const team = teams[d.subject.team] ?? { city: '', name: d.subject.team }; const parts = successParts(d); const def = d.subject.role === 'def';
  const empty = d.totals?.eligibleN === '0';
  return <article className={`direction-reading scene-${direction}`} aria-label="Observação selecionada" data-observation-id={d.observationId}>
    <div className="reading-scene">
      <div className="scene-background" aria-hidden="true"><span className="background-word">{team.name}</span><FieldScene/></div>
      <header className="direction-identity"><p className="archive-label">{entry.dataKind === 'SYNTHETIC' ? 'Dados sintéticos · demonstração' : 'Arquivo real · histórico'}</p><p className="team-city">{team.city}</p><h2>{team.name}<span>{d.subject.team}</span></h2><p className="sport-subject">{def ? 'Defesa' : 'Ataque'} <span>/</span> {foundationLabel(d.subject)}</p><p className="reading-period">{readingPeriod(d)}</p></header>
      {controls}
      <section className="main-graphic" aria-label="Leitura gráfica principal">
        <div className="observation-statement"><h3>{!d.totals ? 'Não há registro de jogadas.' : empty ? 'Nenhuma jogada elegível observada.' : direction === 'C' ? 'O volume, jogo a jogo.' : parts ? `${countText(parts.positive)} de ${countText(parts.total)} jogadas com EPA positivo.` : 'Há jogadas. Falta a base EPA.'}</h3><p>{!d.totals ? 'Sem play-by-play (PBP), quantidade e eficiência são desconhecidas. Ausência não é zero.' : empty ? (d.guarantees.completeness.state === 'COMPLETE' ? 'População declarada completa e vazia.' : 'Zero nos registros observados; completude não demonstrada.') : def ? 'Valores permitidos ao ataque adversário neste recorte.' : 'Leitura das jogadas arquivadas deste ataque.'}</p></div>
        {direction === 'C' ? <MembersGraphic d={d}/> : d.totals ? <SuccessGraphic d={d} broadcast={direction === 'B'}/> : <div className="source-gap-diagram"><span aria-hidden="true">—</span><strong>Fonte ausente</strong><p>Período solicitado preservado. Nenhuma semana substituída.</p></div>}
        {d.totals && <p className="model-note">{d.guarantees.compatibility.epaModel.state === 'UNKNOWN' ? 'EPA da fonte, modelo não identificado.' : `Modelo EPA: ${d.guarantees.compatibility.epaModel.id}.`} A taxa de sucesso depende desse EPA.</p>}
        {direction === 'C' && <p className="scene-disclaimer">Campo esquemático decorativo. As barras contam jogadas; não mostram posições no campo.</p>}
      </section>
      <Metrics d={d}/>
    </div>
    <Frequency d={d}/>
    <EssentialLimits d={d}/>
    {direction !== 'C' && <details className="obs-details game-reading"><summary>Jogadas por jogo <span>Ver o volume dos registros</span></summary><MembersGraphic d={d}/></details>}
    <ObservationInspection d={d} entry={entry}/>
  </article>;
}
