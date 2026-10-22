import { useState } from 'react';
// Visual only. Keyed state retries independently after a team/source change.
function LogoImage({ team, className }: { team: { id: string; logo: string; logoPlate?: boolean }; className: string }) {
  const [failed, setFailed] = useState(false);
  return !team.logo.trim() || failed
    ? <span className={`logo-fallback ${className}`} aria-hidden="true">{team.id}</span>
    : <img className={`team-logo ${className}`} src={team.logo} style={team.logoPlate ? { backgroundColor: '#E1E9ED', padding: 6, boxSizing: 'border-box' } : undefined} alt="" width="500" height="500" onError={() => setFailed(true)}/>;
}
export function Logo({ team, className = '' }: { team: { id: string; logo: string; logoPlate?: boolean }; className?: string }) {
  return <LogoImage key={`${team.id}|${team.logo}`} team={team} className={className}/>;
}
