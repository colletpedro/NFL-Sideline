import {useEffect,useRef,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {PresentationContext} from '../presentation';
import {ReadingPolishContext} from '../reading-polish/context';
import {RankingRedzoneContext} from '../ranking-redzone/context';
import {RedzoneEpaContext} from '../redzone-epa/context';
import type {EpaData} from '../redzone-epa/model';
import {Hub} from '../hub-team/Hub';
import {TeamPage} from '../hub-team/TeamPage';
import {MatchupContent} from '../w12/Content';
import {calendarGame} from '../w12/calendar';
import {RequestGate} from '../hub-team/model';
import {PIN,WEEKS,foundation,originWeek,gameHref,teamHref,weekHref,readRoute,validateRoute,type RouteData} from './model';
import '../hub-team/hub-team.css';
import './season.css';
const presentation={weeks:WEEKS,period:'W1–7',defaultWeek:7,pin:PIN,redzonePin:PIN,gameHref,teamHref,weekHref};
function routeError(q:URLSearchParams){try{validateRoute(q);return '';}catch(e){return e instanceof Error?e.message:'URL incompatível com este acervo.';}}
export default function SeasonApp({labEnabled=false}:{labEnabled?:boolean}){
 const [q,setQ]=useSearchParams(),[retry,setRetry]=useState(0),gate=useRef(new RequestGate());const requestParams=new URLSearchParams(q);requestParams.delete('foundation');requestParams.delete('rank');const requestHref=requestParams.toString(),key=requestHref+'|'+retry;
 const focusedEntity=useRef('');
 const [loaded,setLoaded]=useState<{key:string;data:RouteData}|null>(null),[failed,setFailed]=useState<{key:string;text:string}|null>(null);
 const invalid=routeError(q),current=loaded?.key===key?loaded.data:null,error=invalid||(failed?.key===key?failed.text:'');
 useEffect(()=>{if(invalid)return;const g=gate.current,revision=g.begin(),controller=new AbortController();readRoute(new URLSearchParams(requestHref),controller.signal).then(data=>{if(g.current(revision))setLoaded({key,data});}).catch(e=>{if(g.current(revision))setFailed({key,text:e instanceof Error?e.message:'A leitura não está disponível.'});});return()=>{controller.abort();g.cancel();};},[key,requestHref,invalid]);
 const entity=q.get('game')??q.get('team')??`hub-${q.get('week')??7}`;
 useEffect(()=>{window.scrollTo(0,0);},[entity]);
 useEffect(()=>{if(!current)return;document.title=(current.kind==='team'?`${current.d.scope.team} · W1–7`:current.kind==='matchup'?`${current.d.game.away} × ${current.d.game.home}`:`Semana ${q.get('week')??7}`)+' · NFL Sideline';const id=current.kind==='team'?'entity-title':current.kind==='matchup'?'mr-title':q.get('q')?'ht-results-title':'hub-title';const focusKey=entity+'|'+(q.get('q')??'');if(focusedEntity.current!==focusKey){document.getElementById(id)?.focus();focusedEntity.current=focusKey;if(window.location.hash)document.getElementById(window.location.hash.slice(1))?.scrollIntoView();}},[current,q,entity]);
 const origin=originWeek(q),back=weekHref(q,origin),f=foundation(q);
 const changeFoundation=(value:typeof f)=>{const next=new URLSearchParams(q);next.set('foundation',value);setQ(next,{preventScrollReset:true});};
 const rz:EpaData|null=current&&current.kind!=='hub'?{contractVersion:'broadcast-season-analysis-v1',rule:'classified-scrimmage-redzone-start-v1',sourcePin:PIN,pbpHash:current.index.sources.pbpHash,season:2026,phase:'REG',weeks:WEEKS,guarantees:current.d.guarantees,policy:{prediction:false,leagueReference:false},games:current.kind==='matchup'?{[current.d.game.gameId]:current.d.redzoneEpa}:{},teams:current.kind==='team'?{[current.d.scope.team]:current.d.redzoneEpa}:{}}:null;
 return <PresentationContext.Provider value={presentation}><ReadingPolishContext.Provider value><RankingRedzoneContext.Provider value><RedzoneEpaContext.Provider value={{data:rz,error:'',loading:!current,retry:()=>setRetry(n=>n+1)}}><div className={`ht season-seven rp rr ${current?.kind==='team'||current?.kind==='matchup'?'mr':''}`}><a className="skip-link" href="#ht-main">Ir ao conteúdo</a><header className="ht-header"><Link className="brand" to={back}>NFL <strong>SIDELINE</strong></Link><nav aria-label="Navegação do acervo"><Link to={back}>Voltar à semana</Link>{labEnabled?<Link style={{display:'inline-flex',minHeight:44,alignItems:'center'}} to="/?view=risk-lab&season=2026">Laboratório — risco de passe</Link>:null}<a href="http://127.0.0.1:18108/?season=2026&week=1">Referência W1–2</a></nav></header><main id="ht-main" className="ht-main" tabIndex={-1}>
 {error?<section className="mr-state" role="alert"><h1>Esta leitura não está disponível</h1><p>{error}</p><button onClick={()=>setRetry(n=>n+1)}>Tentar carregar novamente</button><Link to={back}>Voltar à semana</Link></section>:!current?<section className="mr-state" role="status"><p>Conferindo os dados desta página…</p></section>:current.kind==='hub'?<Hub index={current.index} q={q} onChange={setQ}/>:current.kind==='team'?<TeamPage key={current.d.scope.team} d={current.d} q={q} foundation={f} onFoundation={changeFoundation}/>:<><MatchupContent key={current.d.game.gameId} d={current.d} game={calendarGame(current.d.calendar)} foundation={f} onFoundation={changeFoundation} participantHref={t=>teamHref(q,t)}/><nav className="mr-switch" aria-label="Outros confrontos da semana">{current.index.games.filter(g=>g.week===current.d.game.weeks[0]&&g.gameId!==current.d.game.gameId).map(g=><Link key={g.gameId} to={gameHref(q,g)}>{g.away} × {g.home}</Link>)}</nav></>}
 </main><footer className="ht-footer"><p>NFL Sideline · 2026 REG W1–7 · acervo local, sem previsão</p><details><summary>Fontes e limites do acervo</summary><p>107 jogos nas semanas 1 a 7. Atualização da fonte congelada em 27/10/2026. Folgas não recebem taxa ou posição. Agregados incluem somente jogos do time nesse período; não representam sete jogos para todos.</p><p>Completude, cobertura esperada, modelo EPA e disponibilidade histórica continuam desconhecidos. Avaliação anterior P01/N=1, sem novo estudo ou reconfirmação de EPA.</p><p>Pin da coleção: <code>{PIN}</code></p></details></footer></div></RedzoneEpaContext.Provider></RankingRedzoneContext.Provider></ReadingPolishContext.Provider></PresentationContext.Provider>;
}
