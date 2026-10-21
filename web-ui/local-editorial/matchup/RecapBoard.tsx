import { useState } from 'react';
import type { Simulation, SimulationTeam } from './fixture';
import { recapCopy } from './fixture';

export function BroadcastHeader({ title, context }: { title: string; context: string }) {
  return <header className="recap-header"><h1>{title}</h1><p>{context}</p></header>;
}
export function TeamIdentity({ team }: { team: SimulationTeam }) {
  const [unavailable, setUnavailable] = useState(false);
  return <section className={`recap-team recap-team-${team.code.toLowerCase()}`} aria-label={`${team.city} ${team.nickname}`}>
    <div className="recap-logo">{unavailable ? <span className="recap-logo-fallback">{team.code}</span> : <img src={team.logo} alt="" width="500" height="500" onError={() => setUnavailable(true)}/>}</div>
    <h2 className="recap-name"><span>{team.city}</span><strong>{team.nickname}</strong></h2>
  </section>;
}
export function FactRow({ lines }: { lines: string[] }) {
  return <li className="recap-fact">{lines.map((line, i) => <span key={line}>{i > 0 && ' '}{line}</span>)}</li>;
}
export function EditorialBody({ copy }: { copy: ReturnType<typeof recapCopy> }) {
  return <section className="recap-editorial" aria-label="Resumo demonstrativo">
    <h2 className="recap-headline">{copy.headline.map((line, i) => <span key={line}>{i > 0 && ' '}{line}</span>)}</h2>
    <ul className="recap-facts">{copy.facts.map(fact => <FactRow key={fact.key} lines={fact.lines}/>)}</ul>
  </section>;
}
export function RecapBoard({ simulation }: { simulation: Simulation }) {
  return <article className="recap-board" aria-label="Dallas Cowboys × New England Patriots — simulação visual" aria-describedby="simulation-notice">
    <BroadcastHeader title={simulation.heading} context={simulation.context}/>
    <div className="recap-identities">{simulation.teams.map(team => <TeamIdentity team={team} key={team.code}/>)}</div>
    <EditorialBody copy={recapCopy(simulation)}/>
  </article>;
}
