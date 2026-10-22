import { useState } from 'react';
// Pure visual identity: no matchup fixtures or editorial decisions.
export function Logo({ team, className = '' }: { team: { id: string; logo: string }; className?: string }) {
  const [failed, setFailed] = useState(false);
  return failed ? <span className={`logo-fallback ${className}`}>{team.id}</span> : <img className={`team-logo ${className}`} src={team.logo} alt="" width="500" height="500" onError={() => setFailed(true)}/>;
}
