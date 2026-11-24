// Own headless Chrome, existing Playwright only; real local HTTP, no synthetic fixtures.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
 const out=process.argv[2];if(!out || fs.existsSync(out))throw Error('New evidence directory required');fs.mkdirSync(out);
 const browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE,headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>sessionStorage.setItem('metrics-lab-mode','observations'));
  const resp=await page.request.get('http://127.0.0.1:18083/__observations/',{headers:{'X-Local-Observations':'1'}});
  assert.equal(resp.status(),200);const catalog=await resp.json();const entry=catalog.bundles.find(e=>e.entryId==='real-recovery');
  assert.equal(entry.status,'READY');assert.equal(entry.dataKind,'REAL_ARCHIVE');assert.equal(entry.observations.length,48);
  await page.goto('http://127.0.0.1:18083/');await page.getByLabel('Bundle',{exact:true}).selectOption(entry.entryId);
  const article=page.getByRole('article');await article.waitFor();
  const choose=async s=>{
   await page.getByLabel('Time',{exact:true}).selectOption(s.subject.team);
   await page.getByLabel('Papel',{exact:true}).selectOption(s.subject.role);
   await page.getByLabel('Fundamento',{exact:true}).selectOption(s.subject.foundation);
   await page.getByLabel('Período',{exact:true}).selectOption(s.observationId);
   await article.getByText(s.observationId,{exact:true}).waitFor({state:'attached'});
   assert.equal(await article.count(),1);
  };
  const shown=[];
  for(const s of entry.observations){
   await choose(s);
   const resp=await page.request.get(`http://127.0.0.1:18083/__observations/${entry.entryId}/${s.observationId.slice(7)}`,{headers:{'X-Local-Observations':'1','X-Observation-Session':catalog.sessionId}});
   assert.equal(resp.status(),200);const {document:d}=await resp.json();const text=await article.innerText();
   assert(text.includes('Conhecimento no corte não demonstrado') && text.includes('modelo não identificado') && text.includes('Completude: desconhecida'));
   for(const v of Object.values(d.values))if(v)assert(text.includes(`${v.numerator} / ${v.denominator}`));
   if(d.subject.role==='def')assert(text.includes('EPA permitido')&&text.includes('Sucesso permitido')&&text.includes('Jogadas enfrentadas observadas'));
   if(d.subject.foundation!=='general')assert(text.includes('Frequência de'));
   if(d.request.phase==='POST')assert(text.includes('2025 · POST · Referência histórica'));
   if(d.request.period.weeks.join(',')==='3')assert(text.includes('Fonte ausente')&&text.includes('Valores desconhecidos não são zero')&&text.includes('Desconhecido')&&!text.includes('zero conhecido'));
   shown.push({observationId:d.observationId,dtoId:d.dtoId,subject:d.subject,request:d.request,exactValuesVisible:true});
  }
  const pick=(team,role,f,week)=>entry.observations.find(s=>s.subject.team===team&&s.subject.role===role&&s.subject.foundation===f&&s.request.period.weeks.join(',')===week);
  const bal=pick('BAL','off','general','1,2');await choose(bal);
  await page.screenshot({path:path.join(out,'desktop-bal-w1-w2.png'),fullPage:true});
  const details=page.getByText('Contagens, fontes ausentes e motivos',{exact:true});
  await details.focus();await page.keyboard.press('Enter');assert(await details.evaluate(e=>e.parentElement.open));assert(await details.evaluate(e=>e===document.activeElement));
  assert.notEqual(await details.evaluate(e=>getComputedStyle(e).outlineStyle),'none');await page.keyboard.press('Space');assert(!(await details.evaluate(e=>e.parentElement.open)));
  const chosen=await page.getByLabel('Período',{exact:true}).inputValue();
  await page.getByRole('button',{name:'Recarregar catálogo da sessão'}).click();await article.getByText(chosen,{exact:true}).waitFor({state:'attached'});
  assert.equal(await page.getByLabel('Período',{exact:true}).inputValue(),chosen);
  await page.reload();await article.getByText(chosen,{exact:true}).waitFor({state:'attached'});assert.equal(await page.getByLabel('Período',{exact:true}).inputValue(),chosen);
  const preference=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('metrics-lab-choice')));assert.equal(preference.observationId,chosen);assert.deepEqual(Object.keys(preference).sort(),['entryId','observationId']);
  await choose(pick('DAL','def','classified_pass','2'));
  await page.screenshot({path:path.join(out,'desktop-dal-defense-pass-w2.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await choose(pick('NE','def','classified_pass','19,20,21,22'));
  await details.focus();await page.keyboard.press('Enter');assert(await details.evaluate(e=>e.parentElement.open));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  await page.screenshot({path:path.join(out,'mobile-ne-post2025.png'),fullPage:true});
  await choose(pick('BAL','off','general','3'));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  await page.screenshot({path:path.join(out,'mobile-bal-w3-gap.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify({proof:'OWN_CHROME_REAL_HTTP_REAL_ARCHIVE',chromeVersion:browser.version(),sessionId:catalog.sessionId,bundleId:entry.bundleId,shown,desktop:'1440x1000',mobile:'390x844',checks:['all 48 real recortes selectable and exact fractions visible','defensive EPA and success allowed labels','frequency and volume denominators','POST2025 separated','BAL W3 absent never zero','UNKNOWN visible','keyboard Enter/Space details and focus','reload and sessionStorage choice persistence','one observation at a time','no horizontal mobile overflow','no page errors'],humanComprehension:'NOT_EVALUATED',browserClosedInFinally:true},null,2)+'\n');
  console.log('Real browser proof passed:',shown.length,'observations');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
