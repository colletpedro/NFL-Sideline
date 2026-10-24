import { useState, type CSSProperties } from 'react';
import { epaAxisLabels, epaScale } from '../../broadcast-experience/chartScale';
import { teamIdentity } from '../../broadcast-real/identity';
import { coordinate, epaText, leaguePositions, permitted, rate, sideAllowed, type Attempt, type Campaign, type Document, type Epa, type Family, type Foundation, type Metric, type Point, type Production, type Reference } from './model';

const distances = { short:'1–3 jardas', medium:'4–6 jardas', long:'7+ jardas', unknown:'Distância desconhecida' };
const outcomes: Record<string,string> = {TOUCHDOWN:'Touchdown',FIELD_GOAL:'Field goal',MISSED_FIELD_GOAL:'Field goal perdido ou bloqueado',TURNOVER:'Turnover',OPPONENT_TOUCHDOWN:'TD do time que defendia',DOWNS:'Perda por descidas',PUNT:'Punt',END_HALF_GAME:'Fim de tempo ou jogo',SAFETY:'Safety'};
export function Unavailable({metric,comparison=false}:{metric?:Metric;comparison?:boolean}) {
  const state=metric?.descriptor.status;
  return <p className="mr-unavailable" role="status">{state==='NO_OPPORTUNITIES'?'Fonte presente, sem oportunidades elegíveis. Sem taxa (0/0).':state==='INSUFFICIENT'?'Registros insuficientes ou contraditórios para apresentar uma taxa neste jogo.':state==='SOURCE_ABSENT'?'Não há fonte para esta leitura do jogo.':comparison?'A comparação não está autorizada para este recorte.':'Esta observação não está disponível para apresentação.'}</p>;
}
export function MetricValue({metric}:{metric:Metric}) {
  if(!permitted(metric.display,'display',[metric.descriptor.id]) || metric.descriptor.status!=='AVAILABLE')return <Unavailable metric={metric}/>;
  const m=metric.descriptor;
  return <span className="mr-ratio"><strong>{m.numerator}/{m.denominator}</strong><span>{rate(m)}</span></span>;
}
function ProductionName({p}:{p:Production}) {return <div className="mr-production"><h3>{p.label}</h3><span>contra a defesa de {p.defense}</span></div>;}
export function Rule({title,children}:{title:string;children:React.ReactNode}) {return <details className="mr-rule"><summary>{title}</summary><div>{children}<a href="#mr-method">Consultar método completo</a></div></details>;}
function epaReady(e:Epa) {return e.descriptor.status==='AVAILABLE' && permitted(e.display,'display',[e.descriptor.id]) && !!e.originalObservation.values.epa;}
export function EpaBlock({d,foundation,onFoundation}:{d:Document;foundation:Foundation;onFoundation:(f:Foundation)=>void}) {
  const entries=d.productions.map(p=>p.epa.find(e=>e.foundation===foundation)!);
  const allowed=sideAllowed(d,foundation) && entries.every(epaReady);
  const values=entries.map(e=>epaReady(e)?coordinate(e.originalObservation.values.epa!):null);
  const scale=epaScale(values),zero=scale.position(0);
  return <section className="mr-section" id="mr-epa" tabIndex={-1} aria-labelledby="mr-epa-title">
    <div className="mr-section-title"><h2 id="mr-epa-title">Produção com a bola</h2><div className="mr-foundations" role="group" aria-label="Fundamento do EPA">{([['general','Geral'],['classified_pass','Passe'],['classified_rush','Corrida']] as const).map(([id,label])=><button key={id} type="button" aria-pressed={foundation===id} onClick={()=>onFoundation(id)}>{label}</button>)}</div></div>
    <p className="mr-unit">EPA · pontos esperados por jogada com EPA válido · deste jogo</p>
    <p className="mr-note">{foundation==='classified_pass'?'Passe inclui sacks.':foundation==='classified_rush'?'Corrida inclui scrambles.':'Geral reúne passe e corrida elegíveis.'} Os dois ataques usam a mesma escala.</p>
    {!allowed?<Unavailable metric={entries.find(e=>!epaReady(e))} comparison/>:<div className="mr-epa-chart" data-foundation={foundation}>
      <div className="mr-epa-axis" aria-hidden="true">{epaAxisLabels(scale).map(v=><span key={v} style={{left:`${scale.position(v)}%`}}>{v===0?'0':`${v>0?'+':'−'}${Math.abs(v).toFixed(2).replace('.',',')}`}</span>)}</div>
      {d.productions.map((p,i)=>{const e=entries[i],v=values[i]!,pos=scale.position(v);return <div key={p.offense} className="mr-epa-row" data-epa-team={p.offense}>
        <div className="mr-epa-label"><ProductionName p={p}/><div className="mr-epa-value"><strong data-epa-value={p.offense}>{epaText(e)}</strong><span>{e.descriptor.denominator} jogadas com EPA válido</span></div></div>
        <div className="mr-epa-track" aria-hidden="true" data-domain={`${scale.min}/${scale.max}`}><i className="mr-zero" style={{left:`${zero}%`}}/><span style={{left:`${Math.min(zero,pos)}%`,width:`${Math.abs(pos-zero)}%`,background:teamIdentity(p.offense).color}}/></div>
      </div>;})}
    </div>}
    <Rule title="Quais jogadas entram no EPA?"><p>A população é própria do EPA: jogadas elegíveis de passe e corrida com EPA finito. O denominador não é o de terceiras ou de campanhas. O modelo de pontos esperados não está identificado neste arquivo; os valores descrevem os registros observados.</p></Rule>
  </section>;
}
function MarkShape({kind,converted}:{kind:Attempt['kind'];converted:boolean}) {
  return <svg viewBox="0 0 28 28" aria-hidden="true" className="mr-attempt-shape">{kind==='pass'?<circle cx="14" cy="14" r="11"/>:<rect x="3" y="3" width="22" height="22"/>}{converted?<path d="m8 14 4 4 8-9"/>:<path d="M9 14h10"/>}</svg>;
}
export function ThirdBlock({d}:{d:Document}) {
  const [selected,setSelected]=useState<Attempt|null>(null);
  const allowed=sideAllowed(d,'third');
  const buckets=(Object.keys(distances) as Attempt['distance'][]).filter(b=>b!=='unknown'||d.productions.some(p=>p.thirdAttempts.some(u=>u.distance==='unknown')));
  return <section className="mr-section" id="mr-third" tabIndex={-1} aria-labelledby="mr-third-title">
    <h2 id="mr-third-title">Terceiras descidas</h2><p className="mr-unit">Conversões / tentativas elegíveis · deste jogo</p>
    {!allowed?<Unavailable comparison metric={d.productions.map(p=>p.metrics.third).find(m=>m.descriptor.status!=='AVAILABLE')}/>:<>
      <div className="mr-pair mr-totals">{d.productions.map(p=><div key={p.offense}><ProductionName p={p}/><MetricValue metric={p.metrics.third}/></div>)}</div>
      <p className="mr-mark-legend"><span><MarkShape kind="pass" converted={false}/> Círculo: passe, incluindo sacks.</span><span><MarkShape kind="run" converted={false}/> Quadrado: corrida, incluindo scrambles.</span><span><i className="mr-filled-key"/> Preenchida e com traço de confirmação: conversão. Vazia e com traço horizontal: não convertida.</span></p>
      <div className="mr-distance-groups">{buckets.map(bucket=><div className="mr-distance" key={bucket} id={bucket==='long'?'mr-long':undefined} tabIndex={bucket==='long'?-1:undefined}>
        <h3>{distances[bucket]}</h3>{bucket==='long'&&!sideAllowed(d,'thirdLong')?<Unavailable comparison/>:<div className="mr-pair">{d.productions.map(p=>{const units=p.thirdAttempts.filter(u=>u.distance===bucket),r=p.metrics.third.observation.byDistance[bucket];return <div className="mr-distance-team" key={p.offense}>
          <div className="mr-distance-heading"><strong>{p.offense} com a bola</strong><span>{r.numerator}/{r.denominator}</span></div>
          <div className="mr-attempts" aria-label={`${p.offense}, ${distances[bucket]}, ${r.numerator} conversões em ${r.denominator} tentativas`}>{units.map(u=><button key={u.id} type="button" data-third-mark={u.id} data-distance={u.distance} data-kind={u.kind} data-converted={u.converted} className={`mr-attempt ${u.converted?'is-converted':''}`} style={{'--production-color':teamIdentity(p.offense).dark} as CSSProperties} onClick={()=>setSelected(u)} aria-pressed={selected?.id===u.id} aria-label={`${p.offense}, jogada ${u.playId}, ${u.yardsToGo??'distância desconhecida'} jardas, ${u.kind==='pass'?'passe':'corrida'}${u.sack?', sack':''}${u.scramble?', scramble':''}, ${u.converted?'convertida':'não convertida'}`}><MarkShape kind={u.kind} converted={!!u.converted}/></button>)}</div>
          <p className="mr-joint-text">{p.thirdDistanceByType.filter(c=>c.distance===bucket).map(c=>`${c.kind==='pass'?'Passe':'Corrida'}: ${c.numerator}/${c.denominator}`).join(' · ')}<span> conversões / tentativas</span></p>
        </div>;})}</div>}
      </div>)}</div>
      <p className="mr-mark-readout" aria-live="polite">{selected?`${selected.offense} contra ${selected.defense} · ${selected.kind==='pass'?'Passe':'Corrida'}${selected.sack?' com sack':''}${selected.scramble?' com scramble':''} · ${selected.yardsToGo??'distância desconhecida'} jardas necessárias · ${selected.converted?'Convertida':'Não convertida'} · ID ${selected.id}`:'Cada marca é uma tentativa. Toque ou use Tab e Enter para consultar a jogada original.'}</p>
    </>}
    <Rule title="O que é uma terceira elegível?"><p>Passe ou corrida de terceira com flags válidas de conversão/falha. Exclui ajoelhadas, spikes, anuladas, abortadas e tentativas especiais. Avanço por penalidade não é automaticamente conversão. São as regras do projeto, não uma afirmação de estatística oficial da NFL.</p></Rule>
    <League reference={d.leagueReferences.third} family="third"/>
  </section>;
}
export function RedZoneBlock({d}:{d:Document}) {
  const [selected,setSelected]=useState<Campaign|null>(null);const allowed=sideAllowed(d,'redZone');
  return <section className="mr-section" id="mr-redzone" tabIndex={-1} aria-labelledby="mr-redzone-title"><h2 id="mr-redzone-title">Red zone</h2><p className="mr-unit">TDs ofensivos / campanhas que entraram nas 20 · deste jogo</p>
    {!allowed?<Unavailable comparison metric={d.productions.map(p=>p.metrics.redZone).find(m=>m.descriptor.status!=='AVAILABLE')}/>:<>
      <div className="mr-pair mr-redzone-pair">{d.productions.map(p=><div key={p.offense}><ProductionName p={p}/><MetricValue metric={p.metrics.redZone}/><p className="mr-note">{p.metrics.redZone.descriptor.numerator} {Number(p.metrics.redZone.descriptor.numerator)===1?'TD':'TDs'} em {p.metrics.redZone.descriptor.denominator} {p.metrics.redZone.descriptor.denominator===1?'campanha observada':'campanhas observadas'}.</p>
        <div className="mr-campaigns">{p.redZoneCampaigns.map(u=><button type="button" key={u.id} data-campaign-mark={u.id} onClick={()=>setSelected(u)} aria-pressed={selected?.id===u.id} aria-label={`${p.offense}, campanha ${u.fixedDrive}, ${outcomes[u.outcome]??u.outcome}`}><strong>{u.outcome==='TOUCHDOWN'?'TD':u.outcome==='FIELD_GOAL'?'FG':outcomes[u.outcome]??u.outcome}</strong><span>Campanha {u.fixedDrive}</span></button>)}</div>
        <p className="mr-outcomes">Desfechos: {Object.entries(p.metrics.redZone.observation.outcomes).sort(([a],[b])=>Number(b==='TOUCHDOWN')-Number(a==='TOUCHDOWN')).map(([k,v])=>`${v} ${k==='TOUCHDOWN'?(v===1?'TD':'TDs'):(outcomes[k]??k).toLowerCase()}`).join(' · ')}</p>
      </div>)}</div><p className="mr-note">Uma marca por campanha, em ordem da fonte. TD = touchdown; FG = field goal. Uma única oportunidade não demonstra uma capacidade estável.</p>
      <div className="mr-mark-readout" aria-live="polite">{selected?<><p>{selected.offense} contra {selected.defense} · Campanha {selected.fixedDrive} · {outcomes[selected.outcome]}.</p><p>Entrada demonstrada nas jogadas {selected.entryEvidence.map(e=>e.play_id).join(', ')}; desfecho na(s) jogada(s) {selected.outcomeEvidence.map(e=>e.play_id).join(', ')}.</p><p>ID {selected.id}</p></>:'Toque ou use Tab e Enter em uma campanha para consultar as evidências de entrada e desfecho.'}</div>
    </>}
    <Rule title="Quando uma campanha entra na red zone?"><p>Há posição observada antes de um evento de scrimmage a até 20 jardas da end zone, incluindo a linha de 20. Várias entradas não criam outra oportunidade na mesma campanha. Posição observada antes de ajoelhada também pode demonstrar entrada. TD de fora não cria entrada artificial.</p></Rule>
    <League reference={d.leagueReferences.redZone} family="redZone"/>
  </section>;
}
export function League({reference:r,family}:{reference:Reference;family:Family}) {
  const [selected,setSelected]=useState<Point|null>(null),points=r.teamRateDistribution.points;
  if(!permitted(r.permission,'leagueReference',points.map(p=>p.observationId)))return <p className="mr-unavailable">Referência da liga indisponível para esta operação.</p>;
  const positions=leaguePositions(points),height=Math.max(72,...positions.map(p=>36+p.lane*20));
  const label=(p:Point)=>`${p.team}: ${p.numerator}/${p.denominator}, ${rate(p)}`;
  const select=(p:Point)=>setSelected(p);
  return <div className="mr-league" aria-label={`Referência da liga, ${family==='third'?'terceiras':'red zone'}`}><h3>Os ataques da liga na W1</h3>
    <p className="mr-note">2026 REG · {points.length} times com taxa · {family==='third'?'conversões / terceiras elegíveis':'TDs ofensivos / campanhas que entraram nas 20'}. Cada ponto é um time.</p>
    <div className="mr-league-chart" role="group" aria-label={`Distribuição das taxas observadas de ${points.length} times, de zero a cem por cento`}><div className="mr-league-plot" style={{height}}>
      {positions.map(({point:p,x,lane})=><button type="button" key={p.team} className={`mr-league-point mr-point-${p.team}${selected?.team===p.team?' is-selected':''}`} style={{left:`${x/10}%`,bottom:18+lane*20}} aria-label={label(p)} aria-pressed={selected?.team===p.team} data-league-point={p.team} data-rate-x={x} onFocus={()=>select(p)} onClick={()=>select(p)}/>)}
    </div><div className="mr-league-axis" aria-hidden="true"><span>0%</span><span>50%</span><span>100%</span></div></div>
    <p className="mr-league-pilots">{points.filter(p=>['NYJ','TEN'].includes(p.team)).map(p=><span key={p.team} className={`mr-reference-${p.team}`}>{label(p)}</span>)}</p>
    <p className="mr-league-readout" aria-live="polite">{selected?label(selected):'Selecione um ponto ou consulte a lista com alvos maiores para toque.'}</p>
    <details className="mr-points-list"><summary>Consultar os {points.length} pontos e seus denominadores</summary><ul>{points.map(p=><li key={p.team}><button type="button" onClick={()=>select(p)} aria-pressed={selected?.team===p.team}>{label(p)}</button></li>)}</ul></details>
    {r.teamsWithoutRate.length>0&&<p className="mr-note">Fora da distribuição de taxas: {r.teamsWithoutRate.map(p=>`${p.team} — ${p.status==='NO_OPPORTUNITIES'?'fonte presente, sem oportunidades elegíveis (0/0), sem taxa':p.status==='INSUFFICIENT'?'registros insuficientes':'fonte ausente'}`).join('; ')}.</p>}
    <p className="mr-note">Taxa conjunta da amostra: {r.pooledRate.numerator}/{r.pooledRate.denominator} ({rate(r.pooledRate)}), calculada pelas somas, sem média das taxas dos times.</p>
    <p className="mr-note">NYJ e TEN pertencem à referência; o piloto não é uma amostra independente. Registros observados, sem ajuste ou inferência de qualidade.</p>
  </div>;
}
