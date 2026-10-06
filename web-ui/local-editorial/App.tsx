import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Database, FlaskConical, RefreshCw } from 'lucide-react';
import { catalog, generate, history, retrieve, sections } from './client';
import type { Attempt, Context, History, Result } from './client';

const message = (error: unknown) => error instanceof Error ? error.message : 'Falha na operação local.';
const date = (value: string) => new Date(value).toLocaleString('pt-BR');

export function Analysis({ result }: { result: Result }) {
  return <div className="analysis-grid">{sections.map(([key, title], index) => <section className={`analysis-section section-${index}`} key={key}>
    <div className="section-heading"><span>0{index + 1}</span><h3>{title}</h3></div>
    <p>{result.analysis[key]}</p>
  </section>)}</div>;
}

function Workspace({ context }: { context: Context }) {
  const [records, setRecords] = useState<History | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState('loading');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const inFlight = useRef(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    let cancelled = false;
    history(context.gameId).then(value => { if (!cancelled) setRecords(value); })
      .catch(e => { if (!cancelled) setError(message(e)); })
      .finally(() => { if (!cancelled) setBusy(''); });
    return () => { cancelled = true; alive.current = false; };
  }, [context.gameId]);
  async function action(kind: 'generate' | 'refresh' | 'open', attempt?: Attempt) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(kind); setError(''); setNotice('');
    try {
      if (kind !== 'refresh') {
        const value = kind === 'generate' ? await generate(context.gameId) : await retrieve(context.gameId, attempt!.attemptId);
        if (!alive.current) return;
        setResult(value);
        setNotice(kind === 'generate' ? 'Nova tentativa salva localmente.' : 'Tentativa recuperada dos arquivos locais.');
      }
      const value = await history(context.gameId);
      if (alive.current) setRecords(value);
    } catch (e) { if (alive.current) setError(message(e)); }
    finally { if (alive.current) setBusy(''); inFlight.current = false; }
  }
  const selected = records?.attempts.find(a => a.attemptId === result?.attemptId);
  return <>
    <div className="matchup-bar">
      <div><p className="eyebrow">TEMPORADA {context.season} <span> / </span> SEMANA {context.week} <span> / </span> {context.phase}</p>
        <h2>{context.awayTeam} <span>@</span> {context.homeTeam}</h2>
        <p className="muted">Contexto congelado · corte informado: {context.asOfDate || 'não informado'}</p></div>
      <button className="primary" disabled={!!busy} onClick={() => void action('generate')}>
        {busy === 'generate' ? 'Gerando análise…' : 'Gerar análise local'}<ArrowRight size={18} aria-hidden="true"/>
      </button>
    </div>
    <p className="scope-note">Análise descritiva por regras locais. Não estima vencedor. Cada geração cria uma nova tentativa, sem aprovação ou publicação.</p>
    <div role="status" className="notice">{notice}</div>
    {error && <div role="alert" className="error">{error}</div>}
    <div className="workspace-grid" aria-busy={!!busy}>
      <div className="reading-panel">
        <div className="panel-heading"><h3>Leitura do confronto</h3><span className="tag">NÃO PUBLICADO</span></div>
        {result ? <><Analysis result={result}/>
          {selected && selected.sourceSha256 !== context.sourceSha256 && <p className="error">Esta tentativa usa uma versão anterior do contexto.</p>}
          <details className="audit"><summary>Identificação da tentativa</summary><dl>
            <dt>ID</dt><dd>{result.attemptId}</dd><dt>Identidade do resultado</dt><dd>{result.resultIdentity}</dd>
            <dt>Modo</dt><dd>Regras locais · validação mecânica concluída</dd>
            <dt>Publicação</dt><dd>Não aprovada</dd>
          </dl></details>
        </> : <div className="empty"><FlaskConical size={32} aria-hidden="true"/><h3>O contexto está pronto.</h3>
          <p>Gere uma análise para examinar os quatro blocos, ou abra uma tentativa do histórico.</p>
          <span>Sem chamadas a modelos externos</span></div>}
      </div>
      <aside className="history-panel"><div className="panel-heading"><h3>Tentativas salvas</h3>
        <button className="icon-button" disabled={!!busy} onClick={() => void action('refresh')} aria-label="Atualizar histórico"><RefreshCw size={17} aria-hidden="true"/></button></div>
        <p className="muted history-note">Arquivos locais deste confronto. Versões anteriores são preservadas.</p>
        {!records ? <p className="history-note">{error ? 'Histórico indisponível.' : 'Carregando histórico…'}</p> : <>
          {records.unavailableInStore > 0 && <p className="error">{records.unavailableInStore} entrada(s) incompleta(s) ou indisponível(is) no diretório de resultados.</p>}
          {records.attempts.length === 0 && <p className="history-note">Nenhuma tentativa concluída para este contexto.</p>}
          <ol className="attempts">{records.attempts.map((a, i) => <li key={a.attemptId}>
            <button disabled={!!busy} aria-pressed={result?.attemptId === a.attemptId} onClick={() => void action('open', a)}>
              <span className="attempt-title">Tentativa {records.attempts.length - i}{result?.attemptId === a.attemptId && <Check size={16} aria-hidden="true"/>}</span>
              <time dateTime={a.startedAt}>{date(a.startedAt)}</time><code>{a.attemptId.slice(0, 8)}</code>
              {a.sourceSha256 !== context.sourceSha256 && <span>Contexto anterior</span>}
            </button></li>)}</ol>
        </>}
      </aside>
    </div>
  </>;
}

export default function App() {
  const [contexts, setContexts] = useState<Context[]>([]);
  const [selected, setSelected] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let cancelled = false;
    catalog().then(value => {
      if (cancelled) return;
      setContexts(value); setSelected(value[0]?.gameId ?? ''); setLoading(false);
    }).catch(e => { if (!cancelled) { setError(message(e)); setLoading(false); } });
    return () => { cancelled = true; };
  }, [reload]);
  const context = contexts.find(c => c.gameId === selected);
  return <><a className="skip" href="#workspace">Pular para o laboratório</a>
    <header className="topbar"><div className="brand">NFL <strong>SIDELINE</strong><span> / EDITORIAL</span></div><span className="local-badge"><span/>AMBIENTE LOCAL</span></header>
    <main id="workspace"><div className="page-heading"><div><p className="eyebrow">LABORATÓRIO EDITORIAL</p><h1>Do contexto à análise.</h1>
      <p className="muted">Explore a geração offline e compare tentativas preservadas.</p></div><Database size={30} aria-hidden="true"/></div>
      <div className="context-picker"><label htmlFor="context">Contexto de avaliação</label>
        <select id="context" value={selected} disabled={loading || !contexts.length} onChange={e => setSelected(e.target.value)}>
          {!contexts.length && <option>{loading ? 'Carregando catálogo…' : 'Nenhum contexto disponível'}</option>}
          {contexts.map(c => <option key={c.gameId} value={c.gameId}>{c.awayTeam} @ {c.homeTeam} · {c.season} · Semana {c.week} · {c.gameId}</option>)}
        </select><span className="muted">{contexts.length} contextos disponíveis</span>
      </div>
      {error && <div role="alert" className="error">{error} <button onClick={() => { setError(''); setLoading(true); setReload(n => n + 1); }}>Reconectar</button></div>}
      {!loading && !error && !context && <p>O catálogo não contém contextos para geração.</p>}
      {context && <Workspace key={context.gameId} context={context}/>}
      <footer>Regras locais · Dados congelados · Sem publicação <span>A validação mecânica não comprova qualidade editorial.</span></footer>
    </main></>;
}
