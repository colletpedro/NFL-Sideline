import {useEffect,useRef,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {MatchupContent} from '../w12/Content';
import {calendarGame} from '../w12/calendar';
import type {Foundation} from '../w12/model';
import {backHref,gameHref,readRoute,RequestGate,teamHref,type RouteData} from './model';
import {Hub} from './Hub';
import {TeamPage} from './TeamPage';
import './hub-team.css';
export default function HubTeamApp() {
 const [q,setQ]=useSearchParams(),[retry,setRetry]=useState(0),[foundation,setFoundation]=useState<Foundation>('general');
 const key=q.toString()+'|'+retry,gate=useRef(new RequestGate());
 const [loaded,setLoaded]=useState<{key:string;data:RouteData}|null>(null),[failed,setFailed]=useState<{key:string;text:string}|null>(null);
 const current=loaded?.key===key?loaded.data:null,error=failed?.key===key?failed.text:'';
 useEffect(()=>{const revision=gate.current.begin(),controller=new AbortController(),g=gate.current;
  readRoute(new URLSearchParams(q),controller.signal).then(data=>{if(g.current(revision))setLoaded({key,data});}).catch(e=>{if(g.current(revision))setFailed({key,text:e instanceof TypeError?'Não foi possível carregar esta fonte local. Nenhum outro time, jogo ou período foi usado.':e instanceof Error?e.message:'Esta leitura está indisponível.'});});
  return()=>{controller.abort();g.cancel();};
 },[key,q]);
 const entity=q.get('team')??q.get('game')??'hub';
 useEffect(()=>{setFoundation('general');window.scrollTo(0,0);},[entity]);
 useEffect(()=>{if(current){const target=document.getElementById(current.kind==='team'?'entity-title':current.kind==='matchup'?'mr-title':q.get('q')?'ht-results-title':'hub-title');target?.focus();if(window.location.hash)document.getElementById(window.location.hash.slice(1))?.scrollIntoView();}},[current,q]);
 const title=current?.kind==='team'?`${current.d.scope.team} · W1–2`:current?.kind==='matchup'?`${current.d.game.away} × ${current.d.game.home}`:`Semana ${q.get('week')??1}`;
 useEffect(()=>{const previous=document.title;document.title=title+' · NFL Sideline';return()=>{document.title=previous;};},[title]);
 const back=backHref(q,current?.kind==='matchup'?current.d.game.weeks[0]:1);
 return <div className={`ht ${current?.kind==='team'||current?.kind==='matchup'?'mr':''}`}><a className="skip-link" href="#ht-main">Ir ao conteúdo</a><header className="ht-header"><Link className="brand" to={back}>NFL <strong>SIDELINE</strong></Link><nav aria-label="Navegação do acervo"><Link to={back}>Voltar à semana</Link><Link to="/?view=explorer&season=2026&week=1">Explorador anterior</Link></nav></header><main id="ht-main" className="ht-main">
 {error?<section className="mr-state" role="alert"><h1>Esta leitura não está disponível</h1><p>{error}</p><button onClick={()=>setRetry(n=>n+1)}>Tentar carregar novamente</button><Link to={back}>Voltar à semana</Link></section>:!current?<section className="mr-state" role="status"><p>Conferindo os dados desta página…</p></section>:current.kind==='hub'?<Hub index={current.index} q={q} onChange={setQ}/>:current.kind==='team'?<TeamPage key={current.d.scope.team} d={current.d} q={q} foundation={foundation} onFoundation={setFoundation}/>:<>
 <MatchupContent key={current.d.game.gameId} d={current.d} game={calendarGame(current.d.calendar)} foundation={foundation} onFoundation={setFoundation} participantHref={t=>teamHref(q,t)}/>
 <nav className="mr-switch" aria-label="Outros confrontos da semana">{current.index.games.filter(g=>g.week===current.d.game.weeks[0]&&g.gameId!==current.d.game.gameId).map(g=><Link key={g.gameId} to={gameHref(q,g)}>{g.away} × {g.home}</Link>)}</nav></>}
 </main><footer className="ht-footer"><p>NFL Sideline · 2026 REG W1–2 · acervo local, sem previsão</p><details><summary>Entradas anteriores e limites do arquivo</summary><p>Somente W1–2 têm leituras nesta entrada. Não é a temporada completa. A avaliação anterior teve P01/N=1; o esclarecimento de EPA não foi reconfirmado por pessoa.</p><Link to="/?view=explorer&season=2026&week=1">Explorador anterior</Link><Link to="/?view=calendar-w12&season=2026&week=1">Calendário anterior</Link><Link to="/?view=legacy&season=2026&week=1">Percurso anterior</Link><Link to="/?view=matchup-reading">Piloto preservado</Link></details></footer></div>;
}
