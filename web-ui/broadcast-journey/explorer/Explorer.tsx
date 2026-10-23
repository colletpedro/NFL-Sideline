import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import type { Game } from '../../src/services/types';
import { Logo } from '../../broadcast-experience/TeamLogo';
import { teamIdentity } from '../../broadcast-real/identity';
import { SituationalContent } from '../situational/SituationalReading';
import { compositionFact } from '../situational/compositionCopy';
import { percent, validateSnapshot, type Snapshot, type SituationalDocument } from '../situational/model';
import { activeSelection, comparison, encodePin, family, initialQuery, options, outcomes, previousHref, project, questions, resolvePins, type Question, type Slice } from './state';
import './explorer.css';

type Props={games:Game[]|null;q:URLSearchParams;onQuery:(q:URLSearchParams,options?:{replace?:boolean})=>void;calendarHref:string;error:string};
export function Explorer({games,q,onQuery,calendarHref,error}:Props) {
  const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[sourceError,setSourceError]=useState(''),[retry,setRetry]=useState(0);
  const [notice,setNotice]=useState('');
  const pinHeading=useRef<HTMLHeadingElement>(null),pinButton=useRef<HTMLButtonElement>(null);
  useEffect(()=>{let active=true;const c=new AbortController();setSnapshot(null);setSourceError('');
    fetch('/__situational/',{headers:{'X-Local-Situational':'1'},cache:'no-store',signal:c.signal}).then(async r=>{if(!r.ok)throw Error('O artefato situacional não está disponível nesta sessão.');return validateSnapshot(await r.json());}).then(s=>{if(active)setSnapshot(s);}).catch(e=>{if(active)setSourceError(e instanceof Error?e.message:'Fonte indisponível.');});
    return ()=>{active=false;c.abort();};
  },[retry]);
  useEffect(()=>{if(!games)return;const next=initialQuery(q,games);if(next.toString()!==q.toString())onQuery(next,{replace:true});},[games,q,onQuery]);
  const game=games?.find(g=>g.gameId===q.get('game')), team=q.get('team')??'',side=q.get('side')??'off';
  const question=(q.get('question')??'distance') as Question,refine=q.get('refine')??'all';
  const selection=snapshot&&game?activeSelection(snapshot,game,q):null,d=selection?.document;
  const pins=snapshot?resolvePins(q,snapshot):{slices:[]};
  const identity=teamIdentity(team || 'NYJ');
  const update=(change:Record<string,string|null>)=>{const n=new URLSearchParams(q);for(const [k,v] of Object.entries(change))if(v===null)n.delete(k);else n.set(k,v);setNotice('');onQuery(n);};
  const chooseQuestion=(key:Question)=>{const saved=q.get(`refine-${key}`)??'all';update({question:key,analysis:family(key),refine:Object.prototype.hasOwnProperty.call(options(key),saved)?saved:'all',...(Object.prototype.hasOwnProperty.call(questions,question)&&Object.prototype.hasOwnProperty.call(options(question),refine)?{[`refine-${question}`]:refine}:{})});};
  const active:Slice|undefined=d&&snapshot?{document:d.id,question,refine,bundle:snapshot.bundleId}:undefined;
  const changePins=(slices:Slice[],announcement:string)=>{const n=new URLSearchParams(q);n.delete('pin');slices.forEach(p=>n.append('pin',encodePin(p)));onQuery(n);setNotice(announcement);};
  const pin=()=>{if(!active)return;if(pins.slices.some(p=>encodePin(p)===encodePin(active))){setNotice('Este recorte já está fixado.');return;}if(pins.slices.length===2){setNotice('Dois recortes fixados. Use Substituir ou Remover em um deles.');return;}changePins([...pins.slices,active],'Recorte fixado. Ele permanece igual durante a investigação.');};
  const teams=games?Array.from(new Map(games.flatMap(g=>[g.homeTeam,g.awayTeam]).map(t=>[t.teamAbbr,t])).values()).sort((a,b)=>a.teamName.localeCompare(b.teamName)):[];
  const teamGames=games?.filter(g=>[g.homeTeam.teamAbbr,g.awayTeam.teamAbbr].includes(team))??[];
  const switchTeam=(next:string)=>{const target=games?.find(g=>g.week===(game?.week??Number(q.get('week'))) && [g.homeTeam.teamAbbr,g.awayTeam.teamAbbr].includes(next));update({team:next,game:target?.gameId??q.get('game'),example:null,entry:null,observation:null});};
  return <div className="explorer" style={{'--sit-team':identity.dark} as CSSProperties}>
    <a href="#explorer-result" className="skip-link">Ir ao resultado</a>
    <header className="site-header"><div className="explorer-mast"><Link className="brand" to={calendarHref}>NFL <strong>SIDELINE</strong></Link><span>Explorador experimental · v1</span><Link to={previousHref(q)}>Voltar à experiência anterior</Link></div></header>
    <main className="explorer-page"><nav className="explorer-return" aria-label="Origem"><Link to={calendarHref}>Voltar ao calendário e à busca · semana {q.get('week')??1}</Link><Link to={previousHref(q,true)}>Abrir resumo atual</Link></nav>
      <h1>Explorador de recortes</h1>
      <section className="explorer-desk" aria-label="Investigação ativa">
        <div className="explorer-context"><Logo team={identity}/><div><strong>{team||'Conferindo contexto'} · {side==='def'?'Defesa':'Ataque'}</strong><p>{game?`${game.awayTeam.teamAbbr} × ${game.homeTeam.teamAbbr} · ${game.season} · ${q.get('reading')==='2026/REG/1,2'?'W1–2 inclusivas':`W${game.week}`}`:'Jogo não confirmado'}{q.get('example')==='nyj'?' · Exemplo inicial':''}</p></div><details className="explorer-context-editor"><summary>Trocar time ou jogo</summary><div><label>Time<select value={team} onChange={e=>switchTeam(e.target.value)}><option value="" disabled>Escolher time</option>{teams.map(t=><option key={t.teamAbbr} value={t.teamAbbr}>{t.teamName} ({t.teamAbbr})</option>)}</select></label><label>Jogo<select value={game?.gameId??''} onChange={e=>update({game:e.target.value,example:null,entry:null,observation:null})}><option value="" disabled>Escolher jogo</option>{teamGames.map(g=><option key={g.gameId} value={g.gameId}>W{g.week} · {g.awayTeam.teamAbbr} × {g.homeTeam.teamAbbr}</option>)}</select></label></div></details></div>
        <div className="explorer-context-tools"><fieldset><legend>Perspectiva</legend>{[['off','Ataque'],['def','Defesa']].map(([k,l])=><button key={k} aria-pressed={side===k} onClick={()=>update({side:k,example:null})}>{l}</button>)}</fieldset><label>Período<select value={q.get('reading')??'game'} onChange={e=>update({reading:e.target.value,example:null})}><option value="game">Deste jogo</option><option value="2026/REG/1,2">Semanas 1–2</option>{q.has('reading')&&!['game','2026/REG/1,2'].includes(q.get('reading')!)&&<option value={q.get('reading')!}>Período inválido</option>}</select></label></div>
        <nav className="explorer-questions" aria-label="Perguntas disponíveis">{Object.entries(questions).map(([key,label])=><button key={key} aria-pressed={question===key} onClick={()=>chooseQuestion(key as Question)}><span className="explorer-question-full">{label}</span><span className="explorer-question-short">{key==='distance'?'Por distância':key==='type'?'Passe e corrida':'Red zone'}</span></button>)}</nav>
        <div id="explorer-result" className="explorer-result" tabIndex={-1}>
          {error?<div role="alert"><h2>Calendário indisponível</h2><p>{error}</p></div>:!games?<p role="status">Conferindo calendário preservado…</p>:!game?<div role="alert"><h2>Contexto não confirmado</h2><p>O jogo ou time da URL não corresponde ao calendário. Nenhum contexto alternativo foi escolhido. Use a troca de contexto ou volte ao calendário.</p></div>:sourceError?<div role="alert"><h2>Fonte indisponível</h2><p>{sourceError} Ausência não é zero.</p><button onClick={()=>setRetry(n=>n+1)}>Conferir novamente</button></div>:!snapshot?<p role="status">Conferindo fonte situacional…</p>:selection?.error?<div role="alert"><h2>Recorte não confirmado</h2><p>{selection.error}</p><button onClick={()=>update({team:game.awayTeam.teamAbbr,side:'off',reading:'game',question:'distance',analysis:'third',refine:'all',entry:null,observation:null})}>Usar ataque do visitante neste jogo</button></div>:selection?.absent?<div role="status" data-availability="SOURCE_ABSENT"><h2>Sem fonte situacional deste jogo</h2><p>O arquivo preservado contém somente 2026 REG W1–2. Não há fonte para W{game.week}. O contexto foi mantido; ausência de fonte não é zero oportunidades.</p></div>:d&&<>
            <SliceResult d={d} question={question} refine={refine} onRefine={v=>update({refine:v,[`refine-${question}`]:v})}/>
            <button ref={pinButton} className="explorer-pin" onClick={pin}>Fixar recorte</button><span className="explorer-pin-help">Até dois recortes; valores descritivos.</span>
            <details className="explorer-deepen"><summary>Aprofundar: amostra, fatos, método e procedência</summary><p>O documento completo abaixo conserva a população original. O refinamento destacado acima não modifica esta leitura.</p><SituationalContent d={d} snapshot={snapshot} family={family(question)} announce={false}/></details>
          </>}
        </div>
        <p className="explorer-announcement" role="status" aria-live="polite" aria-atomic="true">{notice || (d?`${d.team}, ${d.perspective==='def'?'defesa':'ataque'}, semanas ${d.weeks.join(' e ')}. ${questions[question]}, ${options(question)[refine]}. ${project(d,question,refine).numerator} de ${project(d,question,refine).denominator} ${project(d,question,refine).unit}.`:'')}</p>
      </section>
      {(pins.slices.length>0||pins.error)&&snapshot&&<section className="explorer-comparison" aria-label="Recortes fixados"><h2 ref={pinHeading} tabIndex={-1}>Recortes fixados</h2><p>Retratos da fonte preservada. A investigação ativa não altera estes recortes.</p>{pins.error?<div role="alert"><p>{pins.error}</p><button onClick={()=>changePins([],'Recortes inválidos removidos.')}>Remover recortes da URL</button></div>:<>
        {pins.slices.length===1&&<p>Consulte outro recorte e use Fixar recorte para colocá-lo ao lado.</p>}
        {pins.slices.length===2&&<ComparisonNote a={pins.slices[0]} b={pins.slices[1]} snapshot={snapshot}/>}
        <div className="explorer-pins">{pins.slices.map((p,i)=>{const doc=snapshot.data.documents.find(x=>x.id===p.document)!;return <article key={i}><h3>Recorte {i+1} · {doc.team} · {doc.perspective==='def'?'Defesa':'Ataque'}</h3><p>{doc.season} {doc.phase} · W{doc.weeks.join('–')} · {questions[p.question]} · {options(p.question)[p.refine]}</p><ul>{doc.games.map(g=><li key={g.gameId}>W{g.week} · {g.away} × {g.home} · adversário {g.opponent}</li>)}</ul><PinnedValue d={doc} slice={p}/><div className="explorer-pin-actions"><button onClick={()=>{changePins(pins.slices.filter((_,j)=>j!==i),'Recorte removido.');(pins.slices.length===1?pinButton.current:pinHeading.current)?.focus();}}>Remover recorte {i+1}</button><button disabled={!active || pins.slices.some((x,j)=>j!==i&&active&&encodePin(x)===encodePin(active))} onClick={()=>active&&changePins(pins.slices.map((x,j)=>j===i?active:x),'Recorte substituído pela investigação ativa.')}>Substituir recorte {i+1} pelo atual</button></div><details><summary>Identidade e versão da fonte</summary><p>Documento {doc.id} · contrato {snapshot.data.contractVersion} · definições {snapshot.data.definitionsVersion} · cálculo {snapshot.data.calculationVersion}</p><code>{p.bundle}</code><p>Fonte bruta: <code>{snapshot.data.provenance.rawHash}</code></p></details></article>;})}</div>
      </>}</section>}
      <p className="explorer-footnote">Arquivo local preservado. Completude e cobertura esperada não demonstradas; sem ranking, previsão ou inferência causal.</p>
    </main>
  </div>;
}
export function SliceResult({d,question,refine,onRefine}:{d:SituationalDocument;question:Question;refine:string;onRefine:(v:string)=>void}) {
  const value=project(d,question,refine),third=question!=='outcomes',m=third?d.third:d.redZone;
  const fact=compositionFact(d,family(question));
  const groups=question==='distance'?d.third.byDistance:question==='type'?d.third.byType:null;
  const chartEntries=Object.keys(options(question)).filter(k=>k!=='all'&&(groups?k in groups:k in d.redZone.outcomes)).map(k=>[k,groups?groups[k]:d.redZone.outcomes[k]] as const);
  const max=groups?Math.max(1,...Object.values(groups).map(f=>f.denominator)):Math.max(1,m.denominator);
  return <section aria-label="Resultado do recorte" data-document={d.id} data-question={question} data-refine={refine}>
    <h2>{questions[question]}</h2>
    <p className="explorer-owner">{d.perspective==='def'?`Permitido ao ataque adversário contra ${d.team}`:`Ataque de ${d.team}`} · {d.games.length} {d.games.length===1?'jogo observado':'jogos observados'}</p>
    <div className="sit-result"><strong>{percent(value.rate)??'Sem taxa'}</strong><p><b>{value.numerator} / {value.denominator}</b><span>{value.label} / {value.unit}{refine!=='all'&&third?' neste grupo':' confirmadas'}</span></p></div>
    <div className="explorer-local"><label>{question==='distance'?'Distância necessária':question==='type'?'Tipo de tentativa':'Desfecho destacado'}<select value={refine} onChange={e=>onRefine(e.target.value)}>{Object.entries(options(question)).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><p>{third?'Distância e tipo são distribuições separadas; não há cruzamento entre elas.':'O destaque conserva todas as campanhas no denominador.'}</p></div>
    {m.status==='AVAILABLE'&&value.denominator===0&&<p>Não há tentativas neste grupo. O documento completo continua disponível; zero denominador não é taxa de 0%.</p>}
    <p className="sit-caption sit-rule-note">{third?'Taxa pelas regras do projeto: tentativas elegíveis de passe e corrida, sem ajoelhadas, spikes ou jogadas anuladas ou abortadas. Exclusões e penalidades nos detalhes; não é uma estatística oficial da NFL.':'A unidade é a campanha, com a linha de 20 jardas incluída. Campanhas com posição observada na região antes de uma ajoelhada também podem entrar na amostra.'}</p>
    {m.status==='AVAILABLE'?<>
      {!third&&refine!=='all'&&<p>Taxa de TD do documento: {d.redZone.numerator}/{d.redZone.denominator} ({percent(d.redZone.ratio)}). O destaque conta {outcomes[refine].toLowerCase()} sobre as mesmas {d.redZone.denominator} campanhas, sem filtrar a população.</p>}
      {fact&&<p className="explorer-fact">No documento completo: {fact}</p>}
      <figure className="explorer-chart"><figcaption>{third?'Conversões / tentativas por grupo':'Campanhas por desfecho'} · escala de contagem 0 a {max}</figcaption>{chartEntries.map(([key,v])=>{const f=typeof v==='number'?{numerator:v,denominator:m.denominator}:v;const label=options(question)[key]??key;return <div key={key} className={`explorer-bar-row${refine===key?' is-highlighted':''}`}><strong>{label}</strong><div className="explorer-bar" role="img" aria-label={`${label}: ${f.numerator} de ${f.denominator} ${value.unit}.`}><span style={{width:`${100*(third?f.denominator:f.numerator)/max}%`}}>{third&&<i style={{width:`${f.denominator?100*f.numerator/f.denominator:0}%`}}/>}</span></div><span>{f.numerator} / {f.denominator}<small>{percent(f)??'Sem oportunidades'}</small>{question==='type'&&<small>{f.denominator} de {m.denominator} tentativas · {percent({numerator:f.denominator,denominator:m.denominator})??'sem proporção'}</small>}</span></div>;})}<p className="sit-caption">{third?'Barra clara: tentativas; parte escura: conversões. Grupos na mesma escala; sem média entre taxas.':'Cada barra conta um desfecho sobre todas as campanhas confirmadas; o destaque não altera o denominador.'}</p></figure>
    </>:<p className="explorer-fact">{m.status==='NO_OPPORTUNITIES'?'Fonte presente, sem oportunidades elegíveis. Denominador zero não é taxa de 0%.':'Há unidades insuficientes ou contraditórias. Contagens confirmadas não sustentam taxa; consulte o documento completo e as unidades ambíguas nos detalhes.'}</p>}
  </section>;
}
function PinnedValue({d,slice}:{d:SituationalDocument;slice:Slice}) {const v=project(d,slice.question,slice.refine);return <p className="explorer-pinned-value"><strong>{percent(v.rate)??'Sem taxa'}</strong><span>{v.numerator} / {v.denominator} · {v.label} / {v.unit} · {v.status}</span></p>;}
function ComparisonNote({a,b,snapshot}:{a:Slice;b:Slice;snapshot:Snapshot}) {const {compatible,overlap}=comparison(a,b,snapshot);return <div className="explorer-comparison-note"><p>{compatible?'Mesma família, recorte e unidade. Valores descritivos lado a lado; não demonstram superioridade ou significância.':'Métricas ou refinamentos diferentes. A leitura lado a lado é contextual; não há diferença numérica entre elas.'}</p>{overlap&&<p>Períodos sobrepostos: há jogo em comum. As amostras não são independentes.</p>}</div>;}
