import { useEffect, useRef, useState } from 'react';
import type { Game, Team } from '../src/services/types';
import { Logo } from '../broadcast-experience/TeamLogo';
import { teamIdentity } from '../broadcast-real/identity';
import { dateLabel } from './relations';
import { suggestGames, suggestTeams } from './discoveryModel';

type Props = {periodLabel?:string;games:Game[];query:string;week:number|null;onSearch:(text:string)=>void;onPick:(game:Game,team:string|null,text:string)=>void;teams?:Team[];onPickTeam?:(team:Team,text:string)=>void};
export function GameSearch({games,query,week,onSearch,onPick,teams,onPickTeam,periodLabel='W1–2'}:Props) {
  const [draft,setDraft] = useState(query),[open,setOpen] = useState(false),[active,setActive] = useState(-1);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {setDraft(query);setOpen(false);setActive(-1);},[query]);
  const suggestions = [...(teams&&onPickTeam?suggestTeams(teams,draft).map(team=>({kind:'team' as const,team})):[]),...suggestGames(games,draft,week).map(item=>({kind:'game' as const,...item}))], expanded = open && draft.trim().length > 0;
  const pick = (index:number) => {const item=suggestions[index];if(item){setOpen(false);setActive(-1);if(item.kind==='team')onPickTeam?.(item.team,draft.trim());else onPick(item.game,item.team,draft.trim());}};
  return <form className="hub-search" role="search" onSubmit={e=>{e.preventDefault();if(expanded && active>=0)pick(active);else{setOpen(false);onSearch(draft.trim());}}} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget)){setOpen(false);setActive(-1);}}}>
    <label htmlFor="game-search">Encontre seu time ou confronto</label>
    <div className="hub-search-line"><div className="hub-search-field"><input ref={input} id="game-search" type="search" role="combobox" autoComplete="off" value={draft} placeholder="Time, cidade ou sigla" aria-autocomplete="list" aria-expanded={expanded} aria-controls={expanded?'game-suggestions':undefined} aria-activedescendant={expanded && active>=0 ? `game-option-${active}`:undefined} aria-describedby="search-hint" onFocus={()=>setOpen(true)} onChange={e=>{setDraft(e.target.value);setActive(-1);setOpen(true);}} onKeyDown={e=>{
      if(e.key==='ArrowDown' || e.key==='ArrowUp'){e.preventDefault();setOpen(true);setActive(i=>suggestions.length?(i<0?(e.key==='ArrowDown'?0:suggestions.length-1):(i+(e.key==='ArrowDown'?1:-1)+suggestions.length)%suggestions.length):-1);}
      if(e.key==='Enter'){e.preventDefault();if(expanded && active>=0)pick(active);else{setOpen(false);onSearch(draft.trim());}}
      if(e.key==='Escape'){e.preventDefault();setOpen(false);setActive(-1);}
    }}/>
    {expanded && <div className="hub-suggestions"><ul id="game-suggestions" role="listbox" aria-label={teams?"Sugestões de times e partidas":"Sugestões de partidas"}>{suggestions.map((item,index)=><li key={item.kind==='team'?'team-'+item.team.teamAbbr:item.game.gameId} id={`game-option-${index}`} role="option" aria-selected={active===index} onMouseDown={e=>e.preventDefault()} onClick={()=>pick(index)}>
      {item.kind==='team'?<><span className="suggestion-logos" aria-hidden="true"><Logo team={teamIdentity(item.team.teamAbbr)}/></span><span><strong>Time · {item.team.teamName} ({item.team.teamAbbr})</strong><small>Ver time · {periodLabel}</small></span></>:<><span className="suggestion-logos" aria-hidden="true"><Logo team={teamIdentity(item.game.awayTeam.teamAbbr)}/><Logo team={teamIdentity(item.game.homeTeam.teamAbbr)}/></span><span><strong>{teams?'Partida · ':''}{item.game.awayTeam.teamAbbr} × {item.game.homeTeam.teamAbbr}</strong><span>{item.game.awayTeam.teamName} × {item.game.homeTeam.teamName}</span><small>Semana {item.game.week} · {dateLabel(item.game.gameday)}</small></span></>}
    </li>)}</ul>{!suggestions.length && <p role="status">{teams?'Nenhum time ou confronto encontrado. Tente outro nome ou sigla.':'Nenhuma partida encontrada. Tente outro nome ou sigla.'}</p>}{!!suggestions.length && <button type="submit" className="hub-all-results" onMouseDown={e=>e.preventDefault()} onClick={e=>{e.preventDefault();setActive(-1);setOpen(false);onSearch(draft.trim());}}>Ver todos os resultados para “{draft}”</button>}</div>}
    </div><button type="submit" className="journey-action">Buscar</button>{query && <button className="discovery-clear" type="button" onClick={()=>{setDraft('');setOpen(false);setActive(-1);onSearch('');input.current?.focus();}}>Limpar</button>}</div>
    <p id="search-hint">{teams?`Times e partidas de ${periodLabel} desde a primeira letra. Use ↑ ↓ e Enter.`:'Sugestões desde a primeira letra, em toda a temporada. Use ↑ ↓ e Enter para escolher.'}</p>
  </form>;
}
