import type { CSSProperties } from 'react';
import type { Game } from '../../src/services/types';
import { Logo } from '../../broadcast-experience/TeamLogo';
import { teamIdentity } from '../../broadcast-real/identity';
import { TeamMedia } from './Media';
import { candidateFor } from './catalog';
export function PilotDuel({ game }: { game: Game }) {
  const away = candidateFor(game.awayTeam.teamAbbr, 'helmet');
  const home = candidateFor(game.homeTeam.teamAbbr, 'helmet');
  // Only original photographs with opposing masks qualify; never mirror inscriptions.
  const facing = !!away?.orientation.includes('direita') && !!home?.orientation.includes('esquerda');
  return <div className="pilot-duel">{[game.awayTeam, game.homeTeam].map(team => {
    const visual = teamIdentity(team.teamAbbr);
    return <div key={team.teamAbbr} className="pilot-team" style={{ '--team': visual.color, '--team-dark': visual.dark } as CSSProperties}>
      <div className="pilot-team-name"><Logo team={visual}/><div><span>{visual.city} · {team.teamAbbr}</span><strong>{visual.name}</strong></div></div>
      {facing ? <TeamMedia team={team.teamAbbr} type="helmet" allowCandidate/> : <div className="pilot-logo"><Logo team={visual}/></div>}
    </div>;
  })}</div>;
}
