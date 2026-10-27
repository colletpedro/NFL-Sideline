import {usePresentation} from '../presentation';
import {useId,useState} from 'react';
import {Logo} from '../../broadcast-experience/TeamLogo';
import {teamIdentity} from '../../broadcast-real/identity';
import {coordinate,permitted,rate,type Point,type Reference,type Family} from '../w12/model';
import {observedPositions,POSITION_RULE} from './positions';
function Axis(){return <div className="rp-league-axis" aria-hidden="true"><span>Posição · time</span><div><i>0%</i><i className="rp-quarter">25%</i><i>50%</i><i className="rp-quarter">75%</i><i>100%</i></div><span>Taxa · razão</span></div>;}
function Row({point:p,position,participant}:{point:Point;position?:number;participant:boolean}) {
 return <li data-ranking-team={p.team} data-position={position??'none'} className={`${participant?'rp-league-participant':''}${position?'':' rr-unpositioned'}`}>
 <span className="rr-identity"><span className="rr-position">{position?`${position}º`:<>Sem<br/>posição</>}</span><span className="rp-league-team"><Logo team={{...teamIdentity(p.team),logoPlate:false}}/><strong>{p.team}</strong></span></span>
 {position?<><span className="rp-league-track" aria-hidden="true"><span data-rate-x={coordinate(p)*1000} style={{left:`${coordinate(p)*100}%`}}/></span><span className="rp-league-value"><strong>{rate(p)}</strong><span>{p.numerator} de {p.denominator}</span></span></>:<span className="rr-no-rate">{p.status==='NO_OPPORTUNITIES'?'0/0 · sem oportunidades, sem taxa':p.status==='INSUFFICIENT'?'Registros insuficientes · sem taxa':p.status==='SOURCE_ABSENT'?'Fonte ausente · sem taxa':'Taxa indisponível'}</span>}
 </li>;
}
export function RankingLeague({reference:r,family,participants}:{reference:Reference;family:Family;participants:string[]}) {
 const {weeks}=usePresentation();
 const [open,setOpen]=useState(false),id=useId(),points=r.teamRateDistribution.points;
 if(!permitted(r.permission,'leagueReference',points.map(p=>p.observationId)))return <p className="mr-unavailable">Referência da liga indisponível para esta operação.</p>;
 let positions:ReturnType<typeof observedPositions>;
 try{if(r.season!==2026||r.phase!=='REG'||r.weeks.length!==1||!weeks.includes(r.weeks[0])||participants.length!==2||new Set(participants).size!==2||participants.some(t=>!r.participantsIncluded.includes(t)||!r.inventory.some(p=>p.team===t)))throw new Error();positions=observedPositions(points);}catch{return <p className="mr-unavailable">Inventário incompatível com a classificação desta semana.</p>;}
 const title=`${family==='third'?'Conversões de terceira':'TDs em campanhas de red zone'} — ataques na W${r.weeks[0]}`;
 return <div className="mr-league rp-league rr-ranking" role="group" aria-label={title} data-position-rule={POSITION_RULE}>
 <h3>{title}</h3><p className="mr-note">{r.season} {r.phase} · {points.length} times com taxa, de {r.candidateTeams.length} candidatos. {family==='third'?'Conversões / tentativas elegíveis.':'TDs ofensivos / campanhas que entraram nas 20.'}</p>
 {r.byeTeams&&r.byeTeams.length>0&&<p className="mr-note">Folgas na W{r.weeks[0]}: {r.byeTeams.join(', ')}. Sem jogo, fora desta referência.</p>}
 <p className="mr-note">Posições pela taxa observada; taxas iguais compartilham posição.</p>
 <div data-ranking-scope="summary"><Axis/><ul className="rp-league-rows" aria-label="Participantes, em ordem visitante e casa">{participants.map(team=>{const row=positions.find(e=>e.point.team===team);return <Row key={team} point={row?.point??r.inventory.find(p=>p.team===team)!} position={row?.position} participant/>;})}</ul></div>
 <button type="button" className="rr-expand" aria-expanded={open} aria-controls={id} onClick={()=>setOpen(v=>!v)}><span className="rr-expand-label"><span className="rr-expand-measure" aria-hidden="true">Ver classificação completa — {points.length} times</span><span>{open?'Recolher classificação':`Ver classificação completa — ${points.length} times`}</span></span><span className="rr-expand-sign" aria-hidden="true">{open?'−':'+'}</span></button>
 <div id={id} className={`rr-reveal${open?' is-open':''}`} aria-hidden={!open} {...(!open?{inert:''}:{})}>
 <div className="rr-reveal-clip"><section className="rr-complete" aria-label="Classificação completa da semana" data-ranking-scope="full"><Axis/><ul className="rp-league-rows">{positions.map(({point,position})=><Row key={point.team} point={point} position={position} participant={participants.includes(point.team)}/>)}</ul>
 {r.teamsWithoutRate.length>0&&<div className="rr-without-rate"><h4>Sem taxa e sem posição</h4><ul className="rp-league-rows" data-ranking-scope="without-rate">{r.teamsWithoutRate.map(p=><Row key={p.team} point={p} participant={participants.includes(p.team)}/>)}</ul></div>}
 </section></div></div>
 <p className="mr-note">Taxa conjunta da amostra: {r.pooledRate.numerator}/{r.pooledRate.denominator} ({rate(r.pooledRate)}), pelas somas. {participants.join(' e ')} pertencem à referência; a repetição na lista completa é apenas visual.</p><p className="mr-note">Registros observados, sem ajuste ou inferência de qualidade. Os participantes não são independentes da referência.</p>
 </div>;
}
