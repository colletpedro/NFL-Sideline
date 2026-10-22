import type { CSSProperties } from 'react';
import type { Game } from '../../src/services/types';
import { Logo } from '../../broadcast-experience/TeamLogo';
import { teamIdentity } from '../../broadcast-real/identity';
import { TeamMedia } from './Media';
export function PilotDuel({ game }: { game: Game }) {
  return <div className="pilot-duel">{[game.awayTeam, game.homeTeam].map(team => {
    const visual = teamIdentity(team.teamAbbr);
    return <div key={team.teamAbbr} className="pilot-team" style={{ '--team': visual.color, '--team-dark': visual.dark } as CSSProperties}>
      <div className="pilot-team-name"><Logo team={visual}/><div><span>{visual.city} · {team.teamAbbr}</span><strong>{visual.name}</strong></div></div>
      <TeamMedia team={team.teamAbbr} type="helmet" allowCandidate/>
    </div>;
  })}</div>;
}
