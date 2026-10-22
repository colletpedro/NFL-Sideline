import { type CSSProperties } from 'react';
import { ArrowUpRight, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { scoreboard, summarize, teams, type Game, type Team } from './fixtures';
import { matchupHref } from './state';

const theme = (team: Team): CSSProperties => ({ '--team': team.color, '--team-dark': team.dark, '--optical': team.optical } as CSSProperties);
import { Logo } from './TeamLogo';
export { Logo } from './TeamLogo';
export function MatchupBand({ game, home = false }: { game: Game; home?: boolean }) {
  const scores = scoreboard(game);
  return <div className={`matchup-band ${home ? 'opening-band' : ''} ${game.status === 'pregame' ? 'pregame-band' : ''}`}>
    {game.sides.map((side, i) => {
      const team = teams[side.team];
      return <div className={`team-wing wing-${i}`} style={theme(team)} key={team.id}>
        <span className="identity-watermark" aria-hidden="true">{team.id}</span>
        <Logo team={team}/>
        <div className="team-name"><span>{team.city}</span><strong>{team.name}</strong></div>
        {scores && <span className="team-score" aria-label={`${scores[i]} pontos`}>{scores[i]}</span>}
      </div>;
    })}
    <span className="band-center">{game.status === 'pregame' ? <>VS<br/><span>Pré-jogo</span></> : <>Final<br/><span>simulado</span></>}</span>
  </div>;
}
export function GameLink({ game, round }: { game: Game; round: number }) {
  const [a, b] = game.sides.map(s => teams[s.team]), scores = scoreboard(game);
  return <Link className={`game-link ${game.status === 'pregame' ? 'game-upcoming' : ''}`} to={matchupHref(game, round)}>
    <div className="game-identities"><div style={theme(a)}><Logo team={a}/></div><div style={theme(b)}><Logo team={b}/></div></div>
    <div className="game-link-copy"><span className="muted">Rodada {game.round} · {game.venue.split(' · ')[0]}</span><h3>{a.city} <span>×</span> {b.city}</h3><p>{game.dataNote ?? game.angle}</p></div>
    <div className="game-status-score"><span>{game.status === 'pregame' ? 'Pré-jogo' : 'Encerrado'}</span>{scores ? <strong className="mini-score">{scores[0]}<span>–</span>{scores[1]}</strong> : <strong className="kickoff-time">{game.kickoff}</strong>}</div>
    <ChevronRight aria-hidden="true" size={20}/>
  </Link>;
}
export function YardagePreview({ game }: { game: Game }) {
  const values = game.sides.map(s => ({ pass: summarize(s, 'game', 'pass'), rush: summarize(s, 'game', 'rush') }));
  const max = Math.max(450, ...values.map(v => v.pass && v.rush ? Math.ceil((v.pass.yards + v.rush.yards) / 50) * 50 : 0));
  return <div className="yardage-preview"><div className="yardage-key"><span>Jardas produzidas</span><span>Passe / corrida</span></div>{game.sides.map((s, i) => {
    const team = teams[s.team], { pass, rush } = values[i];
    return <div className="yardage-row" key={team.id} style={theme(team)}><div><b>{team.id}</b><strong>{pass?.yards ?? '—'}<span> / {rush?.yards ?? '—'}</span></strong></div>{pass && rush ? <div className="yardage-track" aria-hidden="true"><span style={{ width: `${pass.yards / max * 100}%` }}/><i style={{ width: `${rush.yards / max * 100}%` }}/></div> : <span className="preview-missing">Composição sem fonte completa</span>}</div>;
  })}<p>Escala comum: 0–{max} jardas. Trecho claro: corrida.</p></div>;
}
export function ExploreLink({ to, children }: { to: string; children: React.ReactNode }) {
  return <Link className="primary-link" to={to}>{children}<ArrowUpRight size={20} aria-hidden="true"/></Link>;
}
