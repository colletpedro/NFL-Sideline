// Own Chrome; operational catalog and DTOs exclusively from real HTTP.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = 'http://127.0.0.1:18090';
const out = path.join(__dirname,'evidence');
const report = { proof:'COMPLETE_READER_TO_REAL_HTTP_TO_UI', shown:[], layouts:[], interactions:[], requests:[] };
function formatted(r, places, percent=false, signed=false) {
 if(!r)return null;
 const negative=r.numerator.startsWith('-'), [a,b='']=r.numerator.replace('-','').split('.');
 let n=BigInt(a+b)*(percent?100n:1n), d=BigInt(r.denominator)*10n**BigInt(b.length), scale=10n**BigInt(places);
 const whole=n*scale/d, remainder=n*scale%d;
 const rounded=whole+(remainder*2n>=d?1n:0n), sign=n===0n?'':negative?'−':signed?'+':'';
 if(n!==0n&&rounded===0n)return sign+'<'+(places?'0,'+'0'.repeat(places-1)+'1':'1')+(percent?'%':'');
 return sign+(rounded/scale).toString()+(places?','+(rounded%scale).toString().padStart(places,'0'):'')+(percent?'%':'');
}
const grouped=s=>s.replace(/\B(?=(\d{3})+(?!\d))/g,'.');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE,headless:true});
 try{
  report.chrome=browser.version();
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>report.requests.push({method:r.method(),url:r.url()}));
  const cr=await page.request.get(origin+'/__observations/',{headers:{'X-Local-Observations':'1'}});
  assert.equal(cr.status(),200);const catalog=await cr.json();const entry=catalog.bundles[0];
  assert.equal(entry.status,'READY');assert.equal(entry.dataKind,'REAL_ARCHIVE');assert.equal(entry.observations.length,48);
  report.sessionId=catalog.sessionId;report.bundleId=entry.bundleId;
  const documents=[];
  for(const s of entry.observations){const response=await page.request.get(`${origin}/__observations/${entry.entryId}/${s.observationId.slice(7)}`,{headers:{'X-Local-Observations':'1','X-Observation-Session':catalog.sessionId}});assert.equal(response.status(),200);documents.push((await response.json()).document);}
  const url=d=>`${origin}/?entry=${entry.entryId}&observation=${d.observationId}`;
  const pick=(team,role,foundation,weeks)=>documents.find(d=>d.subject.team===team&&d.subject.role===role&&d.subject.foundation===foundation&&d.request.period.weeks.join(',')===weeks);
  const bal=pick('BAL','off','general','1,2'), defense=pick('DAL','def','classified_pass','2'), gap=pick('BAL','off','general','3'), ne=pick('NE','def','classified_rush','19,20,21,22');
  const ready=async d=>{await page.locator('.real-reading').waitFor();await page.waitForFunction(id=>document.querySelector('.real-reading .obs-details:last-child')?.textContent.includes(id),d.observationId);};
  const open=async d=>{await page.goto(url(d));await ready(d);await page.evaluate(()=>document.fonts.ready);};
  for(const d of documents){
   await open(d);const article=page.locator('.real-reading');assert.equal(await article.count(),1);
   const text=await article.innerText();assert(text.includes('Completude não confirmada')&&text.includes('Cobertura esperada desconhecida')&&text.includes('Conhecimento anterior ao jogo não demonstrado'));
   if(d.totals){
    assert.equal(await page.locator('[data-value=epa]').innerText(),formatted(d.values.epa,d.presentation.epaDecimals,false,true)??'Sem denominador');
    assert.equal(await page.locator('[data-value=success]').innerText(),formatted(d.values.successRate,d.presentation.ratePercentDecimals,true)??'Sem denominador');
    assert.equal(await page.locator('[data-value=volume]').innerText(),grouped(d.totals.eligibleN));
    assert(text.includes(`${grouped(d.totals.successN)} / ${grouped(d.totals.epaN)}`));
    assert(text.includes('Modelo EPA não identificado'));
    if(d.subject.role==='def')assert(text.includes('EPA médio permitido')&&text.includes('permitidos ao ataque adversário'));
    if(d.subject.foundation!=='general')assert(text.includes('Frequência: '+formatted(d.values.frequency,d.presentation.ratePercentDecimals,true)));
   }else{assert(text.includes('Sem fonte para este recorte'));assert.equal(await page.locator('[data-value]').count(),0);assert.equal(await page.locator('.real-track').count(),0);assert(text.includes('Ausência de fonte não é zero'));}
   if(d.request.phase==='POST')assert(text.includes('2025 · Pós-temporada'));
   // Actual disclosure content, not just serialization present in the DOM.
   await page.locator('.obs-details').first().locator('summary').click();
   for(const value of Object.values(d.values))if(value)assert((await article.innerText()).includes(`${value.numerator} / ${value.denominator}`));
   await page.locator('.obs-details').last().locator('summary').click();
   assert((await article.innerText()).includes(d.dtoId));
   for(const l of d.limitations)assert((await article.innerText()).includes(l.code));
   report.shown.push({observationId:d.observationId,dtoId:d.dtoId,subject:d.subject,request:d.request,exactMetricsChecked:true,completeLimitationsChecked:true});
  }
  // Select with the actual controls, then reload the selected observation.
  await open(bal);await page.getByRole('button',{name:'Alterar recorte',exact:true}).click();
  await page.getByLabel('Time',{exact:true}).selectOption('DAL');
  await page.getByLabel('Papel',{exact:true}).selectOption('def');
  await page.getByLabel('Fundamento',{exact:true}).selectOption('classified_pass');
  const periodOption=await page.getByLabel('Período',{exact:true}).locator('option').evaluateAll(options=>options.find(o=>o.value.endsWith('semanas 2'))?.value);
  await page.getByLabel('Período',{exact:true}).selectOption(periodOption);await ready(defense);
  const chosen=page.url();await page.reload();await ready(defense);assert.equal(page.url(),chosen);
  assert.deepEqual(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('broadcast-real-choice-v1'))),{entryId:entry.entryId,observationId:defense.observationId});
  report.interactions.push('catalog-only team/role/foundation/period controls','URL and preference reload persistence');
  // Keyboard: visible outline, chart disclosure, details Enter/Space and retained select focus.
  await open(bal);await page.keyboard.press('Tab');assert.equal(await page.locator('.skip-link').evaluate(e=>e===document.activeElement),true);
  const explore=page.locator('.real-chart-button');await explore.focus();
  await page.keyboard.press('Enter');assert.equal(await explore.getAttribute('aria-expanded'),'true');
  assert((await page.locator('#chart-counts').innerText()).includes('65 / 115'));
  assert.notEqual(await explore.evaluate(e=>getComputedStyle(e).outlineStyle),'none');
  const details=page.locator('.obs-details').first().locator('summary');await details.focus();await page.keyboard.press('Enter');assert(await details.evaluate(e=>e.parentElement.open));
  await page.keyboard.press('Space');assert(!(await details.evaluate(e=>e.parentElement.open)));
  await page.getByRole('button',{name:'Alterar recorte',exact:true}).click();
  await page.getByLabel('Papel',{exact:true}).focus();await page.getByLabel('Papel',{exact:true}).selectOption('def');
  await ready(pick('BAL','def','general','1,2'));assert.equal(await page.getByLabel('Papel',{exact:true}).evaluate(e=>e===document.activeElement),true);
  report.interactions.push('keyboard chart/details Enter/Space','visible outline','select focus preserved');
  // Delayed old response cannot overwrite a more recent choice. The client is intentionally
  // made to ignore abort here to exercise its active/identity guard in addition to AbortController.
  const delayed=await browser.newPage({viewport:{width:390,height:844}});
  await delayed.addInitScript(()=>{const fetchOriginal=window.fetch;window.fetch=(input,init)=>fetchOriginal(input,{...init,signal:undefined});});
  let release,arrive;const gate=new Promise(r=>release=r), arrived=new Promise(r=>arrive=r);
  const stale=pick('BAL','off','general','1');
  await delayed.route(`**/__observations/${entry.entryId}/${stale.observationId.slice(7)}`,async route=>{const response=await route.fetch();arrive();await gate;await route.fulfill({response});});
  await delayed.goto(url(bal));await delayed.locator('.real-reading').waitFor();
  await delayed.getByRole('button',{name:'Alterar recorte',exact:true}).click();
  const pSelect=delayed.getByLabel('Período',{exact:true});
  const p1=await pSelect.locator('option').evaluateAll(options=>options.find(o=>o.value.endsWith('semanas 1'))?.value);
  const p2=await pSelect.locator('option').evaluateAll(options=>options.find(o=>o.value.endsWith('semanas 2'))?.value);
  await pSelect.selectOption(p1);await arrived;await delayed.getByRole('status').filter({hasText:'Abrindo a observação'}).waitFor();
  assert.equal(await delayed.locator('.real-reading').count(),0);
  await delayed.screenshot({path:path.join(out,'mobile-loading.png'),fullPage:true});
  await pSelect.selectOption(p2);const latest=pick('BAL','off','general','2');
  await delayed.waitForFunction(id=>document.querySelector('.obs-details:last-child')?.textContent.includes(id),latest.observationId);
  release();await delayed.waitForResponse(r=>r.url().endsWith(stale.observationId.slice(7)));
  await delayed.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  assert((await delayed.locator('.obs-details').last().textContent()).includes(latest.observationId));
  assert.equal(await delayed.locator('[data-value=volume]').innerText(),grouped(latest.totals.eligibleN));
  report.interactions.push('late response discarded even when fetch ignores abort','no stale numbers while loading');await delayed.close();
  // Recoverable fetch failure and an actual 409 response routed through the existing client.
  for(const kind of ['network','session']){
   const check=await browser.newPage({viewport:{width:390,height:844}});let rejected=false;
   await check.route(`**/__observations/${entry.entryId}/${bal.observationId.slice(7)}`,async route=>{
    if(!rejected){rejected=true;if(kind==='network')await route.abort('failed');else await route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:'OBSERVATION_SESSION_CHANGED'})});}
    else await route.continue();
   });
   await check.goto(url(bal));await check.getByRole('alert').waitFor();
   if(kind==='session')assert((await check.getByRole('alert').innerText()).includes('A sessão mudou'));
   assert.equal(await check.locator('.real-reading').count(),0);
   await check.screenshot({path:path.join(out,`mobile-${kind}-error.png`),fullPage:true});
   await check.getByRole('button',{name:'Recarregar catálogo',exact:true}).click();await check.locator('.real-reading').waitFor();
   report.interactions.push(kind+' error and explicit recovery');await check.close();
  }
  // A missing preferred identity remains missing: no automatic bundle or period fallback.
  await page.goto(`${origin}/?entry=removed&observation=sha256:${'f'.repeat(64)}`);
  await page.getByText('A seleção anterior não está disponível. Nenhum outro arquivo ou recorte foi usado.',{exact:true}).waitFor();
  assert.equal(await page.locator('.real-reading').count(),0);report.interactions.push('removed preference has no fallback');
  // Representative real screenshots + 200% text at all required widths.
  for(const width of [1440,900,390,320])for(const zoom of [1,2]){
   await page.setViewportSize({width,height:1000});
   await open(bal);await page.evaluate(zoom=>document.documentElement.style.fontSize=(16*zoom)+'px',zoom);
   const measure=async()=>page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth,titleWhiteSpace:getComputedStyle(document.querySelector('.stats-title p')).whiteSpace,titleHeight:document.querySelector('.stats-title p').getBoundingClientRect().height,titleFontSize:getComputedStyle(document.querySelector('.stats-title p')).fontSize,localScroll:[...document.querySelectorAll('*')].filter(e=>e.clientWidth&&e.scrollWidth>e.clientWidth+1&&['auto','scroll'].includes(getComputedStyle(e).overflowX)).map(e=>({tag:e.tagName,class:e.className,width:e.clientWidth,scroll:e.scrollWidth}))}));
   const m=await measure();assert(m.scroll<=width,JSON.stringify(m));
   for(const selector of ['[data-value=epa]','[data-value=volume]','[data-value=success]']){
    const lines=await page.locator(selector).evaluate(e=>{const r=document.createRange();r.selectNodeContents(e);return [...new Set([...r.getClientRects()].map(r=>Math.round(r.top)))].length;});
    assert.equal(lines,1,`${selector} split at ${width}, text ${zoom}`);
   }
   report.layouts.push({...m,textScale:zoom,case:'BAL off general W1–2'});
   // Expanded selectors and disclosures cannot create page scrolling either.
   await page.getByRole('button',{name:'Alterar recorte',exact:true}).click();
   await page.locator('.obs-details').last().locator('summary').click();
   const expanded=await measure();assert(expanded.scroll<=width,JSON.stringify(expanded));report.layouts.push({...expanded,textScale:zoom,case:'BAL expanded controls and provenance'});
   await page.getByRole('button',{name:'Fechar seleção',exact:true}).click();
   await page.locator('.obs-details').last().locator('summary').click();
   if(zoom===1)await page.screenshot({path:path.join(out,`available-${width}.png`),fullPage:true});
   if(width===320&&zoom===2)await page.screenshot({path:path.join(out,'reflow-real-320-text200.png'),fullPage:true});
   await open(gap);await page.evaluate(zoom=>document.documentElement.style.fontSize=(16*zoom)+'px',zoom);
   const g=await measure();assert(g.scroll<=width,JSON.stringify(g));report.layouts.push({...g,textScale:zoom,case:'BAL W3 absent'});
   if(zoom===1)await page.screenshot({path:path.join(out,`absent-${width}.png`),fullPage:true});
  }
  await page.setViewportSize({width:1440,height:1000});await open(defense);await page.screenshot({path:path.join(out,'defense-pass-1440.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await open(ne);await page.screenshot({path:path.join(out,'postseason-rush-390.png'),fullPage:true});
  assert.deepEqual(errors,[]);assert(report.requests.every(r=>r.method==='GET'));assert(report.requests.every(r=>r.url.startsWith(origin)));
  assert(report.requests.every(r=>!r.url.includes('fixtures')&&!r.url.includes('__local-analysis')&&!r.url.includes('readSlice')));
  report.interactions.push('same-origin GET only','no generation or synthetic modules on real entry');
  report.errors=errors;report.browserClosedInFinally=true;
  fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify(report,null,2)+'\n');
  console.log('PASS',report.shown.length,'real documents;',report.layouts.length,'layout checks;',report.interactions.length,'interactions');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
