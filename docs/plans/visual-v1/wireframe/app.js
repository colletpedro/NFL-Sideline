/* Presentation prototype only. Fixed contract fixtures, no generation/network. */
const fixtures = window.visualFixtures;
const names = {'complete-matchup':'Confronto completo',opportunity:'Oportunidade localizada',opposition:'Ataque e defesa favoráveis','attack-not-demonstrated':'Ataque sem produção positiva','both-negative':'Sinais negativos',variation:'Variação entre semanas',zero:'Zero observado','tiny-sign':'Positivo muito próximo de zero',tie:'Alternativas empatadas','both-sides':'Oportunidades dos dois lados',partial:'Dados de apenas um lado',missing:'Sem dados',historical:'Referência histórica','coverage-gap':'Lacuna de cobertura','two-weeks':'Amostra de duas semanas','general-represented':'Panorama geral representado','uneven-weeks':'Semanas diferentes','negative-tiny-sign':'Negativo muito próximo de zero',outlier:'Extremo semanal','independent-opportunity':'Oportunidade independente'};
const $ = selector => document.querySelector(selector);
const el = (tag, className, text) => { const node=document.createElement(tag); if(className)node.className=className;if(text!==undefined)node.textContent=text;return node; };
for(const [key] of Object.entries(fixtures)){const option=el('option','',names[key]||key);option.value=key;$('#scenario').append(option);}
const foundationName = f => ({PASS:'Passe',RUSH:'Corrida',GENERAL:'Panorama geral'})[f];
function render(name){
 const doc=fixtures[name], container=$('#reading');container.replaceChildren();
 const evidence=Object.fromEntries(doc.evidence.map(e=>[e.id,e]));const series=Object.fromEntries(doc.series.map(s=>[s.id,s.evidenceIds.map(id=>evidence[id])]));const restrictions=Object.fromEntries(doc.restrictions.map(r=>[r.id,r]));const encounters=Object.fromEntries(doc.encounters.map(e=>[e.id,e]));const findings=Object.fromEntries(doc.findings.map(f=>[f.id,f]));
 const numerical=doc.evidence.map(e=>Number(e.value));const representable=numerical.every((n,i)=>Number.isFinite(n)&&(n!==0||Number(doc.evidence[i].value)===0&&/^[-]?0(?:\.0+)?$/.test(doc.evidence[i].value)));
 const extent=Math.max(...numerical.map(Math.abs),0)||.1;
 const game=el('section','game');game.append(el('div','eyebrow',`TEMPORADA ${doc.game.season} / SEMANA ${doc.game.week} / PRÉ-JOGO`));game.append(el('h1','',`${doc.game.awayTeam} × ${doc.game.homeTeam}`));game.append(el('p','muted','Leitura dos recortes observados · Sem estimativa de vencedor'));container.append(game);
 const top=el('section','summary');top.append(el('div','eyebrow','LEITURA RÁPIDA'));
 const highlights=doc.presentation.highlightFindingIds.map(id=>findings[id]);
 if(!highlights.length){top.append(el('h2','','Não há um confronto comparável neste contexto.'),el('p','muted','Os cartões mostram os dados disponíveis e o que está faltando.'));}
 else{
  top.append(el('h2','',highlights.length>1?'Há mais de um achado com a mesma prioridade.':highlights[0].title));
  const list=el('ul');for(const f of highlights){const e=encounters[f.encounterId];list.append(el('li','',`${foundationName(e.foundation)} de ${e.attackTeam} contra ${e.defenseTeam}: ${f.summary}`));}top.append(list);
  const limits=[...new Set(highlights.map(f=>restrictions[f.primaryRestrictionId].text))];for(const text of limits)top.append(el('p','limit',text));
 }
 container.append(top);
 const head=el('div','section-head');head.append(el('h2','','Os quatro encontros'),el('span','','EPA semanal · mesma escala em todos os cartões'));container.append(head);
 const grid=el('div','grid');container.append(grid);
 function card(e){
  const f=doc.findings.find(f=>f.encounterId===e.id);const card=el('article','card'+(f&&doc.presentation.highlightFindingIds.includes(f.id)?' primary':''));
  card.append(el('div','eyebrow',e.foundation==='GENERAL'?'CONTEXTO ADICIONAL':`${foundationName(e.foundation).toUpperCase()} / ATAQUE × DEFESA`));card.append(el('h3','',`${e.attackTeam} → ${e.defenseTeam}`));
  const a=series[e.attackSeriesId]||[],d=series[e.defenseSeriesId]||[];
  const period=rows=>rows.length?`${rows[0].season} · semanas ${rows.map(e=>e.week).join(', ')}`:'sem observações';
  card.append(el('p','period',`Ataque: ${period(a)}`),el('p','period',`Defesa: ${period(d)}`));
  if(f)card.append(el('p','relation',f.title));
  else if(e.state==='REPRESENTED_BY')card.append(el('p','relation','Mesmo perfil e cobertura já representados por fundamento específico.'));
  else card.append(el('p','empty',e.unavailableReason==='MISSING_BOTH'?'Sem dados de ataque e defesa neste recorte.':e.unavailableReason==='INCOMPATIBLE_ORIGIN'?'Os recortes pertencem a períodos incompatíveis.':'Faltam dados de um lado. A série disponível não permite concluir sobre o confronto.'));
  if(a.length||d.length){
   if(representable){const plot=el('div','chart');plot.setAttribute('role','img');plot.setAttribute('aria-label',`EPA observado de ${e.attackTeam} no ataque e permitido por ${e.defenseTeam}. Valores na tabela expansível. Zero ao centro; negativo à esquerda.`);
    const axis=el('div','axis');axis.append(el('span','',''));const ticks=el('div','ticks');for(const n of [-extent,0,extent])ticks.append(el('span','',n===0?'0':n.toLocaleString('pt-BR',{maximumSignificantDigits:3})));axis.append(ticks,el('span','value','EPA/jogada'));plot.append(axis);
    for(const [rows,label,def] of [[a,`${e.attackTeam} · ataque`,false],[d,`${e.defenseTeam} · permitido`,true]]){
     plot.append(el('div','series-label',`${def?'◆':'●'} ${label}`));if(!rows.length)plot.append(el('p','chart-note','Sem observações.'));
     for(const row of rows){const r=el('div','point-row');r.append(el('span','',`S${row.week}`));const track=el('div','track');const point=el('span','point'+(def?' def':''));point.style.left=`${50+50*Number(row.value)/extent}%`;track.append(point);r.append(track,el('span','value'+(row.displayValue.includes('<')?' tiny':''),row.displayValue));plot.append(r);}
    }card.append(plot);
   }else card.append(el('p','limit','Escala gráfica indisponível para estes valores. Consulte os valores exatos na tabela.'));
   card.append(el('p','chart-note','Defesa: menor EPA permitido é melhor. Zero não é a média da liga.'));
   card.append(el('p','chart-note','Cada ponto é uma média semanal. Volume por fundamento não informado.'));
  }
  if(f)card.append(el('p','limit',restrictions[f.primaryRestrictionId].text));
  const detail=el('details');detail.append(el('summary','','Ver dados e definição'));
  if(f)detail.append(el('p','detail-copy',f.summary));
  detail.append(el('p','detail-copy','EPA mede pontos esperados adicionados por jogada elegível. As séries são observações separadas: não estimam o EPA deste jogo e não são somadas para produzir uma vantagem.'));
  const table=el('table');const caption=el('caption','',`Valores observados · ${foundationName(e.foundation)}`);table.append(caption);const heading=el('tr');for(const text of ['Papel','Semana','EPA','Jogadas']){const th=el('th','',text);th.scope='col';heading.append(th);}const thead=el('thead');thead.append(heading);table.append(thead);const body=el('tbody');for(const [rows,label] of [[a,`${e.attackTeam} ataque`],[d,`${e.defenseTeam} defesa`]])for(const row of rows){const tr=el('tr');for(const text of [label,String(row.week),row.value,row.plays===null?'Não informado':String(row.plays)])tr.append(el('td','',text));body.append(tr);}table.append(body);detail.append(table);card.append(detail);return card;
 }
 for(const team of [doc.game.awayTeam,doc.game.homeTeam])for(const f of ['PASS','RUSH'])grid.append(card(doc.encounters.find(e=>e.attackTeam===team&&e.foundation===f)));
 const general=doc.encounters.filter(e=>e.foundation==='GENERAL'&&e.state!=='UNAVAILABLE');if(general.length){const detail=el('details');detail.append(el('summary','',`Panorama geral · ${general.length} recorte(s)`));const g=el('div','grid');for(const e of general)g.append(card(e));detail.append(g);container.append(detail);}
 if(doc.links.length){const relations=el('section','methodology');relations.append(el('h2','','Relações entre os achados'));for(const link of doc.links)relations.append(el('p','detail-copy',link.relation==='INDEPENDENT_OPPORTUNITY'?'Há uma oportunidade independente do outro lado; ela não refuta diretamente o primeiro achado.':'Outro fundamento do mesmo ataque limita a generalização do destaque.'));container.append(relations);}
 const method=el('section','methodology');method.append(el('h2','','O que este recorte permite dizer'));const ul=el('ul');for(const id of doc.presentation.globalRestrictionIds)ul.append(el('li','',restrictions[id].text));ul.append(el('li','','Ausência de uma semana não distingue folga de falha na fonte.'));method.append(ul);container.append(method);
 const market=el('details');market.append(el('summary','','Mercado · camada independente'));market.append(el('p','detail-copy','Sem cotações neste protótipo. Probabilidades de mercado não participam da seleção ou da interpretação destes cartões.'));container.append(market);
}
$('#scenario').addEventListener('change',event=>render(event.target.value));
$('#compact').addEventListener('click',()=>{const active=document.body.classList.toggle('compact');$('#compact').setAttribute('aria-pressed',String(active));$('#compact').textContent=active?'Voltar à largura livre':'Simular celular';});
render($('#scenario').value);
