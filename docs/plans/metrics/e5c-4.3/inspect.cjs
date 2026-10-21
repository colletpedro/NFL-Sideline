const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const fs=require('node:fs');const path=require('node:path');
(async()=>{const out=path.join(__dirname,'evidence');const b=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try{const page=await b.newPage({viewport:{width:1440,height:900}});await page.addInitScript(()=>{sessionStorage.setItem('metrics-lab-mode','observations');sessionStorage.setItem('metrics-lab-presentation-v2','E')});
await page.goto('http://127.0.0.1:18084/');await page.locator('.r43-reading').waitFor();await page.evaluate(()=>document.fonts.ready);
await page.screenshot({path:path.join(out,'round1-bal-desktop.png')});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'round1-bal-mobile.png')});
console.log(await page.locator('.r43-reading').innerText());console.log(await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,fonts:[...document.fonts].filter(f=>f.status==='loaded').map(f=>[f.family,f.weight])})));
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
