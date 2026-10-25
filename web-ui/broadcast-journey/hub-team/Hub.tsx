import {teamStyle} from './visual';
import {Link} from 'react-router-dom';
import type {CalendarEntry,Index} from '../w12/model';
import {calendarGame} from '../w12/calendar';
import {dateLabel} from '../relations';
import {GameSearch} from '../GameSearch';
import {searchGames,suggestTeams} from '../discoveryModel';
import {teamIdentities,teamIdentity} from '../../broadcast-real/identity';
import {Logo} from '../../broadcast-experience/TeamLogo';
import {gameHref,teamHref,weekHref} from './model';
export function TeamLogo({team}:{team:string}) {const v=teamIdentity(team);return <Logo team={{...v,logoPlate:false}}/>;}
export function MatchItem({game:g,q,density='compact'}:{game:CalendarEntry;q:URLSearchParams;density?:'feature'|'support'|'compact'}) {
 return <article className={`ht-match ht-${density}`} data-hub-game={g.gameId} aria-label={`${g.away} contra ${g.home}, semana ${g.week}`}>
  <div className="ht-match-meta"><span>{dateLabel(g.gameday)}</span><span>Semana {g.week}</span></div>
  <div className="ht-duel">{[g.away,g.home].map((team,i)=>{const t=teamIdentity(team);return <div className="ht-participant" key={team} style={teamStyle(team)}><TeamLogo team={team}/><div><strong>{team}</strong><span>{t.city} {t.name}</span><Link to={teamHref(q,team)} aria-label={`Ver time ${t.city} ${t.name} (${team})`}>Ver time</Link></div><strong className="ht-score">{(i===0?g.awayScore:g.homeScore)??'—'}</strong></div>;})}</div>
  <div className="ht-match-action"><span>{g.awayScore!==null&&g.homeScore!==null?'Resultado registrado':'Resultado indisponível'}</span><Link to={gameHref(q,g)} aria-label={`Ver confronto ${g.away} × ${g.home}, semana ${g.week}`}>Ver confronto</Link></div>
 </article>;
}
export function Hub({index,q,onChange}:{index:Index;q:URLSearchParams;onChange:(q:URLSearchParams)=>void}) {
 const week=Number(q.get('week')??1),query=q.get('q')??'';
 const games=[...index.games].filter(g=>g.week===week).sort((a,b)=>(a.gameday??'').localeCompare(b.gameday??'')||a.gameId.localeCompare(b.gameId));
 const all=index.games.map(calendarGame),teams=[...new Map(all.flatMap(g=>[g.awayTeam,g.homeTeam]).map(t=>[t.teamAbbr,t])).values()].sort((a,b)=>a.teamAbbr.localeCompare(b.teamAbbr));
 const matchingTeams=suggestTeams(teams,query,32),matchingGames=searchGames(q.get('scope')==='week'?all.filter(g=>g.week===week):all,query);
 const search=(text:string)=>{const next=new URLSearchParams(q);if(text)next.set('q',text);else next.delete('q');if(!next.has('scope'))next.set('scope','season');next.delete('page');onChange(next);};
 const pickContext=(text:string)=>{const next=new URLSearchParams(q);next.set('q',text);if(!next.has('scope'))next.set('scope','season');return next;};
 return <><section className="ht-intro"><h1 id="hub-title" tabIndex={-1}>Seu próximo confronto.</h1><p>2026 REG · acervo de W1–2 · resultados e duas leituras ofensivas por jogo.</p></section>
 <nav className="ht-weeks" aria-label="Semanas disponíveis">{[1,2].map(w=><Link key={w} to={weekHref(q,w)} aria-current={week===w?'page':undefined}>Semana {w}<span>16 jogos</span></Link>)}</nav>
 <GameSearch games={all} teams={teams} query={query} week={week} onSearch={search} onPick={(game,_team,text)=>{const e=index.games.find(e=>e.gameId===game.gameId)!;onChange(new URLSearchParams(gameHref(pickContext(text),e).slice(2)));}} onPickTeam={(team,text)=>onChange(new URLSearchParams(teamHref(pickContext(text),team.teamAbbr).slice(2)))}/>
 {query.trim()&&<section className="ht-results" aria-labelledby="ht-results-title"><h2 id="ht-results-title" tabIndex={-1}>Resultados para “{query}”</h2><p>{matchingTeams.length} times · {matchingGames.length} partidas no acervo{q.get('scope')==='week'?` da semana ${week}`:''}.</p><ul>{matchingTeams.map(t=><li key={t.teamAbbr}><Link to={teamHref(q,t.teamAbbr)}>Ver time · {t.teamName} ({t.teamAbbr})</Link></li>)}{matchingGames.map(g=><li key={g.gameId}><Link to={gameHref(q,index.games.find(e=>e.gameId===g.gameId)!)}>Ver confronto · {g.awayTeam.teamAbbr} × {g.homeTeam.teamAbbr} · W{g.week}</Link></li>)}</ul></section>}
 <section aria-labelledby="ht-week-title"><div className="ht-heading"><h2 id="ht-week-title">Semana {week}</h2><a href="#ht-teams">Encontrar um time</a></div>
 <p className="ht-caption">16 confrontos disponíveis. O destaque segue a ordem de datas do calendário.</p>
 <MatchItem game={games[0]} q={q} density="feature"/>
 <div className="ht-supports">{games.slice(1,3).map(g=><MatchItem game={g} q={q} density="support" key={g.gameId}/>)}</div>
 <h3 className="ht-more">Continue pela semana</h3><div className="ht-remaining">{games.slice(3).map(g=><MatchItem key={g.gameId} game={g} q={q}/>)}</div></section>
 <section id="ht-teams" className="ht-directory" aria-labelledby="ht-team-title"><h2 id="ht-team-title">Os 32 times</h2><p>Abra um time para ler o recorte observado de W1–2 e seus dois jogos.</p><ul>{teams.map(t=><li key={t.teamAbbr}><Link to={teamHref(q,t.teamAbbr)} style={teamStyle(t.teamAbbr)}><TeamLogo team={t.teamAbbr}/><span>{teamIdentities[t.teamAbbr].city} <strong>{teamIdentities[t.teamAbbr].name}</strong><small>{t.teamAbbr} · Ver time</small></span></Link></li>)}</ul></section></>;
}
