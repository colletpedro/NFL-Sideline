import { useEffect, useState, type CSSProperties } from 'react';
import { StaticNflDataClient } from '../../src/services/staticDataClient';
import type { NflDataClient } from '../../src/services/dataClient';
import type { Game } from '../../src/services/types';
import { finalGameResult } from '../../src/components/matchupResult';
import { Logo } from '../../broadcast-experience/TeamLogo';
import { teamIdentity } from '../../broadcast-real/identity';
import { dateLabel } from '../relations';
import { epaText, FOUNDATION_PIN, linkedFacts, permitted, loadDocument, matchCalendar, type Document, type Foundation } from './model';
import { EpaBlock, ThirdBlock, RedZoneBlock } from './Charts';
import './matchup.css';

const previous='/?view=explorer&season=2026&week=1&game=2026_01_NYJ_TEN&team=NYJ&side=off&analysis=third&question=distance&reading=game';
export function MatchupContent({d,game,foundation,onFoundation}:{d:Document;game:Game;foundation:Foundation;onFoundation:(f:Foundation)=>void}) {
  const result=finalGameResult(game),facts=linkedFacts(d);
  return <>
    <section className="mr-game" aria-labelledby="mr-title"><h1 id="mr-title">{game.awayTeam.teamAbbr} × {game.homeTeam.teamAbbr}</h1>
      <div className="mr-band">{[game.awayTeam,game.homeTeam].map((team,i)=>{const identity=teamIdentity(team.teamAbbr);return <div className={`mr-team mr-team-${team.teamAbbr}`} key={team.teamAbbr} style={{'--team':identity.color,'--team-dark':identity.dark} as CSSProperties}><Logo team={{...identity,logoPlate:false}}/><div><strong>{team.teamName}</strong><span>{team.teamAbbr}</span></div><strong className="mr-score">{result?(i===0?result.awayScore:result.homeScore):'—'}</strong></div>;})}</div>
      <p className="mr-game-context">{result?'Resultado registrado':'Resultado indisponível no calendário'} · {dateLabel(game.gameday)} · {game.season} {game.gameType} · Semana {game.week}</p>
      <p className="mr-retrospective">Leitura retrospectiva deste jogo.</p>
    </section>
    <div className="mr-paper">
      <section className="mr-section mr-summary" aria-labelledby="mr-summary-title"><h2 id="mr-summary-title">O que os registros mostram</h2>
        {facts.length===0?<p>Não há fatos autorizados para resumir esta fonte.</p>:<ul>{facts.map(f=><li key={f.id} data-fact={f.id}><p>{f.text}</p><a href={f.metric==='redZone'?'#mr-redzone':f.metric==='thirdLong'?'#mr-long':'#mr-third'}>Ver {f.metric==='redZone'?'campanhas':f.metric==='thirdLong'?'terceiras longas':'terceiras'}: {f.evidence.map(e=>`${d.productions.find(p=>p.metrics[f.metric].descriptor.id===e.observationId)?.offense} ${e.numerator}/${e.denominator}`).join('; ')}</a></li>)}</ul>}
      </section>
      <nav className="mr-anchors" aria-label="Blocos da leitura"><a href="#mr-epa">EPA</a><a href="#mr-third">Terceiras</a><a href="#mr-redzone">Red zone</a><a href="#mr-method">Método</a></nav>
      <EpaBlock d={d} foundation={foundation} onFoundation={onFoundation}/><ThirdBlock d={d}/><RedZoneBlock d={d}/>
      <section className="mr-section mr-market" id="mr-market" tabIndex={-1} aria-labelledby="mr-market-title"><h2 id="mr-market-title">Cotações arquivadas</h2><p>Instante de captura e fornecedor desconhecidos. Estes valores não são identificados como linha pré-jogo ou fechamento.</p>
        {d.market.records.length===0?<p>Sem cotações neste arquivo.</p>:d.market.records.map((r,i)=><dl key={i} className="mr-market-values">{([['away_moneyline',`${game.awayTeam.teamAbbr} · moneyline`],['home_moneyline',`${game.homeTeam.teamAbbr} · moneyline`],['spread_line','Spread · valor bruto'],['total_line','Total · valor bruto']] as const).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{typeof r[key]==='number'?`${(r[key] as number)>0?'+':''}${String(r[key]).replace('.',',')}`:'Não disponível'}</dd></div>)}</dl>)}
        <p className="mr-note">O sinal do spread é preservado como campo bruto, sem atribuição a um time. Sem favorito, edge, confiança ou recomendação.</p><details className="mr-rule"><summary>Origem das cotações</summary><p>Schedule preservado. A data do jogo não demonstra quando a cotação foi capturada.</p>{d.market.sources.map(s=><p key={s.sourceRevisionId}>Origem: {s.origin}<br/><code>{s.sourceRevisionId}</code></p>)}</details>
      </section>
      <section className="mr-section mr-method" id="mr-method" tabIndex={-1} aria-labelledby="mr-method-title"><h2 id="mr-method-title">Método e procedência</h2><p>Regras resumidas junto de cada unidade; fontes e cálculos completos abaixo. As comparações descrevem a amostra observada, sem demonstrar superioridade, estabilidade ou previsão.</p>
        <p>Não há semanas anteriores da temporada regular disponíveis neste recorte da W1. É um limite do recorte, não uma falha de fonte desta partida. W2 não compõe esta leitura.</p>
        <details className="mr-audit"><summary>Consultar regras, exclusões e penalidades</summary><pre>{d.definitions.document}</pre>{d.productions.map(p=><div key={p.offense}><h3>{p.label}</h3><p>Exclusões de terceira: {Object.entries(p.metrics.third.observation.exclusions).map(([k,v])=>`${k}: ${v}`).join('; ')||'nenhuma'}.</p><p>Avanços por penalidade: {p.metrics.third.observation.penaltyFirstDowns.included} em tentativas incluídas; {p.metrics.third.observation.penaltyFirstDowns.excluded} em excluídas. Não são adicionados automaticamente às conversões.</p><p>IDs excluídos: {p.metrics.third.observation.excludedIds.join(', ')||'nenhum'}.</p></div>)}</details>
        <details className="mr-audit"><summary>Consultar EPA, unidades originais e campanhas</summary><h3>EPA, com somas e denominadores próprios</h3><div className="mr-table-scroll" tabIndex={0} role="region" aria-label="Tabela equivalente dos seis EPA"><table><thead><tr><th>Ataque</th><th>Fundamento</th><th>EPA/jogada</th><th>Jogadas válidas</th><th>Soma EPA exata</th></tr></thead><tbody>{d.productions.flatMap(p=>p.epa.filter(e=>e.descriptor.status==='AVAILABLE'&&permitted(e.display,'display',[e.descriptor.id])).map(e=><tr key={e.descriptor.id}><th>{p.offense}</th><td>{{general:'Geral',classified_pass:'Passe',classified_rush:'Corrida'}[e.foundation]}</td><td>{epaText(e)??'Sem taxa'}</td><td>{e.descriptor.denominator}</td><td>{e.originalObservation.totals.epaSum}</td></tr>))}</tbody></table></div>{d.productions.map(p=><div key={p.offense}><h3>{p.label}: unidades</h3><p>Defesa adversária é contexto da mesma produção, sem segunda amostra ou confirmação independente.</p><details><summary>IDs de EPA geral, passe e corrida</summary>{p.epa.filter(e=>e.descriptor.status==='AVAILABLE'&&permitted(e.display,'display',[e.descriptor.id])).map(e=><p key={e.foundation}>{e.foundation}: {e.eligibleUnitIds.join(', ')}</p>)}</details><details><summary>Jogadas de terceira</summary><ul>{p.thirdAttempts.map(u=><li key={u.id}>{u.id} · ordem {u.sourceOrder} · {u.yardsToGo??'desconhecida'} jardas · {u.kind} · {u.converted?'convertida':'não convertida'}</li>)}</ul></details><details><summary>Campanhas e evidências</summary>{p.redZoneCampaigns.map(u=><div key={u.id}><h4>{u.id}</h4><p>Ordem da fonte: {u.sourceOrder}. Desfecho: {u.outcome}.</p><p>Entradas: {u.entryEvidence.map(e=>`jogada ${e.play_id}, ${e.yardline_100} jardas até a end zone`).join('; ')}.</p>{u.outcomeEvidence.map(e=><p key={e.play_id}>Jogada {e.play_id}: {e.desc}</p>)}</div>)}</details></div>)}</details>
        <details className="mr-audit"><summary>Consultar garantias, fontes e permissões</summary><p>Completude, cobertura esperada, modelo EPA e disponibilidade histórica continuam desconhecidos (UNKNOWN). O mesmo arquivo e a mesma definição permitem as apresentações descritivas autorizadas; não certificam o modelo EPA. Não existe referência EPA da liga nesta página.</p><dl>{Object.entries(d.guarantees).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl><p>{d.contractVersion} · projeção {d.projectionVersion} · {d.policy.version}</p><p>Pin do pacote: <code>{FOUNDATION_PIN}</code></p>{Object.entries(d.sources).map(([k,v])=>typeof v==='string'?<p key={k}>{k}: <code>{v}</code></p>:null)}<pre>{d.policy.document}</pre><p>Operações indisponíveis: {d.unavailableOperations.map(o=>`${o.operation} (${o.reason})`).join('; ')}.</p></details>
      </section>
    </div>
  </>;
}
export default function MatchupPage() {
  const [d,setDocument]=useState<Document|null>(null),[game,setGame]=useState<Game|null>(null),[error,setError]=useState(''),[reload,setReload]=useState(0),[foundation,setFoundation]=useState<Foundation>('general');
  useEffect(()=>{
    let active=true;const controller=new AbortController();
    const calendar:NflDataClient=new StaticNflDataClient(window.fetch.bind(window));
    setDocument(null);setGame(null);setError('');
    Promise.all([loadDocument(controller.signal),calendar.listGames(2026)]).then(([document,games])=>{const g=matchCalendar(games,document);if(active){setDocument(document);setGame(g);}}).catch(()=>{if(active)setError('Não foi possível validar os dados deste jogo e seu calendário. Nenhuma outra fonte ou período foi usado.');});
    return()=>{active=false;controller.abort();};
  },[reload]);
  useEffect(()=>{const title=document.title;document.title='NYJ × TEN · Leitura do confronto · NFL Sideline';return()=>{document.title=title;};},[]);
  useEffect(()=>{if(d && game && window.location.hash)document.getElementById(window.location.hash.slice(1))?.scrollIntoView();},[d,game]);
  return <div className="mr"><a className="skip-link" href="#mr-main">Ir à leitura do confronto</a><header className="mr-header"><a className="brand" href="/">NFL <strong>SIDELINE</strong></a><a href={previous}>Voltar ao explorador anterior</a></header><main className="mr-main" id="mr-main">
    {error?<section className="mr-state" role="alert"><h1>Leitura do confronto indisponível</h1><p>{error}</p><button type="button" onClick={()=>setReload(n=>n+1)}>Tentar carregar o piloto novamente</button></section>:d&&game?<MatchupContent d={d} game={game} foundation={foundation} onFoundation={setFoundation}/>:<section className="mr-state" role="status"><h1>Conferindo o confronto</h1><p>Validando a base comparável e o calendário preservado…</p></section>}
  </main><footer className="mr-footer">NFL Sideline · leitura local de registros preservados · sem previsão</footer></div>;
}
