import { useState, type CSSProperties, type ReactNode } from 'react';
import type { DTO, Entry } from '../observations/model';
import { countText, formatRatio } from '../observations/format';
import { foundationLabel, proportionWidth, readingPeriod } from '../observations/presentation';
import { successParts } from '../observations/directionData';
import { ObservationInspection } from '../observations/ObservationReading';
import { refinementTheme } from './refinementThemes';
import './refinement.css';

function Logo({ src, team }: { src?: string; team: string }) {
 const [failed, setFailed] = useState(false);
 return <div className="r43-logo" aria-hidden="true">{src && !failed ? <img src={src} alt="" width="240" height="200" onError={() => setFailed(true)}/> : <span>{team}</span>}</div>;
}
function Volume({ d }: { d: DTO }) {
 const total = d.totals?.eligibleN;
 return <figure className="r43-volume" aria-label="Volume observado por jogo"><figcaption>Volume observado, não eficiência</figcaption><ul>{d.members.map(m => <li key={m.gameId}>
  <div><strong>Semana {m.week}{m.round && m.round !== 'REG' ? ` · ${m.round}` : ''}</strong><details className="r43-game-id"><summary>Identificador do jogo</summary><p>{m.gameId}</p></details></div>
  <div className="r43-volume-value">{m.sourceState === 'ABSENT' || !m.statistics ? <span>Fonte ausente · quantidade desconhecida</span> : <><strong>{countText(m.statistics.eligibleN)}</strong><span> jogadas</span></>}</div>
  {m.statistics && total && total !== '0' && <div className="r43-volume-track" aria-hidden="true"><span style={{ width: proportionWidth({ numerator: m.statistics.eligibleN, denominator: total }) }}/></div>}
 </li>)}</ul><p>{total ? `Base de cada barra: ${countText(total)} jogadas observadas neste recorte.` : 'Não há fonte para contar as jogadas deste recorte.'} Sem inferência de ritmo ou tendência. Jogos sem fonte não entram na soma.{total === '0' && ' Sem proporção com base zero.'}</p></figure>;
}
export function RefinedBroadcastReading({ d, entry, controls }: { d: DTO; entry: Pick<Entry, 'label' | 'dataKind'>; controls: ReactNode }) {
 const theme = refinementTheme(d.subject.team); const t = d.totals; const defense = d.subject.role === 'def';
 const parts = successParts(d); const width = parts ? proportionWidth(parts.ratio) : null;
 const tiny = parts && parts.positive !== '0' && width === '0.00%';
 const completeness = d.guarantees.completeness.state === 'COMPLETE' ? 'População declarada completa.' : d.guarantees.completeness.state === 'PARTIAL' ? 'Fonte parcial.' : 'Completude desconhecida.';
 const style = { '--name-plate': theme.namePlate, '--name-ink': theme.nameInk, '--logo-plate': theme.logoPlate, '--context-plate': theme.contextPlate, '--identity-accent': theme.accent, '--team-scene': theme.scene, '--logo-scale': theme.logoScale } as CSSProperties;
 return <article className="r43-reading" data-observation-id={d.observationId} data-team={d.subject.team} aria-label="Observação selecionada" style={style}>
  <div className="r43-stage"><div className="r43-board">
   <header className="r43-identity"><div className="r43-name"><p>{theme.city}</p><h2>{theme.name}</h2><span>{d.subject.team}</span></div><Logo key={d.subject.team} src={theme.logo} team={d.subject.team}/></header>
   <div className="r43-context"><p><strong>{defense ? 'Defesa' : 'Ataque'}</strong><span>{foundationLabel(d.subject)}</span></p><p>{readingPeriod(d)}</p></div>
   {controls}
   <div className="r43-surface">
    <p className="r43-source">{entry.dataKind === 'SYNTHETIC' ? 'Dados sintéticos · demonstração' : 'Arquivo real · leitura histórica'}</p>
    <section className="r43-main" aria-label="Composição da amostra">
     <h3>{!t ? 'Não há fonte para este período' : t.eligibleN === '0' ? 'Amostra observada vazia' : !parts ? 'Há jogadas, mas não há base EPA' : defense ? 'Sucesso permitido ao adversário' : 'Jogadas com EPA positivo'}</h3>
     {parts ? <figure className="r43-composition" aria-label={`${countText(parts.positive)} de ${countText(parts.total)} jogadas com EPA positivo; ${countText(parts.other)} com EPA zero ou negativo. Taxa de sucesso: ${parts.percent}.`}>
      <div className="r43-fact"><strong>{parts.percent}</strong><figcaption>{countText(parts.positive)} de {countText(parts.total)}<span>jogadas com EPA positivo</span></figcaption></div>
      {tiny ? <p>Proporção positiva menor que 0,01%; sem área mínima artificial.</p> : <div className="r43-track" aria-hidden="true">{parts.positive !== '0' && <span style={{ width: width! }}/>}</div>}
      <div className="r43-legend"><span><i/>EPA positivo</span><span><i/>{countText(parts.other)} com EPA zero ou negativo</span></div>
     </figure> : <div className="r43-no-data"><span aria-hidden="true">—</span><p>{!t ? 'Sem registro de jogadas (PBP), quantidade e eficiência são desconhecidas. Ausência não é zero.' : t.eligibleN === '0' ? (d.guarantees.completeness.state === 'COMPLETE' ? 'População declarada completa e vazia. Não há denominador para calcular eficiência.' : 'Nenhuma jogada elegível nos registros observados. A completude não está demonstrada.') : 'Nenhuma jogada com EPA disponível. Denominador zero não é uma taxa de sucesso de 0%.'}</p></div>}
     {defense && <p className="r43-defense">EPA e sucesso são valores permitidos ao ataque adversário.</p>}
     {t && <p className="r43-model">{d.guarantees.compatibility.epaModel.state === 'UNKNOWN' ? 'EPA da fonte, modelo não identificado.' : `Modelo EPA: ${d.guarantees.compatibility.epaModel.id}.`} A taxa de sucesso depende desse EPA.{(t.epaMissingN !== '0' || t.epaNonfiniteN !== '0') && ` Fora da base EPA: ${countText(t.epaMissingN)} ausentes e ${countText(t.epaNonfiniteN)} não finitos.`}</p>}
    </section>
    <aside className="r43-stats" aria-label="EPA e amostra"><dl>
     <div className="r43-epa-row"><dt>{defense ? 'EPA permitido' : 'EPA por jogada'}</dt><dd>{d.values.epa ? formatRatio(d.values.epa,d.presentation.epaDecimals,false,true) : '—'}</dd></div>
     <div><dt>Base EPA</dt><dd>{t ? countText(t.epaN) : '—'}</dd></div>
     <div><dt>Jogadas observadas</dt><dd>{t ? countText(t.eligibleN) : '—'}</dd></div>
     <div><dt>Jogos com fonte</dt><dd>{d.observed.includedGameIds.length}</dd></div>
    </dl><p>{d.values.epa ? 'EPA: mudança nos pontos esperados por jogada. Zero é a referência numérica.' : t ? 'EPA indisponível · denominador EPA zero.' : 'EPA indisponível · fonte ausente.'}</p><p>{t ? 'Amostra deste recorte, não o total da temporada.' : 'A quantidade de jogadas é desconhecida.'}</p></aside>
   </div>
   <aside className="r43-limits" aria-label="Limites essenciais"><p><strong>{completeness}</strong> {d.guarantees.coverage.expectedCount === null ? 'Total esperado de jogos desconhecido.' : `Jogos esperados: ${countText(d.guarantees.coverage.expectedCount)}.`} Conhecimento antes dos jogos não demonstrado.</p><details><summary>Alcance da leitura</summary><p>O arquivo não comprova o que era conhecido antes dos jogos. Sem comparação entre times ou previsão de vencedor. {d.guarantees.completeness.state === 'UNKNOWN' && 'Não sabemos se todas as jogadas estão na fonte.'}</p></details></aside>
   {d.subject.foundation !== 'general' && t && <section className="r43-frequency" aria-label="Frequência do fundamento"><div><h3>Participação {d.subject.foundation === 'classified_pass' ? 'do passe' : 'da corrida'} na amostra</h3><p>{countText(t.eligibleN)} de {countText(t.generalEligibleN)} jogadas classificadas{defense ? ' enfrentadas' : ''}. Frequência descreve distribuição, não qualidade.</p></div><strong>{d.values.frequency ? formatRatio(d.values.frequency,d.presentation.ratePercentDecimals,true) : 'Sem denominador'}</strong></section>}
   <details className="obs-details r43-members"><summary>Jogadas por jogo <span>Volume e disponibilidade de fonte</span></summary><Volume d={d}/></details>
   <ObservationInspection d={d} entry={entry}/>
  </div></div>
 </article>;
}
