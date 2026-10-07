import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Database, FlaskConical, RefreshCw } from 'lucide-react';
import { VisualAnalysis } from '../src/features/analysis-visual/VisualAnalysis';
import { validateDocument } from '../src/features/analysis-visual/validate';
import type { VisualAnalysisDocument } from '../src/features/analysis-visual/model';
import { catalog, generate, history, retrieve, retrieveVisual, sections, VisualUnavailableError } from './client';
import type { Attempt, Context, History, Result } from './client';

const fixtureFiles = import.meta.glob('../../contracts/visual-analysis/v1/fixtures/valid/*.json', { eager: true, import: 'default' });
const fixtures = Object.fromEntries(Object.entries(fixtureFiles).map(([path, value]) => [path.split('/').pop()!.replace('.json', ''), value]));
const fixtureNames = Object.keys(fixtures).sort();
const message = (error: unknown) => error instanceof Error ? error.message : 'Falha na operação local.';
const date = (value: string) => new Date(value).toLocaleString('pt-BR');

export function Analysis({ result }: { result: Result }) {
  return <div className="analysis-grid">{sections.map(([key, title], index) => <section className={`analysis-section section-${index}`} key={key}>
    <div className="section-heading"><span>0{index + 1}</span><h3>{title}</h3></div>
    <p>{result.analysis[key]}</p>
  </section>)}</div>;
}

function FixtureWorkspace() {
  const [name, setName] = useState('complete-matchup');
  let document: VisualAnalysisDocument | null = null;
  let error = '';
  try { document = validateDocument(fixtures[name], 'fixture'); } catch (cause) { error = message(cause); }
  return <section className="fixture-workspace"><div className="fixture-banner" role="status">
    <strong>FIXTURE SINTÉTICA · CONTRATO E1</strong><span>AAA/BBB são fictícios. Esta prévia não foi gerada pelo motor e não integra o catálogo ou histórico reais.</span></div>
    <div className="fixture-picker"><label htmlFor="fixture">Estado de demonstração</label><select id="fixture" value={name} onChange={event => setName(event.target.value)}>
      {fixtureNames.map(item => <option key={item} value={item}>{item}</option>)}
    </select></div>
    {error && <div className="error" role="alert">{error}</div>}
    {document && <VisualAnalysis document={document}/>}
  </section>;
}

function Workspace({ context }: { context: Context }) {
  const [records, setRecords] = useState<History | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [visual, setVisual] = useState<VisualAnalysisDocument | null>(null);
  const [visualStatus, setVisualStatus] = useState<'idle' | 'loading' | 'legacy' | 'invalid' | 'error'>('idle');
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
        if (attempt && value.resultIdentity !== attempt.resultIdentity) throw new Error('Identidade da tentativa diferente do histórico.');
        setResult(value); setVisual(null); setVisualStatus('loading');
        setNotice(kind === 'generate' ? 'Nova tentativa salva localmente.' : 'Tentativa recuperada dos arquivos locais.');
        try {
          const view = await retrieveVisual(context, value);
          if (!alive.current) return;
          setVisual(view.document); setVisualStatus('idle');
        } catch (cause) {
          if (!alive.current) return;
          if (cause instanceof VisualUnavailableError) setVisualStatus('legacy');
          else {
            setVisualStatus(message(cause).includes('Documento visual incompatível') ? 'invalid' : 'error');
            setError(message(cause));
          }
        }
      }
      const value = await history(context.gameId);
      if (alive.current) setRecords(value);
    } catch (cause) { if (alive.current) setError(message(cause)); }
    finally { if (alive.current) setBusy(''); inFlight.current = false; }
  }
  const selected = records?.attempts.find(item => item.attemptId === result?.attemptId);
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
          <ol className="attempts">{records.attempts.map((item, index) => <li key={item.attemptId}>
            <button disabled={!!busy} aria-pressed={result?.attemptId === item.attemptId} onClick={() => void action('open', item)}>
              <span className="attempt-title">Tentativa {records.attempts.length - index}{result?.attemptId === item.attemptId && <Check size={16} aria-hidden="true"/>}</span>
              <time dateTime={item.startedAt}>{date(item.startedAt)}</time><code>{item.attemptId.slice(0, 8)}</code>
              {item.sourceSha256 !== context.sourceSha256 && <span>Contexto anterior</span>}
            </button></li>)}</ol>
        </>}
      </aside>
    </div>
    {result && <div className="visual-status" role="status">{visualStatus === 'loading' && 'Consultando documento visual desta tentativa…'}
      {visualStatus === 'legacy' && 'Compatibilidade: esta tentativa legada v3 não possui documento visual. A leitura textual acima permanece disponível.'}
      {visualStatus === 'invalid' && 'Documento visual inválido. A leitura textual acima foi preservada; o visual não será exibido.'}
      {visualStatus === 'error' && 'Não foi possível recuperar o documento visual. A leitura textual permanece disponível; abra a tentativa novamente para consultar.'}
    </div>}
    {visual && <VisualAnalysis document={visual}/>}
  </>;
}

export default function App() {
  const [mode, setMode] = useState<'real' | 'fixture'>('real');
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
    }).catch(cause => { if (!cancelled) { setError(message(cause)); setLoading(false); } });
    return () => { cancelled = true; };
  }, [reload]);
  const context = contexts.find(item => item.gameId === selected);
  return <><a className="skip" href="#workspace">Pular para o laboratório</a>
    <header className="topbar"><div className="brand">NFL <strong>SIDELINE</strong><span> / EDITORIAL</span></div><span className="local-badge"><span/>AMBIENTE LOCAL</span></header>
    <main id="workspace"><div className="page-heading"><div><p className="eyebrow">LABORATÓRIO EDITORIAL</p><h1>Do contexto à análise.</h1>
      <p className="muted">Explore a geração offline e as tentativas preservadas.</p></div><Database size={30} aria-hidden="true"/></div>
      <div className="mode-picker"><label htmlFor="mode">Fonte da leitura</label><select id="mode" value={mode} onChange={event => setMode(event.target.value as 'real' | 'fixture')}>
        <option value="real">API local · resultados reais</option><option value="fixture">Fixtures sintéticas · prévia do contrato</option>
      </select></div>
      {mode === 'fixture' ? <FixtureWorkspace/> : <>
        <div className="context-picker"><label htmlFor="context">Contexto de avaliação</label>
          <select id="context" value={selected} disabled={loading || !contexts.length} onChange={event => setSelected(event.target.value)}>
            {!contexts.length && <option>{loading ? 'Carregando catálogo…' : 'Nenhum contexto disponível'}</option>}
            {contexts.map(item => <option key={item.gameId} value={item.gameId}>{item.awayTeam} @ {item.homeTeam} · {item.season} · Semana {item.week} · {item.gameId}</option>)}
          </select><span className="muted">{contexts.length} contextos disponíveis</span>
        </div>
        {error && <div role="alert" className="error">{error} <button onClick={() => { setError(''); setLoading(true); setReload(n => n + 1); }}>Reconectar</button></div>}
        {!loading && !error && !context && <p>O catálogo não contém contextos para geração.</p>}
        {context && <Workspace key={context.gameId} context={context}/>}
      </>}
      <footer>Regras locais · Dados congelados · Sem publicação <span>A validação mecânica não comprova qualidade editorial.</span></footer>
    </main></>;
}
