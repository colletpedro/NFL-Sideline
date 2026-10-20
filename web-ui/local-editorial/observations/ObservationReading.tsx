import type { DTO, Entry, Ratio } from './model';
import { countText, exact, formatRatio } from './format';
import { readingPeriod, foundationLabel, proportionWidth } from './presentation';

function Proportion({ ratio, label }: { ratio: Ratio; label: string }) {
  if (ratio.numerator !== '0' && proportionWidth(ratio) === '0.00%') return <p className="obs-definition">Proporção positiva, menor que 0,01%; pequena demais para a barra.</p>;
  return <div className="obs-proportion" role="img" aria-label={label}>
    <div className="obs-track" aria-hidden="true"><span style={{ width: proportionWidth(ratio) }}/></div>
    <div className="obs-scale" aria-hidden="true"><span>0%</span><span>100%</span></div>
  </div>;
}
export function ObservationReading({ d, entry }: { d: DTO; entry: Pick<Entry, 'label' | 'dataKind'> }) {
  const t = d.totals; const def = d.subject.role === 'def';
  const missing = d.members.filter(m => m.sourceState === 'ABSENT');
  const epa = d.values.epa && formatRatio(d.values.epa, d.presentation.epaDecimals, false, true);
  const sr = d.values.successRate && formatRatio(d.values.successRate, d.presentation.ratePercentDecimals, true);
  const freq = d.values.frequency && formatRatio(d.values.frequency, d.presentation.ratePercentDecimals, true);
  const foundation = foundationLabel(d.subject);
  const completeness = d.guarantees.completeness.state;
  const metricLabels = { epa: def ? 'EPA permitido' : 'EPA ofensivo', successRate: def ? 'Sucesso permitido' : 'Taxa de sucesso', volume: 'Jogadas observadas', frequency: 'Frequência' };
  return <article className="observation-reading" aria-label="Observação selecionada">
    <header className="obs-heading">
      <div className="obs-team" aria-hidden="true">{d.subject.team}</div>
      <div className="obs-identity"><p className="obs-kind">{entry.dataKind === 'SYNTHETIC' ? 'Dados sintéticos · demonstração' : 'Arquivo real · leitura histórica'}</p>
        <h2><span className="obs-sr-only">{d.subject.team} </span><span>{def ? 'Defesa' : 'Ataque'} / {foundation}</span></h2>
        <p className="obs-date">{readingPeriod(d)}</p>
      </div>
    </header>
    <div className="obs-scoreboard">
      <section className={`obs-sample ${t === null ? 'obs-sample-absent' : ''}`} aria-label="Amostra observada">
        <h3>{t === null ? 'Fonte ausente' : t.eligibleN === '0' ? 'Amostra vazia observada' : 'Amostra observada'}</h3>
        {t ? <><p className="obs-volume">{countText(t.eligibleN)}</p><p className="obs-volume-label">{t.eligibleN === '1' ? (def ? 'jogada enfrentada' : 'jogada') : (def ? 'jogadas enfrentadas' : 'jogadas')}{d.subject.foundation !== 'general' && ` de ${d.subject.foundation === 'classified_pass' ? 'passe' : 'corrida'}`}</p>
          <p className="obs-sample-context">{d.observed.includedGameIds.length} {d.observed.includedGameIds.length === 1 ? 'jogo com fonte' : 'jogos com fonte'} · {d.observed.actualWeeks.length === 1 ? 'semana' : 'semanas'} {d.observed.actualWeeks.join(', ') || 'nenhuma'}</p></> : <><p className="obs-absent-title">Sem registro de jogadas.</p><p>O play-by-play (PBP) não está disponível neste recorte. Quantidade e eficiência são desconhecidas, não zero.</p></>}
        <p className="obs-sample-note">{t === null ? 'Nenhuma semana observada. O período solicitado foi preservado.' : d.scope.population === 'OBSERVED_SAMPLE' ? 'Amostra do arquivo; não é o total da temporada.' : 'População declarada neste recorte.'}</p>
      </section>
      {t && <div className="obs-efficiency">
        <div className="obs-metric-pair">
          <section className="obs-metric"><h3>{metricLabels.epa}</h3><p className={`obs-value ${epa === null ? 'obs-undefined' : epa.length > 6 ? 'obs-value-compact' : ''}`}>{epa ?? 'Sem denominador'}</p>
            <p>pontos esperados / jogada</p><p className="obs-denominator">{countText(t.epaN)} {t.epaN === '1' ? 'jogada' : 'jogadas'} com EPA</p>
            {epa !== null ? <p className="obs-definition">EPA mede a mudança nos pontos esperados. Zero é a referência numérica{d.values.epa?.numerator === '0' ? ' · zero conhecido' : ''}.</p> : <p className="obs-definition">Denominador zero; não equivale a valor zero.</p>}
          </section>
          <section className="obs-metric"><h3>{metricLabels.successRate}</h3><p className={`obs-value ${sr === null ? 'obs-undefined' : sr.length > 6 ? 'obs-value-compact' : ''}`}>{sr ?? 'Sem denominador'}</p>
            <p>{def ? 'EPA positivo do ataque adversário' : 'jogadas com EPA positivo'}</p><p className="obs-denominator">{countText(t.successN)} de {countText(t.epaN)} {t.epaN === '1' ? 'jogada' : 'jogadas'} com EPA{d.values.successRate?.numerator === '0' && d.values.successRate && ' · zero conhecido'}</p>
            {d.values.successRate && <Proportion ratio={d.values.successRate} label={`${metricLabels.successRate}: ${sr}; ${t.successN} de ${t.epaN} jogadas com EPA positivo.`}/>}
          </section>
        </div>
        <p className="obs-model">{d.guarantees.compatibility.epaModel.state === 'UNKNOWN' ? 'EPA da fonte, modelo não identificado. A taxa de sucesso depende desse mesmo EPA.' : `Modelo EPA declarado: ${d.guarantees.compatibility.epaModel.id}. A taxa de sucesso depende desse EPA.`}{def && ' Os dois valores são permitidos ao ataque adversário.'}{(t.epaMissingN !== '0' || t.epaNonfiniteN !== '0') && ` Fora da base EPA: ${countText(t.epaMissingN)} ausente(s) e ${countText(t.epaNonfiniteN)} não finito(s).`}</p>
      </div>}
    </div>
    {t?.eligibleN === '0' && <p className="obs-gap">{completeness === 'COMPLETE' ? 'Observação vazia sustentada: população declarada completa, sem jogadas elegíveis.' : 'Zero jogadas elegíveis no conteúdo observado; completude não demonstrada.'} EPA e taxas sem denominador permanecem indisponíveis.</p>}
    {missing.length > 0 && t !== null && <p className="obs-gap">Fonte ausente em {missing.length} jogo(s) do recorte. As métricas usam apenas os jogos com fonte; as lacunas não são zero.</p>}
    {d.subject.foundation !== 'general' && t && <section className="obs-frequency" aria-label="Distribuição da amostra">
      <div><h3>Frequência de {d.subject.foundation === 'classified_pass' ? 'passes' : 'corridas'}{def ? ' enfrentados' : ''}</h3><p>Distribuição de jogadas, não qualidade ou eficiência.</p></div>
      <div className="obs-frequency-value"><strong>{freq ?? 'Sem denominador'}</strong><span>{countText(t.eligibleN)} de {countText(t.generalEligibleN)} {t.generalEligibleN === '1' ? 'jogada geral' : 'jogadas gerais'}</span></div>
      {d.values.frequency ? <Proportion ratio={d.values.frequency} label={`Frequência: ${freq}; ${t.eligibleN} de ${t.generalEligibleN} jogadas gerais da mesma amostra.`}/> : <p>Denominador zero; a frequência é desconhecida.</p>}
    </section>}
    <aside className="obs-limits" aria-label="Limites essenciais"><h3>Até onde esta leitura vai</h3>
      <p>{completeness === 'COMPLETE' ? 'Completude demonstrada para a população declarada.' : completeness === 'PARTIAL' ? 'A fonte contém uma amostra parcial.' : 'Não sabemos se a fonte contém todas as jogadas.'} {d.guarantees.coverage.expectedCount === null ? 'Cobertura esperada desconhecida.' : `${d.observed.includedGameIds.length} jogo(s) com fonte de ${countText(d.guarantees.coverage.expectedCount)} esperado(s).`} Conhecimento no corte não demonstrado: este arquivo não comprova o que se sabia antes dos jogos. Sem comparação entre times ou previsão de vencedor.</p>
    </aside>
    <ObservationInspection d={d} entry={entry}/>
  </article>;
}

export function ObservationInspection({ d, entry }: { d: DTO; entry: Pick<Entry, 'label' | 'dataKind'> }) {
  const t = d.totals; const def = d.subject.role === 'def';
  const metricLabels = { epa: def ? 'EPA permitido' : 'EPA ofensivo', successRate: def ? 'Sucesso permitido' : 'Taxa de sucesso', volume: 'Jogadas observadas', frequency: 'Frequência' };
  return (
    <div className="obs-inspection">
      <details className="obs-details"><summary>Precisão e contagens <span>Valores originais e denominadores</span></summary>
        <dl className="obs-counts">{Object.entries(d.values).map(([key, value]) => <div key={key}><dt>{metricLabels[key as keyof typeof metricLabels]} · fração exata</dt><dd>{value ? exact(value) : 'Desconhecido / não definido'}</dd></div>)}</dl>
        {t && <dl className="obs-counts">{Object.entries(t).map(([key, value]) => <div key={key}><dt>{({ eligibleN: 'Jogadas elegíveis do fundamento', epaN: 'Denominador EPA', epaSum: 'Soma EPA exata', successN: 'Sucessos (EPA > 0)', epaMissingN: 'EPA ausente', epaNonfiniteN: 'EPA não finito', generalEligibleN: 'Jogadas gerais do mesmo contexto', unknownFilterFlagsN: 'Flags desconhecidas · contexto dos jogos' } as Record<string, string>)[key]}</dt><dd>{value ?? 'Não disponível'}</dd></div>)}</dl>}
        <p>Flags desconhecidas são contexto do jogo inteiro, não contagem medida por time ou fundamento. Não somar entre grupos ou períodos sobrepostos.</p>
      </details>
      <details className="obs-details"><summary>Origem e limites completos <span>Jogos, evidências e identidades</span></summary>
        <p>{entry.label}. {d.request.origin === 'HISTORICAL_REFERENCE' ? 'Referência histórica separada da temporada corrente.' : 'A origem CURRENT identifica o arquivo da temporada; não significa atualização da semana atual.'} Solicitado: semanas {d.request.period.weeks.join(', ')}. Observado: {d.observed.actualWeeks.join(', ') || 'nenhuma semana'}.</p>
        <ul className="obs-games">{d.members.map(m => <li key={m.gameId}><strong>{m.gameId}</strong><span>Semana {m.week}{m.round && ` / ${m.round}`} · {m.sourceState === 'ABSENT' ? 'Fonte ausente; contagens desconhecidas' : `Fonte presente; ${countText(m.statistics!.eligibleN)} jogadas elegíveis; completude ${m.completeness}`}</span></li>)}</ul>
        <h3>Garantias do documento</h3><dl>{Object.entries(d.guarantees).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value.state} · {value.reasonCodes.join(', ') || 'sem motivos adicionais'}</dd></div>)}</dl>
        <h3>Motivos e vínculos de evidência</h3><ul>{d.limitations.map((m, i) => <li key={i}><code>{m.code}</code> · {m.subjectId}</li>)}</ul>
        <h3>Identidades para rastreabilidade</h3><dl><dt>Bundle validado</dt><dd>{d.bundleId}</dd><dt>Observação original</dt><dd>{d.observationId}</dd><dt>DTO reduzido de transporte</dt><dd>{d.dtoId}</dd></dl>
        <h3>Escopos originais do transporte</h3><dl>{Object.entries(d.fieldScopes).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>
        <p>O DTO é uma projeção de apresentação; seu hash não identifica os bytes originais. A verificação do browser é estrutural e não autentica a origem. A linhagem integral e os receipts permanecem no bundle local validado.</p>
      </details>
    </div>
  );
}
