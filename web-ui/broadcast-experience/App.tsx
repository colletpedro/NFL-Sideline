import { useEffect, useRef } from 'react';
import { ArrowLeft, ArrowUpRight, ChevronDown, ChevronRight } from 'lucide-react';
import { BrowserRouter, Link, Route, Routes, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { format, games, periodLabels, playLabels, summarize, teams, type Game, type Period, type PlayType } from './fixtures';
import { gameForId, matchupHref, navigationContext, readState } from './state';
import { readSlice } from './editorial';
import { ExploreLink, GameLink, MatchupBand, YardagePreview } from './ui';
import { EfficiencyChart, ScoreTimeline, SuccessChart } from './Charts';
import { AnalysisDetails, SliceReading, StatSummary } from './AnalysisReading';

function Header() {
  const location = useLocation(), nav = navigationContext(location.pathname, location.search);
  return <><a className="skip-link" href="#main">Pular para o conteúdo</a><header className="site-header"><div className="header-inner">
    <Link className="brand" to={nav.centralHref} aria-label="NFL Sideline, central da rodada">NFL <strong>SIDELINE</strong><span className="brand-rule" aria-hidden="true"/></Link>
    <nav aria-label="Principal"><Link to={nav.centralHref} aria-current={location.pathname === '/' ? 'page' : undefined}>Central da rodada</Link><Link to={nav.analysisHref} aria-current={nav.current ? 'page' : undefined}>Mesa de análise</Link></nav>
    <span className="demo-notice">Demonstração · dados simulados</span>
  </div></header></>;
}
function PageFocus() {
  const { pathname } = useLocation(), first = useRef(true);
  useEffect(() => {
    document.title = pathname === '/' ? 'NFL Sideline · Central da rodada' : 'NFL Sideline · Mesa de análise';
    if (first.current) { first.current = false; return; }
    window.scrollTo(0, 0);
    document.getElementById('main')?.focus({ preventScroll: true });
  }, [pathname]);
  return null;
}
function Footer() {
  return <footer className="site-footer"><span className="footer-brand">NFL <b>SIDELINE</b></span><p>Futebol americano, sob outra perspectiva.</p><span>Experimento de interface · edição demonstrativa</span></footer>;
}
function Archive({ active, round }: { active: Game; round: number }) {
  const archived = [6, 7, 8].filter(r => r !== active.round).map(r => games.find(g => g.round === r)!);
  return <section className="archive" aria-labelledby="archive-title"><div className="archive-heading"><h2 id="archive-title">Em outras rodadas</h2><span>Arquivo da demonstração</span></div><div className="archive-games">{archived.map(g => <GameLink key={g.id} game={g} round={round}/>)}</div></section>;
}
function RoundGames({ active, round }: { active: Game; round: number }) {
  const selected = games.filter(g => g.round === active.round), others = selected.filter(g => g.id !== active.id);
  if (!others.length) return null;
  return <section className="archive round-games" aria-labelledby="round-games-title"><div className="archive-heading"><h2 id="round-games-title">Mais jogos da rodada {active.round}</h2><span>{selected.length} jogos · {selected.filter(g => g.status === 'final').length} encerrados · {selected.filter(g => g.status === 'pregame').length} pré-jogo</span></div><div className="archive-games">{others.map(g => <GameLink key={g.id} game={g} round={round}/>)}</div></section>;
}
function Home() {
  const [params, setParams] = useSearchParams(), { round } = readState(params.toString());
  const game = games.find(g => g.round === round) ?? games[0], [a, b] = game.sides.map(s => teams[s.team]);
  const pass = summarize(game.sides[0], 'game', 'pass'), rush = summarize(game.sides[0], 'game', 'rush'), reading = readSlice(game, 'game', 'all');
  return <main id="main" tabIndex={-1} className="page home-page"><div className="edition-heading"><div><span className="section-kicker">Edição de demonstração</span><h1>CENTRAL DA RODADA</h1></div><div className="round-picker" role="group" aria-label="Selecionar rodada"><span>Rodada</span>{[6, 7, 8].map(r => <button key={r} aria-pressed={round === r} onClick={() => setParams({ round: String(r) })}>{r}</button>)}</div></div>
    <section className="opening" aria-labelledby="opening-headline"><div className="opening-main"><div className="segment-header"><span>Confronto em foco</span><span>Rodada {game.round} <span className="header-dot">/</span> {game.venue}</span></div><MatchupBand game={game} home/>
      <div className="opening-story"><span className="section-kicker">{a.city} × {b.city}</span><h2 id="opening-headline">{game.title}</h2><ExploreLink to={matchupHref(game, round)}>Explorar confronto</ExploreLink><p className="opening-deck">{game.deck}</p><div className="opening-bottom"><div className="opening-fact"><strong>{pass ? format(pass.yards) : '—'}</strong><span>jardas no passe<br/>de {a.city}</span></div><div className="opening-fact"><strong>{rush ? format(rush.yards) : '—'}</strong><span>jardas em corrida<br/>de {a.city}</span></div></div></div></div>
      <aside className="opening-aside"><span className="section-kicker">Leitura dos ataques · jogo completo</span><h2>{reading.title}</h2><p>{reading.text}</p><YardagePreview game={game}/><Link className="text-link" to={`${matchupHref(game, round)}&play=pass`}>Explorar o passe<ArrowUpRight size={18} aria-hidden="true"/></Link><div className="aside-bottom"><span>Recortes disponíveis</span><p>Passe e corrida, antes e depois do intervalo.</p></div></aside>
    </section><RoundGames active={game} round={round}/><Archive active={game} round={round}/>
  </main>;
}
function AnalysisControls({ period, play, change }: { period: Period; play: PlayType; change: (key: string, value: string) => void }) {
  return <div className="analysis-controls"><div className="analysis-intro"><span className="section-kicker">Mesa de análise</span><h2>Produção dos ataques</h2></div><div className="control-fields"><label className="period-label">Período<span className="select-wrap"><select value={period} onChange={e => change('period', e.target.value)}>{Object.entries(periodLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select><ChevronDown aria-hidden="true" size={16}/></span></label><div className="play-select"><span>Fundamento</span><div role="group" aria-label="Fundamento">{(['all', 'pass', 'rush'] as const).map(p => <button key={p} aria-pressed={p === play} onClick={() => change('play', p)}>{p === 'all' ? 'Todos' : playLabels[p]}</button>)}</div></div></div></div>;
}
function Pregame({ game }: { game: Game }) {
  return <section className="pregame-content"><div><span className="section-kicker">Antes do kickoff</span><h2>Sem estatísticas desta partida.</h2><p>Ainda sem jogadas, não há recortes de período ou fundamento para selecionar.</p></div><dl><div><dt>Local</dt><dd>{game.venue}</dd></div><div><dt>Dados oferecidos</dt><dd>Agenda e identidade dos times</dd></div><div><dt>Série histórica</dt><dd>Não oferecida nesta demonstração</dd></div></dl></section>;
}
function Matchup() {
  const { id } = useParams(), game = gameForId(id), location = useLocation();
  const [params, setParams] = useSearchParams(), state = readState(params.toString()), nav = navigationContext(location.pathname, location.search);
  const update = (changes: Record<string, string>) => { const next = new URLSearchParams(params); Object.entries(changes).forEach(([key, value]) => { if (value) next.set(key, value); else next.delete(key); }); if (!next.has('round')) next.set('round', String(nav.originRound)); setParams(next, { replace: true, preventScrollReset: true }); };
  const change = (key: string, value: string) => update({ [key]: value });
  if (!game) return <main id="main" tabIndex={-1} className="page not-found"><h1>Confronto fora desta edição.</h1><p>Escolha um dos jogos disponíveis pela central.</p><ExploreLink to={nav.centralHref}>Voltar à central</ExploreLink></main>;
  const [a, b] = game.sides.map(s => teams[s.team]), reading = readSlice(game, state.period, state.play);
  return <main id="main" tabIndex={-1} className="page matchup-page"><div className="breadcrumb"><Link to={nav.centralHref}><ArrowLeft size={16} aria-hidden="true"/>Central · rodada {nav.originRound}</Link><ChevronRight size={14} aria-hidden="true"/><span>Duelo da rodada {game.round} · {a.city} × {b.city}</span></div><article className="analysis-board"><div className="segment-header"><span>Rodada {game.round} · {game.venue}</span><span>{game.status === 'pregame' ? 'Pré-jogo' : 'Encerrado · simulação'}</span></div><MatchupBand game={game}/>
    <div className="matchup-summary"><div><span className="section-kicker">{game.status === 'pregame' ? 'Pré-jogo' : 'Resumo da partida'}</span><h1>{game.title}</h1><p>{game.deck}</p></div>{game.status === 'final' ? <ScoreTimeline game={game}/> : <div className="pregame-agenda"><span>Próximo kickoff</span><strong>{game.kickoff}</strong><span>Rodada {game.round} · agenda demonstrativa</span></div>}</div>
    {game.status === 'pregame' ? <Pregame game={game}/> : <>
      <AnalysisControls period={state.period} play={state.play} change={change}/>
      <div className="analysis-context"><span>{periodLabels[state.period]} <span>/</span> {playLabels[state.play]}</span><span>{game.sides.map(s => { const stat = summarize(s, state.period, state.play); return `${s.team}: ${stat ? `${stat.plays} jogadas` : 'amostra sem fonte'}`; }).join(' · ')}</span></div>
      <div className="chart-grid"><EfficiencyChart game={game} period={state.period} play={state.play}/><SuccessChart game={game} period={state.period} play={state.play}/></div>
      <SliceReading reading={reading} game={game} recover={(period, play) => update({ period, play })}/>
      <StatSummary reading={reading}/>
      <AnalysisDetails game={game} period={state.period} play={state.play} open={state.details} toggle={() => change('details', state.details ? '' : 'open')}/>
    </>}
    </article><RoundGames active={game} round={nav.originRound}/><Archive active={game} round={nav.originRound}/><Link className="back-bottom" to={nav.centralHref}><ArrowLeft size={17} aria-hidden="true"/>Voltar à central · rodada {nav.originRound}</Link></main>;
}
export default function App() {
  return <BrowserRouter><PageFocus/><Header/><Routes><Route path="/" element={<Home/>}/><Route path="/confronto/:id" element={<Matchup/>}/><Route path="*" element={<main id="main" className="page not-found" tabIndex={-1}><h1>Página fora de campo.</h1><ExploreLink to="/?round=7">Voltar à central</ExploreLink></main>}/></Routes><Footer/></BrowserRouter>;
}
