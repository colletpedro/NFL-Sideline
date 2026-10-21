import { useEffect, useRef } from 'react';
import { ArrowLeft, ArrowUpRight, ChevronDown, ChevronRight } from 'lucide-react';
import { BrowserRouter, Link, Route, Routes, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { countPair, format, games, pair, periodLabels, playLabels, rate, signed, summarize, teams, type Game, type Period, type PlayType } from './fixtures';
import { gameForId, readState } from './state';
import { ExploreLink, GameLink, MatchupBand, YardagePreview } from './ui';
import { EfficiencyChart, ScoreTimeline, SuccessChart } from './Charts';

function Header() {
  const location = useLocation(), state = readState(location.search), matchup = location.pathname.startsWith('/confronto/');
  return <><a className="skip-link" href="#main">Pular para o conteúdo</a><header className="site-header"><div className="header-inner">
    <Link className="brand" to={`/?round=${state.round}`} aria-label="NFL Sideline, central da rodada">NFL <strong>SIDELINE</strong><span className="brand-rule" aria-hidden="true"/></Link>
    <nav aria-label="Principal"><Link to={`/?round=${state.round}`} aria-current={!matchup ? 'page' : undefined}>Central da rodada</Link><Link to={`/confronto/${(games.find(g => g.round === state.round) ?? games[0]).id}?round=${state.round}`} aria-current={matchup ? 'page' : undefined}>Mesa de análise</Link></nav>
    <span className="demo-notice">Demonstração · dados simulados</span>
  </div></header></>;
}
function PageFocus() {
  const { pathname } = useLocation();
  const first = useRef(true);
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
  return <section className="archive" aria-labelledby="archive-title"><div className="archive-heading"><h2 id="archive-title">Outros duelos, outras histórias.</h2><span>Arquivo da demonstração</span></div><div className="archive-games">{games.filter(g => g.id !== active.id).map(g => <GameLink key={g.id} game={g} round={round}/>)}</div></section>;
}
function Home() {
  const [params, setParams] = useSearchParams(), { round } = readState(params.toString());
  const game = games.find(g => g.round === round) ?? games[0];
  const [a, b] = game.sides.map(s => teams[s.team]);
  const pass = summarize(game.sides[0], 'game', 'pass'), rush = summarize(game.sides[0], 'game', 'rush');
  return <main id="main" tabIndex={-1} className="page home-page"><div className="edition-heading"><div><span className="section-kicker">Edição de demonstração</span><h1>CENTRAL DA RODADA</h1></div><div className="round-picker" role="group" aria-label="Selecionar rodada"><span>Rodada</span>{[6, 7, 8].map(r => <button key={r} aria-pressed={round === r} onClick={() => setParams({ round: String(r) })}>{r}</button>)}</div></div>
    <section className="opening" aria-labelledby="opening-headline"><div className="opening-main"><div className="segment-header"><span>Confronto em foco</span><span>Rodada {game.round} <span className="header-dot">/</span> {game.venue}</span></div><MatchupBand game={game} home/>
      <div className="opening-story"><span className="section-kicker">{a.city} × {b.city}</span><h2 id="opening-headline">{game.title}</h2><p>{game.deck}</p><div className="opening-bottom"><div className="opening-fact"><strong>{format(pass.yards)}</strong><span>jardas no passe<br/>de {a.city}</span></div><div className="opening-fact"><strong>{format(rush.yards)}</strong><span>jardas em corrida<br/>de {a.city}</span></div><ExploreLink to={`/confronto/${game.id}?round=${round}`}>Explorar confronto</ExploreLink></div></div></div>
      <aside className="opening-aside"><span className="section-kicker">Na mesa</span><h2>{game.angle}</h2><p>O placar conta o resultado. A distribuição de jardas revela os caminhos de cada ataque.</p><YardagePreview game={game}/><Link className="text-link" to={`/confronto/${game.id}?round=${round}&play=pass`}>Ver o passe em detalhe<ArrowUpRight size={18} aria-hidden="true"/></Link><div className="aside-bottom"><span>Leitura tática</span><p>Eficiência, volume e consistência. Três maneiras de ir além do placar.</p></div></aside>
    </section><Archive active={game} round={round}/>
    <section className="reading-strip"><span className="section-kicker">O jogo nos números</span><h2>Volume não é eficiência.</h2><p>Um ataque pode avançar mais jardas e ainda desperdiçar jogadas. Entre na mesa e compare a produção de cada tentativa.</p><Link to={`/confronto/${game.id}?round=${round}&play=all`}>Abrir a mesa<ArrowUpRight size={18} aria-hidden="true"/></Link></section>
  </main>;
}
function AnalysisControls({ period, play, change }: { period: Period; play: PlayType; change: (key: string, value: string) => void }) {
  return <div className="analysis-controls"><div className="analysis-intro"><span className="section-kicker">Mesa de análise</span><h2>Onde o jogo muda</h2></div><div className="control-fields"><label className="period-label">Período<span className="select-wrap"><select value={period} onChange={e => change('period', e.target.value)}>{Object.entries(periodLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select><ChevronDown aria-hidden="true" size={16}/></span></label><div className="play-select"><span>Fundamento</span><div role="group" aria-label="Fundamento">{(['all', 'pass', 'rush'] as const).map(p => <button key={p} aria-pressed={p === play} onClick={() => change('play', p)}>{p === 'all' ? 'Todos' : playLabels[p]}</button>)}</div></div></div></div>;
}
function StatSummary({ game, period, play }: { game: Game; period: Period; play: PlayType }) {
  const stats = game.sides.map(s => summarize(s, period, play));
  return <section className="stats-section"><div className="stats-title"><h3>A produção em perspectiva</h3><p>Mesmo recorte, dois ataques.</p></div><table className="stat-table"><caption className="sr-only">Estatísticas de ataque · {periodLabels[period]} · {playLabels[play]}</caption><thead><tr><th scope="col">Ataque</th>{game.sides.map(s => <th scope="col" key={s.team}><span className="team-dot" style={{ background: teams[s.team].color }}/>{teams[s.team].city}</th>)}</tr></thead><tbody>
    <tr><th scope="row">Jogadas</th>{stats.map((s, i) => <td key={i}>{s.plays}</td>)}</tr><tr><th scope="row">Jardas produzidas</th>{stats.map((s, i) => <td key={i}>{format(s.yards)}</td>)}</tr><tr><th scope="row">Jardas por jogada</th>{stats.map((s, i) => <td key={i}>{s.plays ? format(s.yards / s.plays, 1) : 'Sem amostra'}</td>)}</tr><tr><th scope="row">Jogadas com sucesso</th>{stats.map((s, i) => <td key={i}>{s.success}<small>de {s.plays}</small></td>)}</tr>
    </tbody></table><div className="defense-note"><b>Do outro lado da bola</b><p>As {format(stats[0].yards)} jardas de {teams[game.sides[0].team].city} são as jardas permitidas pela defesa de {teams[game.sides[1].team].city}, neste recorte.</p></div></section>;
}
function Details({ game, period, play, open, change }: { game: Game; period: Period; play: PlayType; open: boolean; change: (key: string, value: string) => void }) {
  return <section className={`details-section ${open ? 'is-open' : ''}`}><button className="details-toggle" aria-expanded={open} aria-controls="analysis-details" onClick={() => change('details', open ? '' : 'open')}><span><b>Por trás dos números</b><span>Contagens, definições e limites da leitura</span></span><ChevronDown size={20} aria-hidden="true"/></button>{open && <div id="analysis-details" className="details-content"><div className="definition-grid"><div><h3>Como ler EPA</h3><p>Pontos esperados adicionados estimam a mudança de valor de uma posse. Aqui, o EPA é sintético. A média divide a soma pela quantidade de jogadas do recorte.</p></div><div><h3>O que entra na amostra</h3><p>Jogadas ofensivas de passe (incluindo sacks) e corrida. Sem special teams, ajoelhadas ou spikes. Sucesso significa EPA positivo; frequência e sucesso são medidas diferentes.</p></div></div><div className="data-table-wrap"><table className="detail-table"><caption>Leitura equivalente dos gráficos · {periodLabels[period]}</caption><thead><tr><th scope="col">Time / fundamento</th><th scope="col">Jogadas</th><th scope="col">Sucesso</th><th scope="col">EPA/jogada</th></tr></thead><tbody>{game.sides.flatMap(s => (play === 'all' ? ['pass', 'rush'] as const : [play]).map(p => { const stat = summarize(s, period, p); return <tr key={`${s.team}-${p}`}><th scope="row">{s.team} · {playLabels[p]}</th><td>{stat.plays}</td><td>{stat.success}/{stat.plays} · {rate(stat)}</td><td>{signed(stat.epa / stat.plays)}</td></tr>; }))}</tbody></table></div><div className="situational"><h3>Situações de jogo</h3><p>Recorte: {periodLabels[period].toLowerCase()} · todos os fundamentos. Red zone = touchdowns / posses que chegaram à linha de 20 jardas.</p><table><thead><tr><th scope="col">Ataque</th><th scope="col">3ª descida</th><th scope="col">Red zone</th></tr></thead><tbody>{game.sides.map(s => <tr key={s.team}><th scope="row">{s.team}</th><td>{pair(countPair(s, period, 'third'))}</td><td>{pair(countPair(s, period, 'redzone'))}</td></tr>)}</tbody></table></div><p className="source-note">Fixture local, criada para esta experiência. Não descreve jogos ocorridos, não é previsão e não representa uma análise publicada. “Não disponível” indica ausência, nunca zero.</p></div>}</section>;
}
function Matchup() {
  const { id } = useParams(), game = gameForId(id);
  const [params, setParams] = useSearchParams(), state = readState(params.toString());
  const change = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true, preventScrollReset: true }); };
  if (!game) return <main id="main" tabIndex={-1} className="page not-found"><h1>Confronto fora desta edição.</h1><p>A demonstração reúne três duelos. Escolha um pela central.</p><ExploreLink to={`/?round=${state.round}`}>Voltar à central</ExploreLink></main>;
  const [a, b] = game.sides.map(s => teams[s.team]);
  return <main id="main" tabIndex={-1} className="page matchup-page"><div className="breadcrumb"><Link to={`/?round=${state.round}`}><ArrowLeft size={16} aria-hidden="true"/>Central · rodada {state.round}</Link><ChevronRight size={14} aria-hidden="true"/><span>{a.city} × {b.city}</span></div><article className="analysis-board"><div className="segment-header"><span>Rodada {game.round} · {game.venue}</span><span>Duelo demonstrativo</span></div><MatchupBand game={game}/>
    <div className="matchup-summary"><div><span className="section-kicker">{game.angle}</span><h1>{game.title}</h1><p>{game.deck}</p></div><ScoreTimeline game={game}/></div>
    <AnalysisControls period={state.period} play={state.play} change={change}/>
    <div className="analysis-context" aria-live="polite"><span>{periodLabels[state.period]} <span>/</span> {playLabels[state.play]}</span><span>{game.sides.map(s => `${s.team}: ${summarize(s, state.period, state.play).plays} jogadas`).join(' · ')}</span></div>
    <div className="chart-grid"><EfficiencyChart game={game} period={state.period} play={state.play}/><SuccessChart game={game} period={state.period} play={state.play}/></div>
    <StatSummary game={game} period={state.period} play={state.play}/>
    <div className="editorial-take"><span className="take-label">Leitura do recorte</span><h3>{state.play === 'all' ? 'O contexto muda a leitura.' : state.play === 'pass' ? 'O passe tem sua própria história.' : 'O chão também move a posse.'}</h3><p>{game.sides.map(s => { const stat = summarize(s, state.period, state.play); return `${teams[s.team].city}: ${signed(stat.epa / stat.plays)} EPA por jogada em ${stat.plays} tentativas.`; }).join(' ')} Compare a eficiência com a taxa de sucesso para distinguir impacto e regularidade.</p></div>
    <Details game={game} period={state.period} play={state.play} open={state.details} change={change}/>
    </article><Archive active={game} round={state.round}/><Link className="back-bottom" to={`/?round=${state.round}`}><ArrowLeft size={17} aria-hidden="true"/>Voltar à central da rodada</Link></main>;
}
export default function App() {
  return <BrowserRouter><PageFocus/><Header/><Routes><Route path="/" element={<Home/>}/><Route path="/confronto/:id" element={<Matchup/>}/><Route path="*" element={<main id="main" className="page not-found" tabIndex={-1}><h1>Página fora de campo.</h1><ExploreLink to="/?round=7">Voltar à central</ExploreLink></main>}/></Routes><Footer/></BrowserRouter>;
}
