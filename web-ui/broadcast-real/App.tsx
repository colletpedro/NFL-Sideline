import { useEffect, useState } from 'react';
import type { Catalog, DTO, Summary } from '../local-editorial/observations/model';
import { errorText, observationCatalog, observationDocument } from '../local-editorial/observations/client';
import { chooseAvailable, order, period } from '../local-editorial/observations/selection';
import { Reading } from './Reading';
import { teamIdentity } from './identity';

type Choice = { entryId?: string; observationId?: string };
const storageKey = 'broadcast-real-choice-v1';
function saved(): Choice {
  const q = new URLSearchParams(window.location.search);
  if (q.has('entry') || q.has('observation')) return { entryId: q.get('entry') ?? '', observationId: q.get('observation') ?? '' };
  try {
    const raw = sessionStorage.getItem(storageKey);
    if (raw === null) return {};
    const value = JSON.parse(raw) as Choice | null;
    return value && typeof value === 'object' && typeof value.entryId === 'string' && typeof value.observationId === 'string' ? { entryId: value.entryId, observationId: value.observationId } : { entryId: '', observationId: '' };
  } catch { return { entryId: '', observationId: '' }; }
}
const failure = (e: unknown) => e instanceof Error ? e.message : 'Falha na leitura local.';
const roles = { off: 'Ataque', def: 'Defesa' };
const foundations = { general: 'Passe + corrida', classified_pass: 'Passe', classified_rush: 'Corrida' };

export default function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [choice, setChoice] = useState<Choice>(saved);
  const [document, setDocument] = useState<{ session: string; value: DTO } | null>(null);
  const [catalogError, setCatalogError] = useState(''), [docError, setDocError] = useState('');
  const [loading, setLoading] = useState(true), [docLoading, setDocLoading] = useState(false);
  const [reload, setReload] = useState(0), [notice, setNotice] = useState(''), [filtersOpen, setFiltersOpen] = useState(false);
  useEffect(() => {
    let active = true; const controller = new AbortController();
    setLoading(true); setCatalog(null); setCatalogError('');
    observationCatalog(controller.signal).then(c => {
      if (!active) return;
      setCatalog(c);
      setChoice(old => {
        const e = c.bundles.find(e => e.entryId === old.entryId && e.dataKind === 'REAL_ARCHIVE');
        if (old.entryId !== undefined || old.observationId !== undefined) {
          if (!e || !e.observations.some(s => s.observationId === old.observationId)) {
            setNotice('A seleção anterior não está disponível. Nenhum outro arquivo ou recorte foi usado.'); setFiltersOpen(true);
            return { entryId: e?.entryId ?? '', observationId: '' };
          }
          return old;
        }
        const entries = c.bundles.filter(e => e.status === 'READY' && e.dataKind === 'REAL_ARCHIVE');
        if (entries.length !== 1) { setFiltersOpen(true); return old; }
        const options = [...entries[0].observations].sort(order);
        const first = options.find(s => s.subject.role === 'off' && s.subject.foundation === 'general' && s.request.period.weeks.length > 1) ?? options[0];
        return { entryId: entries[0].entryId, observationId: first?.observationId ?? '' };
      });
    }).catch(e => { if (active) setCatalogError(failure(e)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [reload]);
  const entry = catalog?.bundles.find(e => e.entryId === choice.entryId && e.dataKind === 'REAL_ARCHIVE');
  const selected = entry?.observations.find(s => s.observationId === choice.observationId);
  useEffect(() => {
    if (choice.entryId === undefined) return;
    try { sessionStorage.setItem(storageKey, JSON.stringify(choice)); } catch { /* preference only */ }
    const url = new URL(window.location.href);
    url.searchParams.set('entry', choice.entryId ?? ''); url.searchParams.set('observation', choice.observationId ?? '');
    window.history.replaceState(null, '', url);
  }, [choice]);
  useEffect(() => {
    let active = true; const controller = new AbortController();
    setDocument(null); setDocError('');
    if (!catalog || !entry || !selected) { setDocLoading(false); return () => controller.abort(); }
    setDocLoading(true);
    observationDocument(catalog, entry, selected, controller.signal).then(value => { if (active) setDocument({ session: catalog.sessionId, value }); })
      .catch(e => { if (active) setDocError(failure(e)); }).finally(() => { if (active) setDocLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [catalog, entry, selected]);
  const visible = document && document.session === catalog?.sessionId && document.value.entryId === choice.entryId && document.value.observationId === choice.observationId ? document.value : null;
  const options = [...(entry?.observations ?? [])].sort(order);
  function choose(list: Summary[]) {
    const next = chooseAvailable(list, selected);
    setNotice(selected && next && period(next) !== period(selected) ? 'Período ajustado à combinação disponível. Confira temporada e fase.' : '');
    setChoice({ entryId: entry?.entryId, observationId: next?.observationId ?? '' });
  }
  const unavailableEntry = catalog?.bundles.find(e => e.dataKind === 'REAL_ARCHIVE' && e.status === 'ERROR');
  const noReadyArchive = catalog && !catalog.bundles.some(e => e.dataKind === 'REAL_ARCHIVE' && e.status === 'READY');
  const error = catalogError || (noReadyArchive && unavailableEntry?.errorCode ? errorText[unavailableEntry.errorCode] : '') || catalog?.errorCode && errorText[catalog.errorCode] || entry?.errorCode && errorText[entry.errorCode] || docError;
  return <>
    <a href="#real-main" className="skip-link">Ir à leitura</a>
    <header className="site-header real-header"><div className="real-header-inner"><a className="brand" href="/">NFL <strong>SIDELINE</strong><i className="brand-rule"/></a><span className="real-header-title">Leitura do arquivo</span><p>Local · arquivo real<br/><span>Uma observação por vez</span></p></div></header>
    <main id="real-main" className="real-page">
      <div className="real-intro"><div><p>Acervo preservado</p><h2>O jogo, nos dados observados.</h2></div><span>Leitura de arquivo real<br/>Sem atualização ao vivo</span></div>
      <section className="real-selection" aria-label="Seleção da observação"><div className="real-selection-bar"><p>{selected ? `${selected.subject.team} · ${roles[selected.subject.role]} · ${foundations[selected.subject.foundation]}` : 'Escolha uma observação do catálogo'}<span>{selected ? period(selected) : ''}</span></p><button onClick={() => setFiltersOpen(v => !v)} aria-expanded={filtersOpen} aria-controls="real-filters">{filtersOpen ? 'Fechar seleção' : 'Alterar recorte'}</button></div>
        <div id="real-filters" hidden={!filtersOpen} className="real-filters">
          <label>Arquivo<select aria-label="Arquivo" value={entry?.entryId ?? ''} onChange={e => { setNotice('Selecione um recorte deste arquivo.'); setChoice({ entryId: e.target.value, observationId: '' }); }}><option value="">Selecione</option>{catalog?.bundles.filter(e => e.dataKind === 'REAL_ARCHIVE').map(e => <option key={e.entryId} value={e.entryId} disabled={e.status !== 'READY'}>{e.label}</option>)}</select></label>
          {options.length > 0 && <>
            <label>Time<select aria-label="Time" value={selected?.subject.team ?? ''} onChange={e => choose(options.filter(s => s.subject.team === e.target.value))}><option value="" disabled>Selecione</option>{[...new Set(options.map(s => s.subject.team))].map(v => <option key={v} value={v}>{teamIdentity(v).city} · {v}</option>)}</select></label>
            <label>Papel<select aria-label="Papel" value={selected?.subject.role ?? ''} disabled={!selected} onChange={e => choose(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === e.target.value))}><option value="" disabled>Selecione</option>{[...new Set(options.filter(s => s.subject.team === selected?.subject.team).map(s => s.subject.role))].map(v => <option key={v} value={v}>{roles[v]}</option>)}</select></label>
            <label>Fundamento<select aria-label="Fundamento" value={selected?.subject.foundation ?? ''} disabled={!selected} onChange={e => choose(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role && s.subject.foundation === e.target.value))}><option value="" disabled>Selecione</option>{[...new Set(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role).map(s => s.subject.foundation))].map(v => <option key={v} value={v}>{foundations[v]}</option>)}</select></label>
            <label>Período<select aria-label="Período" value={selected ? period(selected) : ''} disabled={!selected} onChange={e => choose(options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role && s.subject.foundation === selected?.subject.foundation && period(s) === e.target.value))}><option value="" disabled>Selecione</option>{options.filter(s => s.subject.team === selected?.subject.team && s.subject.role === selected?.subject.role && s.subject.foundation === selected?.subject.foundation).map(s => <option key={s.observationId} value={period(s)}>{period(s)}</option>)}</select></label>
          </>}
        </div>
        {notice && <p className="real-notice" role="status">{notice}</p>}
      </section>
      <div aria-live="polite" aria-atomic="true" className="sr-only">{visible ? `Leitura carregada: ${visible.subject.team}, ${roles[visible.subject.role]}, ${foundations[visible.subject.foundation]}, ${period(visible)}.` : ''}</div>
      {loading || docLoading ? <section className="real-state" role="status"><h2>Preparando a leitura…</h2><p>{loading ? 'Carregando o catálogo validado.' : 'Abrindo a observação selecionada.'}</p></section> : error ? <section className="real-state" role="alert"><h2>Não foi possível abrir a leitura.</h2><p>{error}</p><button onClick={() => setReload(v => v + 1)}>Recarregar catálogo</button></section> : visible && entry ? <Reading key={visible.observationId} d={visible} entry={entry}/> : <section className="real-state"><h2>Selecione um recorte disponível.</h2><p>Somente arquivos reais validados aparecem nesta entrada.</p><button onClick={() => setFiltersOpen(true)}>Abrir seleção</button></section>}
    </main><footer className="real-footer"><span className="brand">NFL <strong>SIDELINE</strong></span><p>Futebol americano, sob outra perspectiva.</p><span>Arquivo observado · sem previsão ou comparação entre times</span></footer>
  </>;
}
