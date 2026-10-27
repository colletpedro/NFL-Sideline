import type {Campaign} from '../w12/model';
import {CampaignSymbol} from '../ranking-redzone/Campaigns';
import {epaLabel,value,type Reading} from './model';
import {evidenceClock,situation,visitReading} from './visits';

const outcomes:Record<string,string>={TOUCHDOWN:'Touchdown',FIELD_GOAL:'Field goal',MISSED_FIELD_GOAL:'Field goal perdido ou bloqueado',TURNOVER:'Turnover',DOWNS:'Perda por descidas',PUNT:'Punt',END_HALF_GAME:'Fim de tempo ou jogo',SAFETY:'Safety',OPPONENT_TOUCHDOWN:'Touchdown da defesa'};
export function VisitNarrative({rows,campaigns}:{rows:{label:string;reading:Reading}[];campaigns?:Campaign[][]}){
 let groups;
 try{
  if(!campaigns||campaigns.length!==rows.length)throw new Error('Campanhas indisponíveis.');
  groups=rows.map((row,i)=>({...row,...visitReading(row.reading,campaigns[i])}));
 }catch{return <p className="mr-note" role="status">Não foi possível conferir o vínculo entre jogadas e campanhas. O EPA disponível permanece acima.</p>;}
 return <div className="rz-visit-narrative">
  <details className="rz-visits"><summary>Jogadas por visita à red zone <span>Situação inicial → jogadas → resultado</span></summary>
   <p className="mr-note">Uma visita por campanha, mesmo quando o ataque sai e volta às últimas 20 jardas. A lista reúne as jogadas que entram no EPA; chutes e outras exclusões não compõem essa média.</p>
   <div className="rz-visit-columns">{groups.map(g=><div key={g.label}><h4>{g.label}</h4><p className="rz-visit-count">{g.visits.length} {g.visits.length===1?'visita':'visitas'} · {g.reading.validN} jogadas com EPA válido</p>
    {!g.visits.length&&<p>Sem visita elegível observada neste recorte.</p>}
    {g.visits.map(v=><article className="rz-visit" key={v.campaign.id} data-rz-visit={v.campaign.id}>
     <header><strong>Campanha {v.campaign.fixedDrive}</strong>{g.reading.gameIds.length>1&&<span>W{v.campaign.week} · {v.campaign.offense} × {v.campaign.defense}</span>}</header>
     <div className="rz-visit-start"><span className="rz-step-label">Situação inicial na red zone</span><strong>{situation(v.initial)}</strong><span>{evidenceClock(v.initial)}</span></div>
     <ol className="rz-visit-plays" aria-label={`Jogadas elegíveis da campanha ${v.campaign.fixedDrive} de ${v.campaign.offense}`}>{v.plays.map(({unit:u,evidence:e})=><li key={u.id} data-rz-visit-play={u.id}><div><strong>{u.kind==='pass'?'Passe':'Corrida'}{u.sack?' · sack':''}{u.scramble?' · scramble':''}</strong><b>{u.epaStatus==='VALID'?`${epaLabel(Number(u.epa))} EPA`:'EPA indisponível'}</b></div><p>{situation(e)}<br/>{evidenceClock(e)} · jogada {u.playId}</p><p className="rz-source-description" lang="en">{e.desc}</p></li>)}</ol>
     {!v.plays.length&&<p>Sem jogada elegível para este EPA na visita.</p>}
     <div className="rz-visit-result"><CampaignSymbol outcome={v.campaign.outcome}/><div><span className="rz-step-label">Resultado da visita</span><strong>{outcomes[v.campaign.outcome]??'Desfecho não identificado'}</strong></div></div>
    </article>)}
    {value(g.reading)!==null&&<p className="rz-mean-explanation"><strong>Como se chega à média</strong><br/>{epaLabel(Number(g.reading.sum.numerator)/Number(g.reading.sum.denominator))} EPA somados ÷ {g.reading.validN} jogadas ≈ <b>{epaLabel(value(g.reading)!)} EPA/jogada</b>.</p>}
   </div>)}</div>
  </details>
  <section className="rz-impact" aria-label="Jogadas que mais pesaram no EPA"><h4>As jogadas que mais pesaram</h4><p className="mr-note">Maior contribuição em valor absoluto para a soma de EPA de cada ataque.</p>
   <div className="rz-visit-columns">{groups.map(g=>{const p=g.highlight;return <div className="rz-impact-reading" key={g.label}><h5>{g.label}</h5>{p?<><p className="rz-impact-value">{epaLabel(Number(p.unit.epa))}<span>EPA na jogada {p.unit.playId}</span></p><p>{Number(p.unit.epa)<0?'Contribuiu negativamente para a soma.':Number(p.unit.epa)>0?'Contribuiu positivamente para a soma.':'Todas as jogadas válidas tiveram EPA zero.'}{g.ties>1&&` ${g.ties} jogadas compartilham o maior valor absoluto; esta é a primeira na ordem do recorte.`}</p><details className="rz-impact-detail"><summary>Ver situação e descrição <span>Jogada {p.unit.playId} · {g.label}</span></summary>{g.reading.gameIds.length>1&&<p>W{p.unit.week} · {p.unit.offense} × {p.unit.defense}</p>}<p><strong>{situation(p.evidence)}</strong><br/>{evidenceClock(p.evidence)}</p><p className="rz-source-description" lang="en">{p.evidence.desc}</p><p className="mr-note">Descrição original da fonte. EPA desta jogada: {epaLabel(Number(p.unit.epa))}; a média acima usa as {g.reading.validN} jogadas válidas.</p></details></>:<p>Sem jogada com EPA válido para destacar.</p>}</div>;})}</div>
  </section>
 </div>;
}
