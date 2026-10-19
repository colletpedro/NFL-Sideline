import { useEffect, useState } from 'react';
import type { Catalog, DTO, Entry, Summary } from './model';
import { errorText, observationCatalog, observationDocument } from './client';
import { countText, exact, formatRatio } from './format';
import { chooseAvailable, order, period } from './selection';
import './observations.css';
const roleName = { off: 'Ataque', def: 'Defesa' };
const foundationName = { general: 'Geral', classified_pass: 'Passe classificado', classified_rush: 'Corrida classificada' };
const failure = (cause: unknown) => cause instanceof Error ? cause.message : 'Falha na leitura local.';
function saved() { try { return JSON.parse(sessionStorage.getItem('metrics-lab-choice') ?? '{}') as { entryId?: string; observationId?: string }; } catch { return {}; } }

export function ObservationReading({ d, entry }: { d: DTO; entry: Pick<Entry, 'label' | 'dataKind'> }) {
  const t = d.totals; const def = d.subject.role === 'def';
  const missing = d.members.filter(m => m.sourceState === 'ABSENT');
  const zeroDenominator = (key: 'epa' | 'successRate' | 'frequency') => t !== null && (key === 'frequency' ? t.generalEligibleN === '0' : t.epaN === '0');
  const cards = [
    { key: 'epa' as const, label: def ? 'EPA permitido' : 'EPA ofensivo', unit: 'pontos esperados por jogada', formatted: d.values.epa ? formatRatio(d.values.epa, d.presentation.epaDecimals, false, true) : null },
    { key: 'successRate' as const, label: def ? 'Sucesso permitido' : 'Taxa de sucesso', unit: def ? 'EPA positivo do ataque adversário' : 'jogadas com EPA positivo', formatted: d.values.successRate ? formatRatio(d.values.successRate, d.presentation.ratePercentDecimals, true) : null },
    { key: 'volume' as const, label: def ? 'Jogadas enfrentadas observadas' : 'Jogadas observadas', unit: 'população classificada nos bytes observados', formatted: d.values.volume ? countText(d.values.volume.numerator) : null },
    ...(d.subject.foundation === 'general' ? [] : [{ key: 'frequency' as const,
      label: `Frequência de ${d.subject.foundation === 'classified_pass' ? 'passes' : 'corridas'}${def ? ' enfrentados' : ''}`,
      unit: 'jogadas do fundamento / jogadas gerais', formatted: d.values.frequency ? formatRatio(d.values.frequency, d.presentation.ratePercentDecimals, true) : null }]),
  ];
  return <article className="observation-reading" aria-label="Observação selecionada">
    <div className="obs-heading"><p className="eyebrow">{entry.dataKind === 'SYNTHETIC' ? 'DADOS SINTÉTICOS · DEMONSTRAÇÃO' : 'ARQUIVO REAL · VALIDADO NO INÍCIO DA SESSÃO'}</p>
      <h2>{d.subject.team} <span>· {roleName[d.subject.role]}</span></h2><p>{foundationName[d.subject.foundation]} · {period(d)}</p></div>
    <aside className="obs-limits" aria-label="Limites essenciais">
      <strong>Observação arquivada. Conhecimento no corte não demonstrado.</strong>
      <p>{d.request.origin === 'CURRENT' ? 'CURRENT identifica a origem declarada; não significa atualização da temporada. ' : 'Referência histórica separada da temporada corrente. '}
        Conteúdo observado nas semanas {d.observed.actualWeeks.join(', ') || 'nenhuma'}; solicitado nas semanas {d.request.period.weeks.join(', ')}.</p>
      <p>Completude: {d.guarantees.completeness.state === 'COMPLETE' ? 'completa para a população declarada' : d.guarantees.completeness.state === 'PARTIAL' ? 'subset parcial' : 'desconhecida'}.
        {' '}{d.guarantees.compatibility.epaModel.state === 'UNKNOWN' ? 'EPA da fonte; modelo não identificado. A taxa de sucesso também depende desse EPA.' : `Modelo EPA declarado: ${d.guarantees.compatibility.epaModel.id}.`}</p>
      <p>{d.guarantees.coverage.expectedCount === null ? 'Cobertura esperada desconhecida; não há percentual de cobertura.' : `${d.observed.includedGameIds.length} jogo(s) observado(s) de ${d.guarantees.coverage.expectedCount} esperado(s).`}
        {' '}Não há comparação entre times nem conclusão pregame nesta leitura.</p>
    </aside>
    {missing.length > 0 && <p className="obs-gap" role="status">Fonte ausente para {missing.map(m => m.gameId).join(', ')}. Valores desconhecidos não são zero.</p>}
    {t?.eligibleN === '0' && <p className="obs-gap">{d.guarantees.completeness.state === 'COMPLETE' ? 'Observação vazia sustentada: população declarada completa, sem jogadas elegíveis.' : 'População observada vazia: zero jogadas elegíveis nesses bytes; completude não demonstrada.'} EPA e taxas sem denominador permanecem indisponíveis.</p>}
    <p className="obs-period">{d.observed.includedGameIds.length} jogo(s) com observação · {d.scope.population === 'OBSERVED_SAMPLE' ? 'amostra observada; não é total da temporada' : 'população declarada'} · semanas observadas {d.observed.actualWeeks.join(', ') || 'nenhuma'}</p>
    <div className="obs-numbers">{cards.map(card => <section key={card.key} className="obs-number"><h3>{card.label}</h3>
      <p className="obs-value">{card.formatted ?? (card.key !== 'volume' && zeroDenominator(card.key) ? 'Sem denominador' : 'Desconhecido')}</p>
      <p>{card.unit}</p><p className="obs-exact">{d.values[card.key] ? <>Exato: <code>{exact(d.values[card.key]!)}</code>{d.values[card.key]!.numerator === '0' && ' · zero conhecido'}</> : card.key !== 'volume' && zeroDenominator(card.key) ? 'Denominador zero; não equivale a valor zero.' : 'Sem observação disponível para este valor.'}</p>
    </section>)}</div>
    <p className="obs-scope">Flags desconhecidas são contexto do jogo inteiro, não contagem medida por time ou fundamento. Não somar entre grupos ou períodos sobrepostos.</p>
    <details className="obs-details"><summary>Contagens, fontes ausentes e motivos</summary>
      {t && <dl className="obs-counts">{Object.entries(t).map(([key, value]) => <div key={key}><dt>{({ eligibleN: 'Jogadas elegíveis do fundamento', epaN: 'Denominador EPA', epaSum: 'Soma EPA exata', successN: 'Sucessos (EPA > 0)', epaMissingN: 'EPA ausente', epaNonfiniteN: 'EPA não finito', generalEligibleN: 'Jogadas gerais do mesmo contexto', unknownFilterFlagsN: 'Flags desconhecidas · contexto dos jogos' } as Record<string, string>)[key]}</dt><dd>{value ?? 'Não disponível'}</dd></div>)}</dl>}
      <ul>{d.members.map(m => <li key={m.gameId}><code>{m.gameId}</code> · semana {m.week} · {m.sourceState === 'ABSENT' ? 'Fonte ausente; contagens desconhecidas' : `Fonte presente; ${m.statistics?.eligibleN} jogadas elegíveis; completude ${m.completeness}`}</li>)}</ul>
      <h3>Motivos estruturados</h3><ul>{d.limitations.map((m, i) => <li key={i}><code>{m.code}</code> · {m.subjectId}</li>)}</ul>
      <h3>Escopo das contagens</h3><p>unknownFilterFlagsN vem da auditoria de cada jogo inteiro. Sua repetição em outro fundamento não é outra medição.</p>
    </details>
    <details className="obs-details"><summary>Identidades para rastreabilidade</summary><dl>
      <dt>Bundle validado</dt><dd>{d.bundleId}</dd><dt>Observação original</dt><dd>{d.observationId}</dd><dt>DTO reduzido de transporte</dt><dd>{d.dtoId}</dd>
      </dl><p>O DTO é uma projeção de apresentação. Seu hash não é o hash dos bytes da observação original. A verificação do browser é estrutural e não autentica a origem.</p></details>
  </article>;
}

export default function Observations() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [choice, setChoice] = useState(() => saved());
  const [doc, setDoc] = useState<{ session: string; value: DTO } | null>(null);
  const [error, setError] = useState(''); const [catalogError, setCatalogError] = useState(''); const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true); const [docLoading, setDocLoading] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true; const controller = new AbortController();
    setLoading(true); setCatalogError('');
    observationCatalog(controller.signal).then(value => {
      if (!active) return; setCatalog(value);
      setChoice(previous => {
        const entry = value.bundles.find(e => e.entryId === previous.entryId);
        if (previous.entryId && (!entry || previous.observationId && !entry.observations.some(o => o.observationId === previous.observationId))) {
          setNotice('O bundle ou recorte anterior não existe nesta sessão. Selecione novamente; nenhum outro foi usado.');
          return { entryId: entry?.entryId ?? '', observationId: '' };
        }
        return previous;
      });
    }).catch(e => { if (active) { setCatalogError(failure(e)); setCatalog(null); } }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [reload]);
  const entry = catalog?.bundles.find(e => e.entryId === choice.entryId);
  const selected = entry?.observations.find(s => s.observationId === choice.observationId);
  useEffect(() => { try { sessionStorage.setItem('metrics-lab-choice', JSON.stringify(choice)); } catch { /* preference only */ } }, [choice]);
  useEffect(() => {
    let active = true; const controller = new AbortController(); setDoc(null); setError('');
    if (!catalog || !entry || !selected) { setDocLoading(false); return () => controller.abort(); }
    setDocLoading(true);
    observationDocument(catalog, entry, selected, controller.signal).then(value => { if (active) setDoc({ session: catalog.sessionId, value }); })
      .catch(e => { if (active) setError(failure(e)); }).finally(() => { if (active) setDocLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [catalog, entry, selected]);
  function choose(list: Summary[]) {
    const next = chooseAvailable(list, selected);
    setNotice(selected && next && period(selected) !== period(next) ? 'Período ajustado à combinação disponível. Confira temporada e fase.' : '');
    setChoice({ entryId: entry?.entryId, observationId: next?.observationId ?? '' });
  }
  const options = [...(entry?.observations ?? [])].sort(order);
  const visible = doc && doc.session === catalog?.sessionId && doc.value.entryId === choice.entryId && doc.value.observationId === choice.observationId ? doc.value : null;
  return <section className="observations-workspace" aria-label="Observações auditáveis">
    <div className="obs-session"><p>Conteúdo congelado na inicialização. Mudanças no disco exigem reiniciar e revalidar o laboratório; recarregar não lê o bundle atual.</p><button onClick={() => setReload(n => n + 1)} disabled={loading}>Recarregar catálogo da sessão</button></div>
    <div className="obs-selectors" aria-busy={loading || docLoading}>
      <label>Bundle<select aria-label="Bundle" value={choice.entryId ?? ''} disabled={loading} onChange={e => {
        const next = catalog?.bundles.find(x => x.entryId === e.target.value); setNotice('');
        setChoice({ entryId: next?.entryId ?? '', observationId: [...(next?.observations ?? [])].sort(order)[0]?.observationId ?? '' });
      }}><option value="">Selecione um bundle</option>{catalog?.bundles.map(e => <option key={e.entryId} value={e.entryId}>{e.label} · {e.dataKind === 'SYNTHETIC' ? 'SINTÉTICO' : 'ARQUIVO REAL'}{e.status === 'ERROR' ? ' · indisponível' : ''}</option>)}</select></label>
      {options.length > 0 && <>
        <label>Time<select aria-label="Time" value={selected?.subject.team ?? ''} onChange={e => choose(options.filter(s => s.subject.team === e.target.value ))}><option value="" disabled>Selecione</option>{[...new Set(options.map(s => s.subject.team))].sort().map(v => <option key={v}>{v}</option>)}</select></label>
        <label>Papel<select aria-label="Papel" value={selected?.subject.role ?? ''} onChange={e => choose(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === e.target.value))}><option value="" disabled>Selecione</option>{[...new Set(options.filter(s => s.subject.team === selected?.subject.team).map(s => s.subject.role))].map(v => <option key={v} value={v}>{roleName[v]}</option>)}</select></label>
        <label>Fundamento<select aria-label="Fundamento" value={selected?.subject.foundation ?? ''} onChange={e => choose(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role && s.subject.foundation === e.target.value))}><option value="" disabled>Selecione</option>{[...new Set(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role).map(s => s.subject.foundation))].map(v => <option key={v} value={v}>{foundationName[v]}</option>)}</select></label>
        <label className="obs-period-select">Período<select aria-label="Período" value={selected?.observationId ?? ''} onChange={e => setChoice({ entryId: entry?.entryId, observationId: e.target.value })}><option value="" disabled>Selecione</option>{options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role && s.subject.foundation === selected?.subject.foundation).map(s => <option key={s.observationId} value={s.observationId}>{period(s)} · {s.observationId.slice(7, 15)}</option>)}</select></label>
      </>}
    </div>
    <div className="notice" role="status">{loading ? 'Carregando catálogo…' : docLoading ? 'Carregando observação selecionada…' : notice}</div>
    {catalog?.errorCode && <p className="error" role="alert">{errorText[catalog.errorCode] ?? 'Catálogo indisponível. Verifique a configuração local.'}</p>}
    {entry?.errorCode && <p className="error" role="alert">{errorText[entry.errorCode] ?? 'Entrada indisponível; nenhum outro bundle foi usado.'}</p>}
    {catalogError && <p className="error" role="alert">{catalogError}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!loading && !catalog?.errorCode && !entry && <p>Selecione um bundle configurado para explorar uma observação por vez.</p>}
    {entry?.status === 'READY' && options.length === 0 && <p>Nenhuma observação disponível neste bundle.</p>}
    {visible && entry && <ObservationReading key={visible.observationId} d={visible} entry={entry}/>}
  </section>;
}
