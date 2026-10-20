import { useState, type CSSProperties, type ReactNode } from 'react';
import type { DTO, Entry } from '../observations/model';
import { countText, formatRatio } from '../observations/format';
import { foundationLabel, proportionWidth, readingPeriod } from '../observations/presentation';
import { successParts } from '../observations/directionData';
import { ObservationInspection } from '../observations/ObservationReading';
import { MembersGraphic } from '../observations/DirectionReading';
import { broadcastThemes, neutralTheme } from './themes';
import './broadcast.css';

function TeamLogo({ src, team }: { src?: string; team: string }) {
 const [failed, setFailed] = useState(false);
 return <div className="broadcast-logo" aria-hidden="true">{src && !failed ? <img src={src} alt="" width="240" height="200" onError={() => setFailed(true)}/> : <span>{team}</span>}</div>;
}
export function BroadcastReading({ d, entry, controls }: { d: DTO; entry: Pick<Entry, 'label' | 'dataKind'>; controls: ReactNode }) {
 const theme = broadcastThemes[d.subject.team] ?? { ...neutralTheme, name: d.subject.team };
 const parts = successParts(d); const t = d.totals; const defense = d.subject.role === 'def';
 const width = parts ? proportionWidth(parts.ratio) : null;
 const tiny = parts && parts.positive !== '0' && width === '0.00%';
 const style = { '--team-identity': theme.identity, '--team-identity-low': theme.identityLow, '--team-ink': theme.text, '--team-trim': theme.secondary, '--team-scene': theme.scene, '--logo-scale': theme.logoScale } as CSSProperties;
 return <article className="broadcast-reading" data-observation-id={d.observationId} data-team={d.subject.team} aria-label="Observação selecionada" style={style}>
  <div className="broadcast-stage">
   <div className="broadcast-scenery" aria-hidden="true"><span>{theme.name}</span><i/><i/><i/></div>
   <div className="broadcast-board">
    <header className="broadcast-identity"><div><p>{theme.city}</p><h2>{theme.name}</h2><span className="broadcast-abbr">{d.subject.team}</span></div><TeamLogo key={d.subject.team} src={theme.logo} team={d.subject.team}/></header>
    <div className="broadcast-context"><p><strong>{defense ? 'Defesa' : 'Ataque'}</strong><span>{foundationLabel(d.subject)}</span></p><div><p>{readingPeriod(d)}</p><span>{entry.dataKind === 'SYNTHETIC' ? 'Dados sintéticos · demonstração' : 'Arquivo real · leitura histórica'}</span></div></div>
    {controls}
    <div className="broadcast-stat-surface">
     <section className="broadcast-main" aria-label="Composição da amostra">
      <h3>{!t ? 'Não há fonte para este período' : t.eligibleN === '0' ? 'Amostra observada vazia' : !parts ? 'Há jogadas, mas não há base EPA' : defense ? 'Sucesso permitido ao adversário' : 'Jogadas com EPA positivo'}</h3>
      {parts ? <figure className="broadcast-composition" aria-label={`${countText(parts.positive)} de ${countText(parts.total)} jogadas com EPA positivo; ${countText(parts.other)} com EPA zero ou negativo. Taxa de sucesso: ${parts.percent}.`}>
       <div className="broadcast-fact"><strong>{parts.percent}</strong><figcaption>{countText(parts.positive)} de {countText(parts.total)} jogadas com EPA positivo</figcaption></div>
       {tiny ? <p>Proporção positiva menor que 0,01%; sem área mínima artificial.</p> : <div className="broadcast-track" aria-hidden="true">{parts.positive !== '0' && <span style={{ width: width! }}/> }</div>}
       <div className="broadcast-legend"><span><i/>EPA positivo</span><span><i/>{countText(parts.other)} com EPA zero ou negativo</span></div>
      </figure> : <div className="broadcast-no-data"><span aria-hidden="true">—</span><p>{!t ? 'Sem registro de jogadas (PBP), quantidade e eficiência são desconhecidas. Ausência não é zero.' : t.eligibleN === '0' ? (d.guarantees.completeness.state === 'COMPLETE' ? 'População declarada completa e vazia. Não há denominador para calcular eficiência.' : 'Nenhuma jogada elegível nos registros observados. A completude não está demonstrada.') : 'Nenhuma jogada com EPA disponível. Denominador zero não é uma taxa de sucesso de 0%.'}</p></div>}
      {defense && <p className="broadcast-explanation">EPA e sucesso são valores permitidos ao ataque adversário.</p>}
     </section>
     <aside className="broadcast-stats" aria-label="EPA e amostra">
      <section><h3>{defense ? 'EPA permitido' : 'EPA por jogada'}</h3><strong className="broadcast-epa">{d.values.epa ? formatRatio(d.values.epa,d.presentation.epaDecimals,false,true) : '—'}</strong><p>{d.values.epa ? `Pontos esperados / jogada · base ${countText(t!.epaN)}` : t ? 'Indisponível · denominador EPA zero' : 'Indisponível · fonte ausente'}</p><p className="broadcast-epa-definition">Mudança nos pontos esperados.<br/>Zero é a referência numérica.</p></section>
      <dl><div><dt>Jogadas observadas</dt><dd>{t ? countText(t.eligibleN) : '—'}</dd></div><div><dt>Jogos com fonte</dt><dd>{d.observed.includedGameIds.length}</dd></div></dl><p className="broadcast-sample-note">{t ? 'Amostra deste recorte, não o total da temporada.' : 'A quantidade de jogadas é desconhecida.'}</p>
     </aside>
     {t && <p className="broadcast-model">{d.guarantees.compatibility.epaModel.state === 'UNKNOWN' ? 'EPA da fonte, modelo não identificado.' : `Modelo EPA: ${d.guarantees.compatibility.epaModel.id}.`} A taxa de sucesso depende desse EPA.{(t.epaMissingN !== '0' || t.epaNonfiniteN !== '0') && ` Fora da base EPA: ${countText(t.epaMissingN)} ausentes e ${countText(t.epaNonfiniteN)} não finitos.`}</p>}
    </div>
    <aside className="broadcast-limits" aria-label="Limites essenciais"><strong>Limites da leitura</strong><p>{d.guarantees.completeness.state === 'COMPLETE' ? 'População declarada completa.' : d.guarantees.completeness.state === 'PARTIAL' ? 'Fonte parcial.' : 'Não sabemos se todas as jogadas estão na fonte.'} {d.guarantees.coverage.expectedCount === null ? 'Total esperado de jogos não confirmado.' : `Jogos esperados: ${countText(d.guarantees.coverage.expectedCount)}.`} O arquivo não comprova o que era conhecido antes dos jogos. Sem comparação entre times ou previsão de vencedor.</p></aside>
   </div>
  </div>
  {d.subject.foundation !== 'general' && t && <section className="broadcast-frequency" aria-label="Frequência do fundamento"><div><h3>Participação {d.subject.foundation === 'classified_pass' ? 'do passe' : 'da corrida'} na amostra</h3><p>{countText(t.eligibleN)} de {countText(t.generalEligibleN)} jogadas classificadas{defense ? ' enfrentadas' : ''}. Frequência descreve distribuição, não qualidade.</p></div><strong>{d.values.frequency ? formatRatio(d.values.frequency,d.presentation.ratePercentDecimals,true) : 'Sem denominador'}</strong></section>}
  <details className="obs-details broadcast-members"><summary>Jogadas por jogo <span>Volume e disponibilidade de fonte</span></summary><MembersGraphic d={d}/></details>
  <ObservationInspection d={d} entry={entry}/>
 </article>;
}
