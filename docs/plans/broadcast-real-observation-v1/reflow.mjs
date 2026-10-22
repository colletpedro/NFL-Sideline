import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url), {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const out=path.join(root,'docs/plans/broadcast-real-observation-v1/evidence');
const {createServer}=await import(path.join(root,'web-ui/node_modules/vite/dist/node/index.js'));
const server=await createServer({configFile:path.join(root,'web-ui/vite.experience.config.ts'),envFile:false,server:{host:'127.0.0.1',port:18091,strictPort:true,cors:false}});
let browser;
try{
 await server.listen();
 browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE,headless:true});
 const page=await browser.newPage({viewport:{width:320,height:1000},deviceScaleFactor:1});
 const report={case:'stats-title p; 320px, root 32px (200% text)',measurements:[]};
 for(const [name,port] of [['reference-before',18089],['isolated-fix',18091]]){
  await page.goto(`http://127.0.0.1:${port}/confronto/kansas-city-buffalo?round=7&period=second&play=pass`);
  await page.locator('.stats-title p').waitFor();await page.evaluate(()=>document.fonts.ready);
  await page.evaluate(()=>document.documentElement.style.fontSize='32px');
  const m=await page.evaluate(()=>{const p=document.querySelector('.stats-title p'),s=getComputedStyle(p);return {viewport:innerWidth,pageWidth:document.documentElement.scrollWidth,whiteSpace:s.whiteSpace,fontSize:s.fontSize,text:p.textContent,height:p.getBoundingClientRect().height,localChartScroll:[...document.querySelectorAll('.efficiency-chart')].map(e=>({width:e.clientWidth,scrollWidth:e.scrollWidth,overflowX:getComputedStyle(e).overflowX}))};});
  report.measurements.push({name,port,...m});
  await page.locator('.stats-title').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(out,`reflow-${name}-320-text200.png`)});
  if(name==='isolated-fix'){assert.equal(m.whiteSpace,'normal');assert(m.pageWidth<=320);}
 }
 assert(report.measurements[0].pageWidth>320);
 assert.equal(report.measurements[0].fontSize,report.measurements[1].fontSize);
 report.noFontReduction=true;report.localChartScrollAssessedSeparately=true;report.temporaryServerClosedInFinally=true;
 fs.writeFileSync(path.join(out,'reflow-reference.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{if(browser)await browser.close();await server.close();}
