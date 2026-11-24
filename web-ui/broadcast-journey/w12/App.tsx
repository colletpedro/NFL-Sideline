import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { calendarGame } from './calendar';
import { Discovery } from '../Discovery';
import { MatchupContent } from './Content';
import { calendarHref, loadDocument, loadIndex, matchupHref, resolveEntry, type Document as MatchupDocument, type Foundation, type Index } from './model';

export default function W12App() {
  const [q,setQ]=useSearchParams();
  const [loaded,setLoaded]=useState<{key:string;index:Index;d:MatchupDocument|null}|null>(null);
  const [failure,setFailure]=useState<{key:string;text:string}|null>(null);
  const [retry,setRetry]=useState(0),[foundation,setFoundation]=useState<Foundation>('general');
  const reading=q.get('view')==='matchup-w12',key=q.toString()+'|'+retry;
  const current=loaded?.key===key?loaded:null,error=failure?.key===key?failure.text:'';
  useEffect(()=>{
    let active=true;const c=new AbortController();
    loadIndex(c.signal).then(async index=>{
      if(reading){const entry=resolveEntry(index,new URLSearchParams(q));const d=await loadDocument(entry,c.signal);if(active)setLoaded({key,index,d});}
      else {if(q.has('season')&&q.get('season')!=='2026'||q.has('week')&&!['1','2'].includes(q.get('week')!))throw new Error('Calendário desta coleção disponível somente em 2026 REG, semanas 1 e 2.');if(active)setLoaded({key,index,d:null});}
    }).catch(e=>{if(active)setFailure({key,text:e instanceof Error?e.message:'Fonte indisponível.'});});
    return()=>{active=false;c.abort();};
  },[key,q,reading]);
  const game=current?.d?calendarGame(current.d.calendar):null;
  const pageTitle=game?`${game.awayTeam.teamAbbr} × ${game.homeTeam.teamAbbr} · W${game.week} · NFL Sideline`:'Calendário W1–2 · NFL Sideline';
  const gameId=q.get('game'),readyId=current?.d?.game.gameId;
  useEffect(()=>{const title=document.title;document.title=pageTitle;return()=>{document.title=title;};},[pageTitle]);
  useEffect(()=>{setFoundation('general');window.scrollTo(0,0);},[gameId]);
  useEffect(()=>{if(readyId){const target=window.location.hash?window.location.hash.slice(1):'mr-title';document.getElementById(target)?.focus();if(window.location.hash)document.getElementById(target)?.scrollIntoView();}},[readyId]);
  const back=calendarHref(q,current?.d?.game.weeks[0]??1);
  if(reading)return <div className="mr"><a className="skip-link" href="#mr-main">Ir à leitura do confronto</a><header className="mr-header"><Link className="brand" to={back}>NFL <strong>SIDELINE</strong></Link><Link to={back}>Voltar ao calendário</Link></header><main className="mr-main" id="mr-main">
    {error?<section className="mr-state" role="alert"><h1>Leitura do confronto indisponível</h1><p>{error}</p><button onClick={()=>setRetry(n=>n+1)}>Tentar carregar novamente</button></section>:current?.d&&game?<><MatchupContent key={game.gameId} d={current.d} game={game} foundation={foundation} onFoundation={setFoundation}/><nav className="mr-switch" aria-label="Outros confrontos da semana">{(()=>{const games=current.index.games.filter(g=>g.week===game.week),i=games.findIndex(g=>g.gameId===game.gameId);return <>{i>0&&<Link to={matchupHref(q,games[i-1])}>Anterior: {games[i-1].away} × {games[i-1].home}</Link>}{i<games.length-1&&<Link to={matchupHref(q,games[i+1])}>Próximo: {games[i+1].away} × {games[i+1].home}</Link>}</>;})()}</nav></>:<section className="mr-state" role="status"><h1>Conferindo o confronto</h1><p>Validando identidade, calendário e documento deste jogo…</p></section>}
  </main><footer className="mr-footer">NFL Sideline · leitura local de registros preservados · sem previsão</footer></div>;
  const week=Number(q.get('week')??'1');
  return <><a className="skip-link" href="#journey-main">Ir ao calendário</a><header className="site-header real-header"><div className="real-header-inner"><Link className="brand" to="/?season=2026&week=1">NFL <strong>SIDELINE</strong></Link><nav aria-label="Navegação principal"><Link to="/?view=explorer&season=2026&week=1">Explorador anterior</Link><Link to="/?view=matchup-reading">Piloto preservado</Link><Link to="/?view=legacy&season=2026&week=1">Percurso anterior</Link></nav></div></header>
  <main className="real-page journey-page" id="journey-main"><div className="real-intro"><div><p>Jogos e leituras arquivadas</p><h1>Encontre seu jogo.</h1></div></div>
  {error?<section className="real-state" role="alert"><h2>Calendário indisponível</h2><p>{error} Nenhum outro calendário foi usado.</p><button onClick={()=>setRetry(n=>n+1)}>Recarregar coleção</button></section>:current?<Discovery games={current.index.games.map(calendarGame)} archive={null} archiveError="" q={q} season="2026" week={week} onChange={next=>{const id=next.get('game');const e=current.index.games.find(g=>g.gameId===id);if(e)setQ(new URLSearchParams(matchupHref(next,e).slice(2)));else setQ(next);}} directHref={g=>matchupHref(q,current.index.games.find(e=>e.gameId===g.gameId)!)} readingStatus={()=>'Leitura dos dois ataques · deste jogo'}/>:<section className="real-state" role="status">Validando o calendário e a coleção local…</section>}
  <p className="journey-publication">Arquivo congelado de 2026 REG W1–2. Resultados do schedule preservado; disponibilidade histórica UNKNOWN.</p></main><footer className="real-footer">NFL Sideline · arquivo local, sem previsão</footer></>;
}
