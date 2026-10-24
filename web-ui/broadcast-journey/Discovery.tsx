import { useRef, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import type { Game } from '../src/services/types';
import { Logo } from '../broadcast-experience/TeamLogo';
import { teamIdentity } from '../broadcast-real/identity';
import type { Archive } from './sources';
import { calendarChange, journeyHref } from './state';
import { dateLabel, gameState } from './relations';
import { GameSearch } from './GameSearch';
import { availabilityDescription, searchGames } from './discoveryModel';

type Props = { games: Game[]; archive: Archive | null; archiveError: string; q: URLSearchParams; season: string; week: number | null; onChange: (q: URLSearchParams) => void; directHref?:(g:Game)=>string; readingStatus?:(g:Game)=>string };
export function Discovery({ games, archive, archiveError, q, season, week, onChange, directHref, readingStatus }: Props) {
  const query=q.get('q')??'',scope=q.get('scope')==='season'?'season':'week',participantsOnly=q.get('filter')==='participants';
  const heading=useRef<HTMLHeadingElement>(null);
  const inFilter=(g:Game)=>!participantsOnly || !!readingStatus || !!archive?.documents.some(({d})=>[g.homeTeam.teamAbbr,g.awayTeam.teamAbbr].includes(d.subject.team));
  const weekGames=games.filter(g=>g.week===week),filtered=weekGames.filter(inFilter),searching=query.trim().length>0;
  const matches=searchGames((scope==='season'?games:weekGames).filter(inFilter),query);
  const pageSize=12,pages=Math.max(1,Math.ceil(matches.length/pageSize)),requestedPage=Number(q.get('page'));
  const page=Math.min(pages,Math.max(1,Number.isInteger(requestedPage)?requestedPage:1));
  const weeks=[...new Set(games.map(g=>g.week))].sort((a,b)=>a-b);
  const change=(values:Record<string,string|null>)=>onChange(new URLSearchParams(journeyHref(q,{...calendarChange,...values}).slice(2)));
  const status=(g:Game)=>readingStatus?readingStatus(g):archiveError?'Arquivo de leituras indisponível':!archive?'Conferindo leituras':availabilityDescription(g,archive);
  const card=(g:Game)=>{
    const away=teamIdentity(g.awayTeam.teamAbbr),home=teamIdentity(g.homeTeam.teamAbbr),state=gameState(g);
    return <li key={g.gameId} data-game={g.gameId}><Link className="hub-match" aria-label={`Abrir confronto ${g.awayTeam.teamAbbr} ${g.homeTeam.teamAbbr} · semana ${g.week}`} to={directHref?directHref(g):journeyHref(q,{...calendarChange,game:g.gameId})}>
      <div className="hub-match-meta"><span>{dateLabel(g.gameday)}</span><span>Semana {g.week}</span></div>
      <div className="hub-duel" style={{'--away':away.color,'--away-dark':away.dark,'--home':home.color,'--home-dark':home.dark} as CSSProperties}>
        <div className="hub-team"><Logo team={away}/><strong>{g.awayTeam.teamAbbr}</strong><span>{away.name}</span></div>
        <div className="hub-score"><strong>{state.score?`${g.awayScore} – ${g.homeScore}`:'×'}</strong><span>{state.score?'Resultado':'Confronto'}</span></div>
        <div className="hub-team"><Logo team={home}/><strong>{g.homeTeam.teamAbbr}</strong><span>{home.name}</span></div>
      </div><div className="hub-match-bottom"><span>{state.score?status(g):state.label}</span><strong>Ver jogo <span aria-hidden="true">↗</span></strong></div>
    </Link></li>;
  };
  return <div className="discovery hub">
    <section className="discovery-tools hub-tools" aria-label="Busca e seleção do calendário">
      <GameSearch games={games.filter(inFilter)} query={query} week={week} onSearch={text=>change({q:text||null,scope:'season',page:null})} onPick={(g,team,text)=>change({game:g.gameId,team,q:text,scope:'season',page:null})}/>
      <details className="hub-options"><summary>Opções de busca e arquivo</summary><div><label>Buscar em<select aria-label="Buscar em" value={scope} onChange={e=>change({scope:e.target.value,page:null})}><option value="week">Esta semana</option><option value="season">Temporada {season}</option></select></label><label>Exibir jogos<select aria-label="Exibir jogos" value={q.get('filter')??'all'} onChange={e=>change({filter:e.target.value,page:null})}><option value="all">Todos os jogos</option><option value="participants">Com recortes dos participantes</option></select></label></div><p>“Com recortes” inclui outros períodos e lacunas; não garante leitura deste jogo.</p></details>
    </section>
    <nav className="hub-weeks" aria-label="Semanas da temporada"><div className="hub-weeks-heading"><h2>Temporada {season}</h2><span>Escolha a semana</span></div><div>{weeks.map(w=><button key={w} type="button" aria-label={`Semana ${w}`} aria-current={week===w?'page':undefined} onClick={()=>change({week:String(w),q:null,page:null,explore:null})}><strong>{w}</strong><span>{games.filter(g=>g.week===w).length} jogos</span></button>)}</div></nav>
    {searching ? <section className="discovery-results" aria-label="Resultados da busca"><div className="discovery-heading"><h2 ref={heading} tabIndex={-1}>Resultados para “{query}”</h2><p role="status">{matches.length} jogos · {scope==='season'?`temporada ${season}`:`semana ${week}`}</p></div>
      {matches.length?<><ul className="hub-games">{matches.slice((page-1)*pageSize,page*pageSize).map(card)}</ul>{pages>1&&<nav className="discovery-pagination" aria-label="Páginas de resultados"><button disabled={page===1} onClick={()=>{change({page:String(page-1)});heading.current?.focus();}}>Página anterior</button><span>Página {page} de {pages}</span><button disabled={page===pages} onClick={()=>{change({page:String(page+1)});heading.current?.focus();}}>Próxima página</button></nav>}</>:<div className="discovery-empty"><h3>Nenhum confronto encontrado.</h3><p>Tente outro nome, cidade ou sigla.</p>{scope==='week'&&<button onClick={()=>change({scope:'season'})}>Buscar na temporada {season}</button>}{participantsOnly&&<button onClick={()=>change({filter:'all'})}>Incluir jogos sem recortes</button>}<button onClick={()=>change({q:null,page:null})}>Voltar aos jogos da semana</button></div>}
    </section>:<section className="hub-week-games" aria-label={`Jogos da semana ${week}`}><div className="discovery-heading"><h2>Semana {week}</h2><p>{filtered.length} jogos · {season} · todos os confrontos abaixo</p></div>
      {participantsOnly&&!archive&&!readingStatus?<p role="status">O filtro aguarda a conferência do arquivo. Escolha “Todos os jogos” para ver o calendário.</p>:filtered.length?<ul className="hub-games">{filtered.map(card)}</ul>:<div className="discovery-empty"><h3>Nenhum jogo nesta seleção.</h3><button onClick={()=>change({filter:'all'})}>Mostrar todos os jogos</button></div>}
    </section>}
  </div>;
}
