import { useState, type CSSProperties } from 'react';
import type { DTO, Entry } from '../local-editorial/observations/model';
import { countText, exact } from '../local-editorial/observations/format';
import { ObservationInspection } from '../local-editorial/observations/ObservationReading';
import { Logo } from '../broadcast-experience/TeamLogo';
import { presentObservation } from './adapter';
import { teamIdentity } from './identity';

type ReadingProps = { d: DTO; entry: Entry; memberLabels?: Record<string, string>; detailsOpen?: boolean; compositionOpen?: boolean; onDetailsChange?: (open: boolean) => void; onCompositionChange?: (open: boolean) => void };
export function Reading({ d, entry, memberLabels, detailsOpen, compositionOpen, onDetailsChange, onCompositionChange }: ReadingProps) {
  const p = presentObservation(d), team = teamIdentity(d.subject.team), t = d.totals;
  const [localChartDetail, setChartDetail] = useState(false);
  const chartDetail = compositionOpen ?? localChartDetail;
  const count = d.observed.includedGameIds.length;
  return <article className="real-reading" aria-label="Observação real selecionada" style={{ '--team': team.color, '--team-dark': team.dark, '--optical': team.optical } as CSSProperties}>
    <header className="real-identity">
      <span className="real-watermark" aria-hidden="true">{team.id}</span>
      <Logo key={team.id} team={team}/>
      <div className="real-team"><span>{team.city}</span><strong>{team.name}</strong><h1>{p.role} <span>/ {p.foundation}</span></h1></div>
      <div className="real-period"><span>Período solicitado</span><p>{p.period}</p></div>
    </header>
    <div className="real-context"><strong>{t ? 'Amostra observada' : 'Nenhuma fonte observada'}</strong><span>{count} {count === 1 ? 'jogo com fonte' : 'jogos com fonte'} · Semanas observadas: {d.observed.actualWeeks.join(', ') || 'nenhuma'}</span></div>
    <section className="real-story" aria-label="Fato da amostra">
      <div><p className="real-label">{p.factContext}</p><h2>{p.fact}</h2>{p.defensive && <p>EPA e sucesso descrevem o que a defesa permitiu ao ataque adversário; os sinais são os da fonte.</p>}
      {p.sourceState === 'absent' && <p>O play-by-play não está disponível neste recorte. Volume e eficiência são desconhecidos. Ausência de fonte não é zero.</p>}
      {p.sourceState === 'empty' && <p>{d.guarantees.completeness.state === 'COMPLETE' ? 'População declarada completa sem jogadas elegíveis.' : 'Zero jogadas elegíveis nos bytes observados; completude não confirmada.'}</p>}
      <a className="real-detail-link" href="#real-details">Ver contagens e origem <span aria-hidden="true">↘</span></a></div>
      {t && <div className="real-numbers"><div><h3>{p.epaLabel}</h3><strong data-value="epa">{p.epa ?? 'Sem denominador'}</strong><p>pontos esperados / jogada</p><p>{countText(t.epaN)} jogadas com EPA finito</p><p>{p.modelNote}. EPA da fonte.</p></div><div><h3>Volume {p.defensive ? 'enfrentado' : 'observado'}</h3><strong data-value="volume">{p.volume}</strong><p>jogadas elegíveis {d.subject.foundation !== 'general' ? `de ${d.subject.foundation === 'classified_pass' ? 'passe' : 'corrida'}` : 'de passe + corrida'}</p>{d.subject.foundation !== 'general' && <p>Frequência: <b>{p.frequency ?? 'Sem denominador'}</b><br/>{countText(t.eligibleN)} / {countText(t.generalEligibleN)} jogadas gerais</p>}</div></div>}
    </section>
    {t && <section className="real-chart-section" aria-labelledby="real-chart-title">
      <div className="real-chart-heading"><div><p className="real-label">Dentro das jogadas com EPA finito</p><h2 id="real-chart-title">{p.successLabel}</h2></div><strong data-value="success">{p.success ?? 'Sem denominador'}</strong></div>
      {d.values.successRate ? <><div className="real-chart" role="img" aria-label={`${p.successLabel}: ${p.success}. ${t.successN} de ${t.epaN}. Complemento: ${p.complement!.numerator} com EPA zero ou negativo.`}>
        {!p.tiny && <div className="real-track" aria-hidden="true"><span style={{ width: p.width! }}/></div>}
        {p.tiny && <p>Proporção positiva menor que 0,01%; pequena demais para a barra.</p>}
        <div className="real-scale" aria-hidden="true"><span>0%</span><span>50%</span><span>100%</span></div>
      </div><div className="real-chart-key"><p><i aria-hidden="true"/><b>{countText(t.successN)} / {countText(t.epaN)}</b> com EPA positivo</p><p><i aria-hidden="true"/><b>{countText(p.complement!.numerator)} / {countText(t.epaN)}</b> com EPA zero ou negativo <span>({p.complementPercent})</span></p></div>
      <button className="real-chart-button" onClick={() => { setChartDetail(!chartDetail); onCompositionChange?.(!chartDetail); }} aria-expanded={chartDetail} aria-controls="chart-counts">{chartDetail ? 'Fechar composição' : 'Explorar composição'}</button>
      {chartDetail && <div id="chart-counts" className="real-chart-detail"><p>EPA positivo: {exact(d.values.successRate)}. EPA zero ou negativo: {exact(p.complement!)}. A unidade é a jogada com EPA finito, neste mesmo recorte.</p><p>Fora do denominador: {countText(t.epaMissingN)} com EPA ausente e {countText(t.epaNonfiniteN)} com EPA não finito. Volume elegível: {countText(t.eligibleN)}.</p></div>}</> : <p className="real-empty">Denominador EPA zero. A proporção é indisponível; isso não significa 0% de sucesso.</p>}
      <p className="real-model">{p.modelNote}. A proporção de sucesso depende desse mesmo EPA.{p.defensive && ' Valores permitidos ao ataque adversário.'}</p>
      {(t.epaMissingN !== '0' || t.epaNonfiniteN !== '0') && <p className="real-model">Fora da base EPA: {countText(t.epaMissingN)} ausentes e {countText(t.epaNonfiniteN)} não finitos. Esses valores não entram na média nem na proporção.</p>}
    </section>}
    <aside className="real-limits" aria-label="Limitações essenciais"><h2>Até onde a amostra permite ler</h2><ul><li>{p.completenessNote}</li><li>{p.coverageNote}</li><li>Conhecimento anterior ao jogo não demonstrado</li>{!t && <li>{p.modelNote}</li>}</ul><p>{t === null ? 'Nenhuma amostra de jogadas observada neste período.' : d.scope.population === 'OBSERVED_SAMPLE' ? 'Amostra do arquivo, sem garantia de representar todo o período.' : 'População declarada neste recorte.'} O arquivo não demonstra o que se sabia antes dos jogos.</p>
      {d.members.some(m => m.sourceState === 'ABSENT') && t && <p>Há jogo sem fonte neste período. As lacunas não foram preenchidas.</p>}</aside>
    <section className="real-members" aria-label="Jogos desta observação"><div className="stats-title"><h2>Volume por jogo</h2><p>{t ? 'Jogadas elegíveis da mesma observação.' : 'Contagens indisponíveis para o período solicitado.'}</p></div><ul>{d.members.map(m => <li key={m.gameId}><div><strong>{memberLabels?.[m.gameId] ?? m.gameId}</strong><span>Semana {m.week}{m.round && ` / ${m.round}`}</span></div><b>{m.statistics ? countText(m.statistics.eligibleN) : 'Sem fonte'}</b><span>{m.sourceState === 'ABSENT' ? 'Contagem desconhecida' : 'Fonte presente'}</span></li>)}</ul><p>Contagens dos bytes observados; não indicam tendência ou ritmo.</p></section>
    <section id="real-details" className="real-details" tabIndex={-1}><h2>Verificar a leitura</h2><ObservationInspection d={d} entry={entry} precisionOpen={detailsOpen} onPrecisionChange={onDetailsChange}/></section>
  </article>;
}
