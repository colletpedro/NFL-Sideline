const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const origin='http://127.0.0.1:18092', out=path.join(__dirname,'evidence');
const report={layouts:[],cases:[],history:[],requests:[],errors:[]};
const grouped=s=>s.replace(/\B(?=(\d{3})+(?!\d))/g,'.');
function formatted(r, places, percent=false, signed=false) {
 if(!r)return null;
 const negative=r.numerator.startsWith('-'), [a,b='']=r.numerator.replace('-','').split('.');
 const n=BigInt(a+b)*(percent?100n:1n),d=BigInt(r.denominator)*10n**BigInt(b.length),scale=10n**BigInt(places);
 const rounded=n*scale/d+(n*scale%d*2n>=d?1n:0n),sign=n===0n?'':negative?'−':signed?'+':'';
 if(n!==0n&&rounded===0n)return sign+'<'+(places?'0,'+'0'.repeat(places-1)+'1':'1')+(percent?'%':'');
 return sign+(rounded/scale).toString()+(places?','+(rounded%scale).toString().padStart(places,'0'):'')+(percent?'%':'');
}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE,headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>report.requests.push({method:r.method(),url:r.url()}));
 const catalog=await (await page.request.get(origin+'/__observations/',{headers:{'X-Local-Observations':'1'}})).json(),entry=catalog.bundles[0];
 assert.equal(entry.status,'READY');assert.equal(entry.observations.length,48);report.sessionId=catalog.sessionId;
 const docs=await Promise.all(entry.observations.map(async s=>(await (await page.request.get(`${origin}/__observations/${entry.entryId}/${s.observationId.slice(7)}`,{headers:{'X-Local-Observations':'1','X-Observation-Session':catalog.sessionId}})).json()).document));
 const pick=(team,weeks)=>docs.find(d=>d.subject.team===team&&d.subject.role==='off'&&d.subject.foundation==='general'&&d.request.period.weeks.join(',')===weeks);
 const bal1=pick('BAL','1'),bal2=pick('BAL','2'),bal12=pick('BAL','1,2'),gap=pick('BAL','3'),ne=pick('NE','19,20,21,22'),dal=pick('DAL','1');
 const route=(game,week,d,extra='')=>`/?season=2026&week=${week}&filter=all${game?'&game='+game:''}${d?'&entry='+entry.entryId+'&observation='+encodeURIComponent(d.observationId):''}${extra}`;
 const g1='2026_01_BAL_IND',g2='2026_02_NO_BAL',g3='2026_03_BAL_DAL',gn='2026_03_NE_JAX',g0='2026_01_GB_MIN';
 const ready=async()=>{await page.waitForFunction(()=>!document.querySelector('[role=status]')?.textContent.includes('Conferindo'));await page.locator('.journey-source').waitFor({state:'hidden'});};
 const open=async url=>{await page.goto(origin+url);await ready();await page.evaluate(()=>document.fonts.ready);};
 const read=async(d,r)=>{await page.waitForFunction(({id,r})=>document.querySelector('[data-relation]')?.getAttribute('data-relation')===r&&document.querySelector('.obs-inspection')?.textContent.includes(id),{id:d.observationId,r});await page.locator('.real-reading').waitFor();assert.equal(await page.locator('[data-relation]').getAttribute('data-relation'),r);assert((await page.locator('.obs-inspection').textContent()).includes(d.observationId));};
 const shot=async name=>{await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});};
 console.log('Start path');await open('/');await page.locator('.journey-games').waitFor();const defaultQ=new URL(page.url()).searchParams;assert.equal(defaultQ.get('season'),'2026');assert.notEqual(defaultQ.get('week'),'3');report.initialWeek=defaultQ.get('week');
 // Complete path with real clicks; prior preferences are deliberately hostile.
 await page.evaluate(()=>sessionStorage.setItem('broadcast-real-choice-v1',JSON.stringify({entryId:'real-recovery',observationId:'invalid'})));
 await open(route(null,1));await page.getByLabel('Exibir jogos').selectOption('participants');await page.getByRole('link',{name:'Abrir confronto BAL IND',exact:true}).click();await page.getByRole('heading',{name:'O que o arquivo permite abrir'}).waitFor();
 assert((await page.locator('.journey-empty').allTextContents()).some(t=>t.includes('Indianapolis')));
 const individual=page.getByRole('region',{name:'Leituras do jogo'});await individual.locator(`a[href*='${encodeURIComponent(bal1.observationId)}']`).click();await read(bal1,'individual');
 assert.equal(new URL(page.url()).searchParams.get('filter'),'participants');report.history.push({step:'calendar -> game -> nominal individual',url:page.url()});
 await page.getByRole('button',{name:'Explorar composição',exact:true}).click();await page.getByText('Precisão e contagens',{exact:false}).first().click();await page.waitForURL('**details=open**');
 await page.reload();await read(bal1,'individual');assert.equal(await page.locator('.obs-details').first().getAttribute('open'),'');assert.equal(await page.locator('#chart-counts').count(),1);report.history.push({step:'reload with details/composition',url:page.url()});
 await page.goBack();await page.getByRole('heading',{name:'O que o arquivo permite abrir'}).waitFor();await page.goForward();await read(bal1,'individual');
 await page.getByRole('link',{name:'Voltar ao confronto',exact:true}).click();await page.getByRole('link',{name:'Voltar ao calendário · semana 1',exact:true}).click();await page.locator('.journey-games').waitFor();assert.equal(await page.getByLabel('Semana',{exact:true}).inputValue(),'1');assert.equal(await page.getByLabel('Exibir jogos').inputValue(),'participants');report.history.push({step:'explicit return preserves week and filter',url:page.url()});
 console.log('Path/history passed');
 // Real categories, invalid and absent IDs.
 for(const [g,w,d,r,name] of [[g1,1,bal1,'individual','bal-individual'],[g2,2,bal2,'individual','bal-week2'],[g2,2,bal12,'includes','bal-inclusive'],[g3,3,gap,'gap','bal-gap'],[gn,3,ne,'archive','ne-archive']]){
  await open(route(g,w,d));await read(d,r);if(d.totals){assert.equal(await page.locator('[data-value=epa]').innerText(),formatted(d.values.epa,d.presentation.epaDecimals,false,true));}else{assert.equal(await page.locator('[data-value=epa]').count(),0);assert((await page.locator('.real-reading').innerText()).includes('Sem fonte'));}
  report.cases.push({name,url:page.url(),observationId:d.observationId,relation:r});await shot(name+'-1440');
 }
 await open(route(g2,2,bal2));await page.getByLabel('Recorte do arquivo').selectOption(`${entry.entryId}|${bal1.observationId}`);await read(bal1,'other');await page.getByLabel('Recorte do arquivo').selectOption(`${entry.entryId}|${bal12.observationId}`);await read(bal12,'includes');
 await open(route(g1,1,dal));assert.equal(await page.locator('[data-relation]').getAttribute('data-relation'),'incompatible');assert.equal(await page.locator('.real-reading').count(),0);await shot('incompatible-1440');report.cases.push({name:'incompatible URL blocked',url:page.url()});
 await open(route('invalid',1,bal1));assert.equal(await page.locator('[data-relation]').getAttribute('data-relation'),'unverified');
 await open(route(g1,1,{observationId:'sha256:'+'0'.repeat(64)}));assert.equal(await page.getByRole('heading',{name:'Observação não encontrada.'}).count(),1);assert.equal(await page.locator('.real-reading').count(),0);
 await open(route(g3,3));assert((await page.locator('.journey-score').innerText()).includes('Resultado não disponível neste arquivo'));assert(!(await page.locator('.journey-score').innerText()).includes('agendado'));await shot('gap-matchup-1440');
 await open(route(g0,1));assert((await page.locator('.journey-empty').allTextContents()).filter(t=>t.includes('nenhuma leitura disponível')).length===2);await shot('no-readings-1440');report.cases.push({name:'no participant readings',url:page.url()});
 console.log('Real categories passed');
 // Every real DTO is shown in a legitimate context; no saved DTO input.
 for(const d of docs){const g=d.subject.team==='NE'?gn:d.request.period.weeks.includes(3)?g3:d.subject.team==='DAL'?'2026_01_DAL_NYG':d.request.period.weeks.length===1&&d.request.period.weeks[0]===2?g2:g1;
  await open(route(g,g===g3||g===gn?3:g===g2?2:1,d));await page.locator('.real-reading').waitFor();assert((await page.locator('.obs-inspection').textContent()).includes(d.dtoId));
  if(d.totals){assert.equal(await page.locator('[data-value=volume]').innerText(),grouped(d.totals.eligibleN));assert.equal(await page.locator('[data-value=epa]').innerText(),formatted(d.values.epa,d.presentation.epaDecimals,false,true));assert.equal(await page.locator('[data-value=success]').innerText(),formatted(d.values.successRate,d.presentation.ratePercentDecimals,true));}
  const text=await page.locator('.real-reading').innerText();assert(text.includes('Cobertura esperada desconhecida')&&text.includes('Conhecimento anterior ao jogo não demonstrado'));assert((await page.locator('.obs-inspection').textContent()).includes('UNKNOWN'));
 }
 report.realDocumentsReconciled=48;
 console.log('48 DTOs passed');
 // Responsive full journeys and enlarged text, with details expanded.
 for(const width of [1440,900,390,320])for(const text of [100,200])for(const [name,url] of [['calendar',route(null,1)],['matchup',route(g2,2)],['reading',route(g2,2,bal12,'&details=open&composition=open')]]){
  await page.setViewportSize({width,height:1000});await open(url);await page.evaluate(size=>document.documentElement.style.fontSize=size+'px',16*text/100);
  const sizes=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth}));assert.equal(sizes.scroll,sizes.viewport,`${name} ${width} ${text}`);report.layouts.push({name,width,text,...sizes});
  if(text===100||width===320)await shot(`${name}-${width}-text${text}`);
 }
 console.log('Layouts passed');
 // Keyboard actions and no invisible focus.
 await page.setViewportSize({width:390,height:900});await open(route(g1,1,bal1));for(let i=0;i<15 && await page.evaluate(()=>document.activeElement.textContent)!=='Ir ao conteúdo';i++) await page.keyboard.press('Shift+Tab');assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Ir ao conteúdo');assert.notEqual(await page.locator('.skip-link').evaluate(el=>getComputedStyle(el).outlineStyle),'none');await page.keyboard.press('Enter');
 await page.getByLabel('Recorte do arquivo').focus();await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');assert.equal(await page.getByLabel('Recorte do arquivo').evaluate(el=>el===document.activeElement),true);
 await page.getByRole('button',{name:'Explorar composição',exact:true}).focus();await page.keyboard.press('Enter');assert.equal(await page.locator('#chart-counts').count(),1);report.keyboard='skip link, select, Enter composition, visible focus verified';await shot('keyboard-390');
 console.log('Keyboard passed');
 // Frozen session failures: calendar survives, retry explicit, no stale numbers.
 const catPattern='**/__observations/';
 await page.route(catPattern,r=>r.abort());await page.goto(origin+route(null,1));await page.getByRole('button',{name:'Recarregar arquivo de leituras'}).waitFor();await page.locator('.journey-games').waitFor();assert.equal(await page.locator('.journey-games li').count(),16);await shot('archive-failure-390');await page.unroute(catPattern);await page.getByRole('button',{name:'Recarregar arquivo de leituras'}).click();await ready();report.cases.push({name:'archive failure isolated + explicit recovery'});
 await page.route('**/data/manifest.json',r=>r.abort());await page.goto(origin+route(g1,1,bal1));await page.getByRole('button',{name:'Recarregar calendário'}).waitFor();await page.locator('.real-reading').waitFor();assert.equal(await page.locator('[data-relation]').getAttribute('data-relation'),'unverified');await shot('calendar-failure-390');await page.unroute('**/data/manifest.json');await page.getByRole('button',{name:'Recarregar calendário'}).click();await read(bal1,'individual');report.cases.push({name:'calendar failure isolated + explicit recovery'});
 await page.route('**/__observations/real-recovery/*',r=>r.fulfill({status:409,contentType:'application/json',body:'{"error":"OBSERVATION_SESSION_CHANGED"}'}));await page.goto(origin+route(g1,1,bal1));await page.getByRole('button',{name:'Recarregar arquivo de leituras'}).waitFor();assert.equal(await page.locator('.real-reading').count(),0);await shot('session-failure-390');await page.unroute('**/__observations/real-recovery/*');await page.getByRole('button',{name:'Recarregar arquivo de leituras'}).click();await read(bal1,'individual');report.cases.push({name:'divergent session clears readings'});
 // Late response after selecting a different nominal document cannot relabel it.
 let release;const gate=new Promise(r=>release=r);let intercepted=false;
 await page.route('**/__observations/real-recovery/*',async r=>{if(!intercepted){intercepted=true;await gate;}await r.continue();});
 await page.goto(origin+route(g1,1,bal1));await page.locator('.journey-source').waitFor();await page.evaluate(url=>{history.pushState(null,'',url);dispatchEvent(new PopStateEvent('popstate'));},route(g3,3,gap));assert.equal(await page.locator('.real-reading').count(),0);release();await read(gap,'gap');assert.equal(await page.locator('[data-value=epa]').count(),0);await page.unroute('**/__observations/real-recovery/*');report.cases.push({name:'late responses retain new game/observation identity'});
 // A stale calendar response after changing season cannot expose old game labels.
 let releaseCalendar;const gateCalendar=new Promise(r=>releaseCalendar=r);let once=false;
 await page.route('**/data/seasons/2026.json',async r=>{if(!once){once=true;await gateCalendar;}await r.continue();});await page.goto(origin+route(g1,1));await page.evaluate(()=>{history.pushState(null,'','/?season=2025&week=1&game=2026_01_BAL_IND');dispatchEvent(new PopStateEvent('popstate'));});await page.getByRole('button',{name:'Recarregar calendário'}).waitFor();releaseCalendar();await page.waitForTimeout(200);assert.equal(await page.locator('.journey-band').count(),0);await page.unroute('**/data/seasons/2026.json');report.cases.push({name:'late calendar response discarded across season'});
 await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:900,height:390});await open(route(g2,2,bal12));assert.equal(await page.locator('.real-reading').count(),1);report.reducedMotionLandscape=true;
 assert.deepEqual(report.errors,[]);assert(report.requests.every(r=>r.method==='GET'));report.chrome=browser.version();
 fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(report,null,2)+'\n');
 fs.writeFileSync(path.join(__dirname,'routes.json'),JSON.stringify({origin,calendar:route(null,1),balIndividual:route(g1,1,bal1),noBalW2:route(g2,2,bal2),noBalAggregate:route(g2,2,bal12),balDalGap:route(g3,3,gap),noReadings:route(g0,1),neArchive:route(gn,3,ne),incompatible:route(g1,1,dal)},null,2)+'\n');
 console.log(JSON.stringify({realDocuments:48,layouts:report.layouts.length,cases:report.cases.length,history:report.history,errors:report.errors}));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
