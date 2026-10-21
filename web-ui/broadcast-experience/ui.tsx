import { useState, type CSSProperties } from 'react';
import { ArrowUpRight, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { score, summarize, teams, type Game, type Team } from './fixtures';

const theme = (team: Team): CSSProperties => ({ '--team': team.color, '--team-dark': team.dark, '--optical': team.optical } as CSSProperties);
export function Logo({ team, className = '' }: { team: Team; className?: string }) {
  const [failed, setFailed] = useState(false);
  return failed ? <span className={`logo-fallback ${className}`}>{team.id}</span> : <img className={`team-logo ${className}`} src={team.logo} alt="" width="500" height="500" onError={() => setFailed(true)}/>;
}
export function MatchupBand({ game, home = false }: { game: Game; home?: boolean }) {
  return <div className={`matchup-band ${home ? 'opening-band' : ''}`}>
    {game.sides.map((side, i) => {
      const team = teams[side.team];
      return <div className={`team-wing wing-${i}`} style={theme(team)} key={team.id}>
        <span className="identity-watermark" aria-hidden="true">{team.id}</span>
        <Logo team={team}/>
        <div className="team-name"><span>{team.city}</span><strong>{team.name}</strong></div>
        <span className="team-score" aria-label={`${score(side)} pontos`}>{score(side)}</span>
      </div>;
    })}
    <span className="band-center">Final<br/><span>simulado</span></span>
  </div>;
}
export function GameLink({ game, round, compact = false }: { game: Game; round: number; compact?: boolean }) {
  const [a, b] = game.sides.map(s => teams[s.team]);
  return <Link className={`game-link ${compact ? 'compact-game' : ''}`} to={`/confronto/${game.id}?round=${round}`}>
    <div className="game-identities"><div style={theme(a)}><Logo team={a}/></div><div style={theme(b)}><Logo team={b}/></div></div>
    <div className="game-link-copy"><span className="muted">Rodada {game.round} · {game.venue.split(' · ')[0]}</span><h3>{a.city} <span>×</span> {b.city}</h3><p>{game.angle}</p></div>
    <div className="mini-score">{score(game.sides[0])}<span>–</span>{score(game.sides[1])}</div>
    <ChevronRight aria-hidden="true" size={20}/>
  </Link>;
}
export function YardagePreview({ game }: { game: Game }) {
  return <div className="yardage-preview"><div className="yardage-key"><span>Jardas produzidas</span><span>Passe / corrida</span></div>{game.sides.map(s => {
    const team = teams[s.team], pass = summarize(s, 'game', 'pass'), rush = summarize(s, 'game', 'rush');
    return <div className="yardage-row" key={team.id} style={theme(team)}><div><b>{team.id}</b><strong>{pass.yards}<span> / {rush.yards}</span></strong></div><div className="yardage-track" aria-hidden="true"><span style={{ width: `${pass.yards / 450 * 100}%` }}/><i style={{ width: `${rush.yards / 450 * 100}%` }}/></div></div>;
  })}<p>Escala comum: 0–450 jardas. Trecho claro: corrida.</p></div>;
}
export function ExploreLink({ to, children }: { to: string; children: React.ReactNode }) {
  return <Link className="primary-link" to={to}>{children}<ArrowUpRight size={20} aria-hidden="true"/></Link>;
}
