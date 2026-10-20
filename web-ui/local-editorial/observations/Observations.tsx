import { useEffect, useState } from 'react';
import type { Catalog, DTO, Summary } from './model';
import { errorText, observationCatalog, observationDocument } from './client';
import { ObservationReading } from './ObservationReading';
export { ObservationReading } from './ObservationReading';
import { readingPeriod, foundationLabel } from './presentation';
import { chooseAvailable, order, period } from './selection';
import './observations.css';
import { DirectionReading } from './DirectionReading';
import { type Direction, directionNames } from './directionData';
import './directions.css';
const roleName = { off: 'Ataque', def: 'Defesa' };
const foundationName = { general: 'Passe + corrida', classified_pass: 'Passe', classified_rush: 'Corrida' };
const failure = (cause: unknown) => cause instanceof Error ? cause.message : 'Falha na leitura local.';
function saved() { try { return JSON.parse(sessionStorage.getItem('metrics-lab-choice') ?? '{}') as { entryId?: string; observationId?: string }; } catch { return {}; } }

export default function Observations() {
  const [direction, setDirection] = useState<Direction>(() => { try { const v = sessionStorage.getItem('metrics-lab-direction'); return v === 'B' || v === 'C' || v === 'original' ? v : 'A'; } catch { return 'A'; } });
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [choice, setChoice] = useState(() => saved());
  const [doc, setDoc] = useState<{ session: string; value: DTO } | null>(null);
  const [error, setError] = useState(''); const [catalogError, setCatalogError] = useState(''); const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true); const [docLoading, setDocLoading] = useState(false);
  const [reload, setReload] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  useEffect(() => {
    let active = true; const controller = new AbortController();
    setLoading(true); setCatalogError('');
    observationCatalog(controller.signal).then(value => {
      if (!active) return; setCatalog(value);
      setChoice(previous => {
        const entry = value.bundles.find(e => e.entryId === previous.entryId);
        if (previous.entryId && (!entry || previous.observationId && !entry.observations.some(o => o.observationId === previous.observationId))) {
          setFiltersOpen(true);
          setNotice('O arquivo ou recorte anterior não existe nesta sessão. Selecione novamente; nenhum outro foi usado.');
          return { entryId: entry?.entryId ?? '', observationId: '' };
        }
        if (previous.entryId === undefined && previous.observationId === undefined && value.bundles.length === 1 && value.bundles[0].status === 'READY') {
          const available = [...value.bundles[0].observations].sort(order);
          const first = available.find(o => o.subject.team === 'BAL' && o.subject.role === 'off' && o.subject.foundation === 'general' && o.request.season === 2026 && o.request.period.weeks.join(',') === '1,2') ?? available[0];
          return { entryId: value.bundles[0].entryId, observationId: first?.observationId ?? '' };
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
  const controls = <div className="direction-controls">
    <div className="obs-toolbar"><p>{direction === 'original' ? 'Uma amostra por vez' : 'Seu recorte'} <span> / {options.length} opções</span></p>{options.length > 0 && <button aria-expanded={filtersOpen} aria-controls="obs-filters" onClick={() => setFiltersOpen(v => !v)}>{filtersOpen ? 'Fechar seleção' : 'Alterar recorte'}</button>}</div>
    <div id="obs-filters" className="obs-selectors" hidden={!filtersOpen || options.length === 0} aria-busy={loading || docLoading}>
      {options.length > 0 && <>
        <label>Time<select aria-label="Time" value={selected?.subject.team ?? ''} onChange={e => choose(options.filter(s => s.subject.team === e.target.value ))}><option value="" disabled>Selecione</option>{[...new Set(options.map(s => s.subject.team))].sort().map(v => <option key={v}>{v}</option>)}</select></label>
        <label>Lado da bola<select aria-label="Lado da bola" value={selected?.subject.role ?? ''} onChange={e => choose(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === e.target.value))}><option value="" disabled>Selecione</option>{[...new Set(options.filter(s => s.subject.team === selected?.subject.team).map(s => s.subject.role))].map(v => <option key={v} value={v}>{roleName[v]}</option>)}</select></label>
        <label>Fundamento<select aria-label="Fundamento" value={selected?.subject.foundation ?? ''} onChange={e => choose(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role && s.subject.foundation === e.target.value))}><option value="" disabled>Selecione</option>{[...new Set(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role).map(s => s.subject.foundation))].map(v => <option key={v} value={v}>{foundationName[v]}</option>)}</select></label>
        <label className="obs-period-select">Período<select aria-label="Período" value={selected?.observationId ?? ''} onChange={e => setChoice({ entryId: entry?.entryId, observationId: e.target.value })}><option value="" disabled>Selecione</option>{options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role && s.subject.foundation === selected?.subject.foundation).map(s => <option key={s.observationId} value={s.observationId}>{readingPeriod(s)}</option>)}</select></label>
      </>}
    </div>
    {direction !== 'original' && selected && <div className="quick-controls">
      <div className="role-switch" role="group" aria-label="Lado da bola rápido">{(['off','def'] as const).filter(r => options.some(o => o.subject.team === selected.subject.team && o.subject.role === r)).map(r => <button key={r} aria-pressed={selected.subject.role === r} onClick={() => choose(options.filter(o => o.subject.team === selected.subject.team && o.subject.role === r))}>{roleName[r]}</button>)}</div>
      <div className="foundation-switch" role="group" aria-label="Fundamento rápido">{(['general','classified_pass','classified_rush'] as const).filter(f => options.some(o => o.subject.team === selected.subject.team && o.subject.role === selected.subject.role && o.subject.foundation === f)).map(f => <button key={f} aria-pressed={selected.subject.foundation === f} onClick={() => choose(options.filter(o => o.subject.team === selected.subject.team && o.subject.role === selected.subject.role && o.subject.foundation === f))}>{foundationName[f]}</button>)}</div>
    </div>}
  </div>;
  return <section className={`observations-workspace direction-workspace direction-${direction}`} aria-label="Observações auditáveis">
    <nav className="proposal-picker" aria-label="Proposta visual"><div><strong>Laboratório de direções</strong><span>Mesmo recorte. Três experiências.</span></div><div className="proposal-options">{(['A','B','C'] as const).map(v => <button key={v} aria-pressed={direction === v} onClick={() => { setDirection(v); try { sessionStorage.setItem('metrics-lab-direction', v); } catch { /* preference only */ } }}><b>{v}</b><span>{directionNames[v]}</span></button>)}</div><button className="original-proposal" aria-pressed={direction === 'original'} onClick={() => { setDirection('original'); try { sessionStorage.setItem('metrics-lab-direction', 'original'); } catch { /* preference only */ } }}>E5c-4 anterior</button></nav>
    {(direction === 'original' || !visible) && controls}
    <div className="notice" role="status">{notice}</div>
    {(loading || docLoading || error) && <div className="obs-loading" role={error ? undefined : 'status'} aria-busy={loading || docLoading}>
      <h2>{selected ? `${selected.subject.team} · ${roleName[selected.subject.role]} / ${foundationLabel(selected.subject)}` : 'Arquivo de jogadas'}</h2>
      {selected && <p>{readingPeriod(selected)}</p>}
      <p>{loading ? 'Carregando catálogo…' : docLoading ? 'Carregando observação selecionada…' : 'Não foi possível abrir esta observação.'}</p>
    </div>}
    {catalog?.errorCode && <p className="error" role="alert">{errorText[catalog.errorCode] ?? 'Catálogo indisponível. Verifique a configuração local.'}</p>}
    {entry?.errorCode && <p className="error" role="alert">{errorText[entry.errorCode] ?? 'Entrada indisponível; nenhum outro bundle foi usado.'}</p>}
    {catalogError && <p className="error" role="alert">{catalogError}</p>}
    {error && <div className="error" role="alert"><p>{error}</p><button onClick={() => setReload(n => n + 1)}>Recarregar catálogo da sessão</button></div>}
    {!loading && !catalog?.errorCode && !entry && <div className="obs-empty"><h2>Escolha um arquivo para começar.</h2><p>Abra “Arquivo e sessão” abaixo e selecione uma fonte. Nenhum recorte foi carregado.</p></div>}
    {entry?.status === 'READY' && options.length === 0 && <p>Nenhuma observação disponível neste arquivo.</p>}
    {visible && entry && (direction === 'original' ? <ObservationReading key={visible.observationId} d={visible} entry={entry}/> : <DirectionReading key={visible.observationId} d={visible} entry={entry} direction={direction} controls={controls}/>)}
    <details className="obs-details obs-session"><summary>Arquivo e sessão <span>Trocar fonte ou recarregar catálogo</span></summary>
      <label>Arquivo<select aria-label="Arquivo" value={choice.entryId ?? ''} disabled={loading} onChange={e => {
        const next = catalog?.bundles.find(x => x.entryId === e.target.value); setNotice('');
        setChoice({ entryId: next?.entryId ?? '', observationId: [...(next?.observations ?? [])].sort(order)[0]?.observationId ?? '' });
      }}><option value="">Selecione um arquivo</option>{catalog?.bundles.map(e => <option key={e.entryId} value={e.entryId}>{e.label} · {e.dataKind === 'SYNTHETIC' ? 'SINTÉTICO' : 'ARQUIVO REAL'}{e.status === 'ERROR' ? ' · indisponível' : ''}</option>)}</select></label>
      <p>Conteúdo validado e congelado na inicialização. Mudanças no disco exigem reiniciar o laboratório; recarregar o catálogo mantém os mesmos dados da sessão.</p><button onClick={() => setReload(n => n + 1)} disabled={loading}>Recarregar catálogo da sessão</button>
    </details>
  </section>;
}
