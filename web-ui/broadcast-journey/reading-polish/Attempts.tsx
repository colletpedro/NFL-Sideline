export function AttemptSymbol({kind,converted}:{kind:'pass'|'run';converted:boolean}) {
 return <svg viewBox="0 0 28 28" aria-hidden="true" className={`mr-attempt-shape rp-attempt-symbol ${converted?'rp-converted':'rp-not-converted'}`} data-symbol-kind={kind} data-symbol-converted={converted}>{kind==='pass'?<circle cx="14" cy="14" r="11"/>:<rect x="3" y="3" width="22" height="22"/>}{converted?<path d="m8 14 4 4 8-9"/>:<path d="M9 14h10"/>}</svg>;
}
export function AttemptLegend() {
 return <div className="rp-attempt-legend"><ul aria-label="Legenda das tentativas de terceira">{(['pass','run'] as const).flatMap(kind=>[true,false].map(converted=><li key={`${kind}-${converted}`}><AttemptSymbol kind={kind} converted={converted}/><span>{kind==='pass'?'Passe':'Corrida'} — terceira {converted?'convertida':'não convertida'}</span></li>))}</ul><p className="mr-note">Uma marca por tentativa. Sacks entram em passe; scrambles entram em corrida.</p></div>;
}
