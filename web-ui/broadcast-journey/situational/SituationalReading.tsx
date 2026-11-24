import { useEffect, useState, type CSSProperties } from 'react';
import type { Game } from '../../src/services/types';
import { teamIdentity } from '../../broadcast-real/identity';
import { compositionFact } from './compositionCopy';
import { percent, selectDocument, validateSnapshot, type Snapshot, type SituationalDocument } from './model';
const names={third:'Terceiras descidas',redzone:'Red zone'};
const outcomes:Record<string,string>={TOUCHDOWN:'Touchdown ofensivo',FIELD_GOAL:'Field goal',MISSED_FIELD_GOAL:'Field goal perdido/bloqueado',TURNOVER:'Turnover',OPPONENT_TOUCHDOWN:'Touchdown adversário',DOWNS:'Perda por descidas',PUNT:'Punt',END_HALF_GAME:'Fim de tempo/jogo',SAFETY:'Safety'};
function DistanceChart({d}:{d:SituationalDocument}) {
  const groups=[['short','1–3 jardas'],['medium','4–6 jardas'],['long','7+ jardas'],['unknown','Distância não informada']].filter(([k])=>k!=='unknown'||d.third.byDistance[k].denominator>0);
  const max=Math.max(1,...groups.map(([k])=>d.third.byDistance[k].denominator));
  return <figure className="sit-distance"><figcaption><h3>Conversões por distância necessária</h3><p>Barras na mesma escala de tentativas: 0 a {max}. Definição de faixas do projeto.</p></figcaption>
    <div className="sit-chart-legend"><span>■ Conversões</span><span>□ Tentativas</span></div>
    {groups.map(([k,label])=>{const f=d.third.byDistance[k];return <div className="sit-distance-row" key={k}><strong>{label}</strong><div className="sit-attempts" role="img" aria-label={`${label}: ${f.numerator} conversões em ${f.denominator} tentativas; ${percent(f)??'sem taxa'}. Escala 0 a ${max}.`}><span style={{width:`${100*f.denominator/max}%`}}><i style={{width:`${f.denominator ? 100*f.numerator/f.denominator:0}%`}}/></span></div><span>{f.numerator} / {f.denominator}<small>{percent(f)??'Sem oportunidades'}</small></span></div>;})}
    <p className="sit-caption">Cada razão mostra conversões / tentativas, sem média entre faixas.</p>
  </figure>;
}
function DriveChart({d}:{d:SituationalDocument}) {
  const m=d.redZone;
  return <figure className="sit-drives"><figcaption><h3>Uma marca, uma campanha</h3><p>{m.numerator} touchdowns ofensivos em {m.denominator} oportunidades confirmadas.</p></figcaption>
    <div className="sit-drive-marks" role="img" aria-label={`${m.numerator} de ${m.denominator} campanhas terminaram em touchdown ofensivo. ${m.denominator-m.numerator} tiveram outros desfechos.`}>{Array.from({length:m.denominator},(_,i)=><span className={i<m.numerator?'sit-td':''} key={i} aria-hidden="true">{i<m.numerator?'TD':'—'}</span>)}</div>
    <p className="sit-caption">TD = touchdown ofensivo. — = outro desfecho. Marcas agrupadas por resultado; não indicam sequência.</p>
    <dl className="sit-outcomes">{Object.entries(m.outcomes).map(([k,n])=><div key={k}><dt>{outcomes[k]??k}</dt><dd>{n}</dd></div>)}</dl>
  </figure>;
}
function Method({d,snapshot,family}:{d:SituationalDocument;snapshot:Snapshot;family:'third'|'redzone'}) {
  const third=family==='third',m=third?d.third:d.redZone;
  return <details className="sit-method"><summary>Como esta leitura foi calculada</summary>
    <h3>Regras da leitura</h3>
    {third?<><p>Uma tentativa é uma terceira descida de passe ou corrida mantida, com flags de conversão complementares. Passe inclui sacks; corrida inclui scrambles. Não representa a divisão entre passes lançados e dropbacks.</p><p>Ajoelhadas, spikes, abortadas, deletadas, extra points, dois pontos e no_play ficam fora. First down por penalidade não é adicionado à conversão; uma jogada mantida segue a flag da fonte.</p><p>Faixas do projeto: 1–3, 4–6 e 7 ou mais jardas, limites inclusivos. Distância desconhecida conserva seu próprio grupo.</p></>:<><p>Entrada observada: posição antes de um evento de scrimmage entre a linha de 20 jardas, inclusive, e a end zone adversária (0 &lt; yardline_100 ≤ 20). Inclui posição de penalidade, ajoelhada ou field goal; timeout isolado não cria entrada.</p><p>Uma campanha identificada por jogo + fixed_drive conta uma vez, mesmo com várias jogadas ou reentrada. Somente touchdown ofensivo confirmado nessa posse converte. TD de fora da região não cria entrada por causa de extra point ou dois pontos.</p><p>Fim de quarto 1/3 não encerra posse. Desfechos exigem evento e resultado de campanha coerentes; campanha incompleta ou contraditória bloqueia a taxa.</p></>}
    <p>{m.excludedIds.length} {third?'registros candidatos excluídos':'campanhas fora do denominador'}. {Object.entries(m.exclusions).map(([k,n])=>`${k}: ${n}`).join('; ')||'Nenhuma exclusão.'}</p>
    <h3>Procedência e garantias</h3>
    <p>Completude não demonstrada ({snapshot.data.guarantees.completeness}); cobertura esperada desconhecida ({snapshot.data.guarantees.expectedCoverage}). Conhecimento anterior ao jogo desconhecido ({snapshot.data.guarantees.temporalKnowledge}). Modelo EPA não identificado ({snapshot.data.guarantees.epaModel}); estas análises de terceiras descidas e red zone não usam EPA.</p>
    <p>Razão exata: {m.numerator}/{m.denominator}. Estado: {m.status}; denominador {m.denominatorState}. {m.ambiguousIds.length} unidades ambíguas. Definições {snapshot.data.definitionsVersion}; cálculo {snapshot.data.calculationVersion}.</p>
    <p>Fonte PBP preservada: <code>{snapshot.data.provenance.rawHash}</code></p><p>Artefato: <code>{snapshot.bundleId}</code></p><p>Ledger auditável: <code>{snapshot.data.ledgerHash}</code></p>
    <p><a href="https://nflreadr.nflverse.com/articles/dictionary_pbp.html" target="_blank" rel="noreferrer">Dicionário primário nflverse</a>. Reconciliação independente dos registros brutos documentada nesta entrega local.</p>
  </details>;
}
export function SituationalContent({d,snapshot,family,announce=true}:{d:SituationalDocument;snapshot:Snapshot;family:'third'|'redzone';announce?:boolean}) {
  const third=family==='third',m=third?d.third:d.redZone,defense=d.perspective==='def';
  const fact=compositionFact(d,family);
  const label=third?'conversões':'touchdowns ofensivos';
  const identity=teamIdentity(d.team);
  return <article className="situational-reading" style={{'--sit-team':identity.dark} as CSSProperties} data-situational={d.id} data-family={family}>
    <header className="sit-heading"><p>{d.team} · {defense?'Defesa · permitido ao ataque adversário':'Ataque'} · {d.weeks.length===2?'Semanas 1–2 inclusivas':`Semana ${d.weeks[0]}`}</p><h2>{third?(defense?'Quantas terceiras o adversário converteu?':'Quantas terceiras viraram conversão?'):(defense?'Quantas entradas adversárias terminaram em touchdown?':'Quantas entradas na red zone terminaram em touchdown?')}</h2></header>
    <div className="sit-result" aria-live={announce?'polite':'off'} aria-atomic="true"><strong data-sit-value="rate">{percent(m.ratio)??'Sem taxa'}</strong><p><b data-sit-value="ratio">{m.numerator} / {m.denominator}</b><span>{label} {defense?(third?'permitidas':'permitidos'):''} / {third?'tentativas elegíveis':'campanhas confirmadas'}</span></p></div>
    <p className="sit-caption sit-rule-note">{third?'Taxa pelas regras do projeto: tentativas elegíveis de passe e corrida, sem ajoelhadas, spikes ou jogadas anuladas ou abortadas. Exclusões e penalidades nos detalhes; não é uma estatística oficial da NFL.':'A unidade é a campanha, com a linha de 20 jardas incluída. Campanhas com posição observada na região antes de uma ajoelhada também podem entrar na amostra.'}</p>
    {m.status==='AVAILABLE' ? fact && <p className="sit-fact">{fact}</p> : <p className="sit-fact" role="status">{m.status==='NO_OPPORTUNITIES'?'A fonte está presente, mas não há oportunidades elegíveis. Denominador zero não é taxa de 0%.':'Há unidades insuficientes ou contraditórias. As contagens confirmadas não sustentam uma taxa para o recorte.'}</p>}
    {m.status==='AVAILABLE' && (third?<DistanceChart d={d}/>:<DriveChart d={d}/>)}
    {third && <section className="sit-types"><h3>Passe e corrida nas tentativas</h3><dl>{[['pass','Passe · inclui sacks'],['run','Corrida · inclui scrambles']].map(([k,label])=>{const f=d.third.byType[k];return <div key={k}><dt>{label}</dt><dd>{f.denominator} de {m.denominator} tentativas ({percent({numerator:f.denominator,denominator:m.denominator})??'sem proporção'})<small>{f.numerator} / {f.denominator} conversões ({percent(f)??'sem taxa'})</small></dd></div>;})}</dl><p>{d.third.sacks} sacks e {d.third.scrambles} scrambles incluídos. First downs por penalidade: {d.third.penaltyFirstDowns.included} em tentativas incluídas; {d.third.penaltyFirstDowns.excluded} em registros excluídos. Estes avanços não foram somados às conversões.</p></section>}
    <section className="sit-sample"><h3>O contexto da amostra</h3><p>{d.games.length} {d.games.length===1?'jogo observado':'jogos observados'}. {m.denominator} {third?'tentativas elegíveis':'campanhas confirmadas'}. {third?'Contagem da amostra, sem avaliação isolada de quarterback.':'A unidade é a campanha, não o número de jogadas dentro da região.'}</p><ul>{d.games.map(g=><li key={g.gameId}>{g.away} × {g.home} · Semana {g.week} · {defense?`Ataque de ${g.opponent} contra ${d.team}`:`Ataque de ${d.team} contra ${g.opponent}`}</li>)}</ul><p>Completude e cobertura esperada não demonstradas. Leitura descritiva dos jogos observados, sem ranking ou previsão.</p></section>
    <Method d={d} snapshot={snapshot} family={family}/>
  </article>;
}
export function SituationalReading({game,q,defaultTeam,onChoice}:{game:Game;q:URLSearchParams;defaultTeam:string;onChoice:(change:Record<string,string>)=>void}) {
  const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  useEffect(()=>{const controller=new AbortController();let active=true;setSnapshot(null);setError('');
    fetch('/__situational/',{headers:{'X-Local-Situational':'1'},signal:controller.signal,cache:'no-store'}).then(async r=>{if(!r.ok)throw new Error('O artefato situacional não está disponível nesta sessão.');return validateSnapshot(await r.json());}).then(s=>{if(active)setSnapshot(s);}).catch(e=>{if(active)setError(e instanceof Error?e.message:'Fonte situacional indisponível.');});
    return ()=>{active=false;controller.abort();};
  },[retry]);
  const family=q.get('analysis')==='third'?'third':'redzone';
  const selected=snapshot?selectDocument(snapshot,game,q,defaultTeam):null;
  const team=q.get('team')??defaultTeam,side=q.get('side')??'off',period=q.get('reading')??'game';
  return <section className="live-reading" aria-label="Análise situacional do confronto"><div className="live-controls"><div className="live-dimensions"><fieldset><legend>Lado da bola</legend><div>{[['off','Ataque'],['def','Defesa']].map(([k,label])=><button type="button" key={k} aria-pressed={side===k} onClick={()=>onChoice({side:k})}>{label}</button>)}</div></fieldset><fieldset><legend>Período da leitura</legend><div>{[['game','Deste jogo'],['2026/REG/1,2','Semanas 1–2']].map(([k,label])=><button type="button" key={k} aria-pressed={period===k} onClick={()=>onChoice({reading:k})}>{label}</button>)}</div></fieldset></div><p className="live-announcement" role="status">{team} · {side==='def'?'Defesa':'Ataque'} · {names[family]} · {period==='game'?'Deste jogo':'Semanas 1–2'}</p></div>
    {error?<div className="live-no-reading" role="alert"><h2>Fonte situacional indisponível.</h2><p>{error} Ausência não é zero.</p><button onClick={()=>setRetry(x=>x+1)}>Conferir novamente</button></div>:!snapshot?<p className="live-no-reading" role="status">Conferindo artefato situacional…</p>:selected?.error?<div className="live-no-reading" role="alert"><h2>Recorte não confirmado.</h2><p>{selected.error} Nenhuma seleção alternativa foi usada.</p></div>:selected?.absent?<div className="live-no-reading" role="status" data-availability="SOURCE_ABSENT"><h2>Sem fonte situacional deste jogo.</h2><p>O PBP preservado desta entrega contém somente 2026 REG W1–2. Este calendário não demonstra fonte para a semana {game.week}. Ausência de fonte não é zero oportunidades.</p></div>:selected?.document?<SituationalContent d={selected.document} snapshot={snapshot} family={family}/>:null}
  </section>;
}
