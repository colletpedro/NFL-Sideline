// Freeze/restart against disposable byte copies only. All own processes close in finally.
const fs=require('node:fs');const path=require('node:path');const os=require('node:os');
const {spawn}=require('node:child_process');const {once}=require('node:events');const crypto=require('node:crypto');
const assert=require('node:assert/strict');const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const base='http://127.0.0.1:18083';const root=path.resolve(__dirname,'../../../..');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));const hash=v=>crypto.createHash('sha256').update(v).digest('hex');
(async()=>{
 const [configFile,out]=process.argv.slice(2);if(!out||fs.existsSync(out))throw Error('New output directory required');fs.mkdirSync(out);
 const original=JSON.parse(fs.readFileSync(configFile));const tmp=fs.mkdtempSync(path.join('/private/tmp','nfl-e5c3r-freeze-'));
 const config=structuredClone(original);const bundle=path.join(tmp,'bundle');fs.cpSync(config.bundles[0].path,bundle,{recursive:true,errorOnExist:true});config.bundles[0].path=bundle;
 const operationalConfig=path.join(tmp,'config.json');fs.writeFileSync(operationalConfig,JSON.stringify(config));
 let server=null,browser=null,round=0;const pids=[];const report={proof:'REAL_HTTP_DISPOSABLE_REAL_BUNDLE_FREEZE_RESTART',temporaryCopy:tmp,preservedBundleModified:false,success:false};
 const req=async(p,headers={})=>{const r=await fetch(base+p,{headers:{'X-Local-Observations':'1',...headers}});return {status:r.status,raw:await r.text()};};
 const start=async()=>{
  const fd=fs.openSync(path.join(out,`server-${++round}.log`),'wx');
  server=spawn(process.execPath,[path.join(root,'web-ui/scripts/editorial-dev.mjs')],{cwd:root,env:{...process.env,NFL_OBSERVATION_CONFIG:operationalConfig},stdio:['ignore',fd,fd]});fs.closeSync(fd);pids.push(server.pid);
  for(let i=0;i<200;i++){
   if(server.exitCode!==null)throw Error(`Own server exited ${server.exitCode}`);
   try{const r=await req('/__observations/');if(r.status===200)return r;}catch{}
   await sleep(100);
  }throw Error('Own server did not become ready');
 };
 const stop=async()=>{
  if(!server)return;const s=server;server=null;if(s.exitCode===null){const closed=once(s,'exit');s.kill('SIGTERM');await Promise.race([closed,sleep(10000).then(()=>{throw Error('Own server failed shutdown');})]);}
  assert.notEqual(s.exitCode,null);let absent=false;try{process.kill(s.pid,0);}catch(e){absent=e.code==='ESRCH';}assert(absent);
 };
 try{
  const a=await start();const catalog=JSON.parse(a.raw);const entry=catalog.bundles[0];assert.equal(entry.status,'READY');assert.equal(entry.observations.length,48);
  const chosen=entry.observations.find(s=>s.subject.team==='DAL'&&s.subject.role==='def'&&s.subject.foundation==='classified_pass'&&s.request.period.weeks.join(',')==='2');
  const docPath=`/__observations/${entry.entryId}/${chosen.observationId.slice(7)}`;const headers={'X-Observation-Session':catalog.sessionId};const before=await req(docPath,headers);assert.equal(before.status,200);
  browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE,headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});
  await page.addInitScript(v=>{sessionStorage.setItem('metrics-lab-mode','observations');if(!sessionStorage.getItem('metrics-lab-choice'))sessionStorage.setItem('metrics-lab-choice',JSON.stringify(v));},{entryId:entry.entryId,observationId:chosen.observationId});
  await page.goto(base);await page.getByRole('article').getByText(chosen.observationId,{exact:true}).waitFor({state:'attached'});
  const file=path.join(bundle,'observations.json');const bytes=fs.readFileSync(file);const docs=JSON.parse(bytes);docs.find(d=>d.values.epa).values.epa.numerator='777';fs.writeFileSync(file,JSON.stringify(docs));
  assert.equal((await req('/__observations/')).raw,a.raw);assert.equal((await req(docPath,headers)).raw,before.raw);
  await page.reload();await page.getByRole('article').getByText(chosen.observationId,{exact:true}).waitFor({state:'attached'});
  await stop();const b=await start();const rejected=JSON.parse(b.raw);assert.equal(rejected.bundles[0].status,'ERROR');assert.equal(rejected.bundles[0].errorCode,'BUNDLE_VALIDATION_FAILED');assert.notEqual(rejected.sessionId,catalog.sessionId);
  assert.equal((await req(docPath,headers)).status,409);
  await page.reload();await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('article').count(),0);
  assert((await page.locator('body').innerText()).includes('O bundle ou recorte anterior não existe nesta sessão'));
  report.changedRestart={previousSession:catalog.sessionId,newSession:rejected.sessionId,oldSessionStatus:409,errorCode:rejected.bundles[0].errorCode,previousChoiceRemovedWithoutFallback:true};
  await stop();fs.writeFileSync(file,bytes);const restored=await start();const fresh=JSON.parse(restored.raw);assert.equal(fresh.sessionId,catalog.sessionId);assert.equal(fresh.bundles[0].status,'READY');
  const again=await req(docPath,headers);assert.equal(again.raw,before.raw);
  // Same browser context, explicitly restore the previous nominal choice after removal.
  await page.evaluate(v=>sessionStorage.setItem('metrics-lab-choice',JSON.stringify(v)),{entryId:entry.entryId,observationId:chosen.observationId});await page.reload();await page.getByRole('article').getByText(chosen.observationId,{exact:true}).waitFor({state:'attached'});
  report.restoredRestart={sessionId:fresh.sessionId,exactDocumentBytesEqual:true,choicePersistenceAfterRestart:true,revalidatedThroughReader:true};
  report.initialSession=catalog.sessionId;report.frozenCatalogSha256=hash(a.raw);report.frozenDocumentSha256=hash(before.raw);report.sameBytesDuringDiskMutation=true;report.serverPids=pids;report.success=true;
 }finally{
  if(browser)await browser.close();await stop();report.ownServersStopped=true;report.browserClosed=true;
  fs.writeFileSync(path.join(out,'lifecycle.json'),JSON.stringify(report,null,2)+'\n');
  // Keep failed disposable copies for diagnostics; original/backup never written.
  if(report.success)fs.rmSync(tmp,{recursive:true});
 }
 console.log('Real freeze/restart/409/browser choice passed');
})().catch(e=>{console.error(e);process.exit(1)});
