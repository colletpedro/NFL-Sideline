import { ArrowLeft, ChevronRight } from 'lucide-react';
import { matchupSimulation } from './fixture';
import { RecapBoard } from './RecapBoard';
import './pilot.css';

export default function MatchupPilot() {
  const proof = new URLSearchParams(window.location.search).get('screen') === 'type-proof';
  return <div className="matchup-pilot">
    <a className="pilot-skip" href="#pilot-main">Pular para o confronto</a>
    <header className="pilot-topbar">
      <a className="pilot-brand" href="/" aria-label="NFL Sideline, piloto do laboratório">NFL <strong>SIDELINE</strong></a>
      <nav aria-label="Laboratório"><a href="/" aria-current={proof ? undefined : 'page'}>Confronto</a><a href="/?screen=lab">Outras propostas</a></nav>
      <span className="pilot-local">Laboratório local</span>
    </header>
    <main id="pilot-main" tabIndex={-1} className={`pilot-main${proof ? ' pilot-proof' : ''}`}>
      <div className="pilot-context"><a href={proof ? '/' : '/?screen=lab'}><ArrowLeft size={15} aria-hidden="true"/>{proof ? 'Voltar ao confronto' : 'Laboratório'}</a><span><ChevronRight size={13} aria-hidden="true"/>{proof ? 'Prova tipográfica' : 'Dallas × New England'}</span></div>
      <p className="pilot-notice" id="simulation-notice">{matchupSimulation.disclosure}</p>
      {proof ? <div className="pilot-type-options">{[
        ['type-archivo', 'Archivo + Roboto Condensed', 'Escolhida · grotesca no topo, condensada nos fatos'],
        ['type-plex', 'IBM Plex Sans + Condensed', 'Alternativa · desenhos mais técnicos'],
        ['type-barlow', 'Barlow + Condensed', 'Alternativa · curvas e proporções mais estreitas'],
      ].map(([className, title, description]) => <section className={className} key={className}><h2>{title}</h2><p>{description}</p><RecapBoard simulation={matchupSimulation}/><p className="pilot-glyphs">AÇÃO · precisão · 27 × 24 · 312 · 7/13 · 53,8%</p></section>)}</div> : <RecapBoard simulation={matchupSimulation}/>}
      <div className="pilot-tools"><a href={proof ? '/' : '/?screen=type-proof'}>{proof ? 'Abrir o piloto' : 'Prova tipográfica'}</a><span>Piloto de identidade visual</span></div>
    </main>
  </div>;
}
