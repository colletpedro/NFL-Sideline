// Local Chrome owned by this proof; no personal browser or historical server control.
const {chromium}=require(process.env.NFL_PLAYWRIGHT||'/Users/pedrocollet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=__dirname, output=process.env.NFL_W12_EVIDENCE||path.join(root,'evidence'),origin=process.env.NFL_W12_ORIGIN||'http://127.0.0.1:18096';
const selection=JSON.parse(fs.readFileSync(path.join(root,'selection.json'))),rounded=JSON.parse(fs.readFileSync(path.join(root,'examples.json'))).rounded;
fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),p=await context.newPage();
 const evidence={flows:{},layouts:[],browser:browser.version(),humanAcceptance:'PENDING',screens:[],externalRequests:[]};
 p.on('request',r=>{if(!r.url().startsWith(origin)&&!r.url().startsWith('data:'))evidence.externalRequests.push(r.url())});
 await p.goto(origin);await p.locator('.journey-choice, .discovery').first().waitFor();await p.waitForFunction(()=>new URL(location.href).searchParams.get('week')==='1');
 await p.waitForFunction(()=>!document.querySelector('.journey-source'));evidence.flows.defaultWeek=1;
 // Exercise actual production relationship/choice modules against every real DTO.
 const adapterModule='/@fs'+path.resolve(root,'../../../web-ui/broadcast-real/adapter.ts');
 const matrix=await p.evaluate(async({selection,rounded,adapterModule})=>{
  const {loadArchive}=await import('/sources.ts'),{choiceGroups}=await import('/choice.ts'),{relation}=await import('/relations.ts'),{journeyHref}=await import('/state.ts');
  const archive=await loadArchive(new AbortController().signal);
  const response=await fetch('/data/seasons/2026.json');const data=await response.json();const games=data.games.map(g=>({...g,homeTeam:data.teams.find(t=>t.teamAbbr===g.homeTeamAbbr),awayTeam:data.teams.find(t=>t.teamAbbr===g.awayTeamAbbr)}));
  const routes=[];let relationships=0;
  const ensure=(v,msg)=>{if(!v)throw new Error(msg)};
  for(const nominal of selection.games){
   const g=games.find(g=>g.gameId===nominal.game_id);ensure(g,'calendar game missing');
   ensure(g.week===nominal.week&&g.homeTeam.teamAbbr===nominal.home_team&&g.awayTeam.teamAbbr===nominal.away_team,'calendar mismatch');
   for(const team of [nominal.away_team,nominal.home_team]){
    const targets=[];
    for(const side of ['off','def'])for(const play of ['general','classified_pass','classified_rush']){
     const groups=choiceGroups(g,archive,{team,side,play});ensure(groups.primary.length===1&&groups.includes.length===1,'ambiguous or missing real choice');
     const individual=groups.primary[0],inclusive=groups.includes[0];
     ensure(relation(g,individual.d)==='individual'&&individual.d.members.length===1,'individual wrong');
     ensure(relation(g,inclusive.d)==='includes'&&inclusive.d.members.length===2,'inclusive wrong');
     for(const x of [individual,inclusive]){
      const base=new URLSearchParams({season:'2026',week:String(g.week),game:g.gameId,team,side,play});
      const href=journeyHref(base,{entry:x.entry.entryId,observation:x.d.observationId});
      const u=new URL(href,location.origin);ensure(u.searchParams.get('observation')===x.d.observationId,'destination mismatch');
      targets.push({side,play,relation:relation(g,x.d),href,observationId:x.d.observationId});relationships++;
     }
    }
    routes.push({gameId:g.gameId,team,targets});
   }
  }
  // No game later than W2 can acquire an individual source through a fallback.
  for(const g of games.filter(g=>g.week>2))ensure(!archive.documents.some(x=>relation(g,x.d)==='individual'),'future source fabricated');
  // Independent expected decimal strings came from the raw rational ledger.
  const first=archive.documents[0];void first;
  const reading=await import(adapterModule);
  let formats=0;
  for(const {d}of archive.documents){const expected=rounded[d.observationId];if(!expected)continue;const presented=reading.presentObservation(d);
   for(const [family,key]of [['epa','epa'],['successRate','success'],['frequency','frequency']]){
    if(expected[family]===null){ensure(presented[key]===null,'unavailable formatting changed');continue}
    const actual=presented[key].replace('−','-').replace('+','').replace(',','.').replace('%','');
    const e=expected[family];
    ensure(actual===e||Number(e)===0&&actual.includes('<'),'rounded rational mismatch '+d.observationId+' '+family+' '+actual+' '+e);formats++;
   }
  }
  return {routes,relationships,documents:archive.documents.length,formats};
 },{selection,rounded,adapterModule});
 assert.equal(matrix.routes.length,64);assert.equal(matrix.relationships,768);assert.equal(matrix.documents,588);
 fs.writeFileSync(path.join(output,'routes.json'),JSON.stringify(matrix,null,2));
 async function ready(q,selector='.journey-choice'){await p.goto(origin+'/'+q);await p.locator(selector).waitFor();await p.evaluate(()=>document.fonts.ready)}
 async function capture(name){await p.screenshot({path:path.join(output,name+'.png'),fullPage:true});evidence.screens.push(name+'.png')}
 const samples=[['off','general'],['def','classified_pass'],['off','classified_rush'],['def','classified_rush']];
 // Select samples only from the validated inventory, covering both weeks and roles.
 const diverse=['MIN','SF','LAC','MIA'];const nominalLinks={};
 for(let i=0;i<diverse.length;i++){
  const team=diverse[i],g=selection.games.find(g=>g.week===(i<2?1:2)&&[g.home_team,g.away_team].includes(team));
  const side=samples[i][0],play=samples[i][1];
  await ready(`?season=2026&week=${g.week}&game=${g.game_id}&team=${team}&side=${side}&play=${play}`);
  assert.equal(await p.locator('.real-reading').count(),0);await p.getByRole('link',{name:`Abrir leitura de ${team}`,exact:true}).click();await p.locator('.real-reading').waitFor();
  assert.equal(await p.locator('[data-relation="individual"]').count(),1);nominalLinks[team]=p.url();
  const values=await p.locator('.real-numbers').innerText();await p.reload();await p.locator('.real-reading').waitFor();assert.equal(await p.locator('.real-numbers').innerText(),values);
  if(side==='def')assert((await p.locator('.real-reading').innerText()).includes('permitido'));
  evidence.flows[team]={individual:p.url(),reload:true,side,play};
  if(i===0){await capture('min-individual-1440');await p.getByRole('link',{name:'Voltar ao confronto',exact:true}).first().click();await p.locator('.journey-choice').waitFor();await p.locator('.journey-recuts').filter({hasText:'Períodos que incluem este jogo'}).locator('summary').click();await p.locator('.journey-recuts[open] a').first().click();await p.locator('.real-reading').waitFor();assert.equal(await p.locator('[data-relation="includes"]').count(),1);evidence.flows.MIN.inclusive=p.url();nominalLinks.inclusive=p.url();await capture('min-inclusive-1440');}
 }
 // Explicit opponent selection, browser history, search and preserved return context.
 await ready('?season=2026&week=2&q=Los%20Angeles&scope=season&filter=participants&explore=open','.discovery-results');
 const row=p.locator('.discovery-results [data-game]').first();await row.getByRole('link').click();await p.locator('.journey-choice').waitFor();
 const buttons=p.locator('.journey-band-interactive .journey-team');await buttons.nth(1).click();const chosen=p.url();await p.reload();await p.locator('.journey-choice').waitFor();assert.equal(p.url(),chosen);
 await p.getByRole('link',{name:/Abrir leitura de/,exact:false}).first().click();await p.locator('.real-reading').waitFor();await p.goBack();await p.locator('.journey-choice').waitFor();assert.equal(p.url(),chosen);await p.goForward();await p.locator('.real-reading').waitFor();
 await p.getByRole('link',{name:'Voltar ao calendário · semana 2',exact:true}).click();await p.locator('.discovery-results').waitFor();
 for(const[k,v]of Object.entries({week:'2',q:'Los Angeles',scope:'season',filter:'participants',explore:'open'}))assert.equal(new URL(p.url()).searchParams.get(k),v);
 evidence.flows.searchExplicitHistoryReturn=true;
 // Missing source and separate historical NE remain available by original nominal IDs.
 await ready('?season=2026&week=3&game=2026_03_BAL_DAL&team=BAL');await p.getByRole('link',{name:'Ver lacuna de BAL',exact:true}).click();await p.locator('.real-reading').waitFor();assert.equal(await p.locator('[data-value]').count(),0);nominalLinks.gap=p.url();evidence.flows.gapNoValues=true;
 await ready('?season=2026&week=3&game=2026_03_NE_JAX&team=NE');await p.locator('.journey-recuts').filter({hasText:'Outra temporada ou fase'}).locator('summary').click();await p.getByRole('link',{name:/Abrir NE/}).click();await p.locator('.real-reading').waitFor();assert.equal(await p.locator('[data-relation="archive"]').count(),1);evidence.flows.neArchiveSeparate=true;
 // Matrix of real UI states, narrow/mobile widths and enlarged text.
 const states={calendar:'?season=2026&week=1',week2:'?season=2026&week=2',matchup:'?season=2026&week=1&game='+selection.games.find(g=>[g.home_team,g.away_team].includes('LAC')&&g.week===1).game_id+'&team=LAC',individual:new URL(nominalLinks.SF).search,inclusive:new URL(nominalLinks.inclusive).search,gap:new URL(nominalLinks.gap).search};
 for(const width of [1440,390,320])for(const[state,q]of Object.entries(states)){
  await p.setViewportSize({width,height:width===1440?1000:844});await ready(q,state==='calendar'||state==='week2'?'.discovery':state==='matchup'?'.journey-choice':'.real-reading');
  const layout=await p.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));assert(layout.scroll<=layout.width+1,JSON.stringify({state,width,layout}));evidence.layouts.push({state,...layout,textPercent:100});
  if((width===1440&&['calendar','individual','matchup'].includes(state))||(width===390&&['individual','matchup','week2'].includes(state))||(width===320&&['inclusive','gap'].includes(state)))await capture(`${state}-${width}`);
 }
 for(const state of ['calendar','matchup','individual','inclusive']){
  await ready(states[state],state==='calendar'?'.discovery':state==='matchup'?'.journey-choice':'.real-reading');await p.addStyleTag({content:'html{font-size:200% !important}'});
  const layout=await p.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));assert(layout.scroll<=layout.width+1,JSON.stringify({state,layout}));evidence.layouts.push({state,...layout,textPercent:200});if(state==='individual')await capture('reading-320-text200');
 }
 await p.setViewportSize({width:1440,height:1000});await ready('?season=2026&week=1&media=helmets','.pilot-duel');assert.equal(await p.locator('.pilot-duel .media-helmet').count(),0);assert.equal(await p.locator('.pilot-logo').count(),2);evidence.flows.helmetPairFallbackLogos=true;await capture('helmet-pending-logos-1440');
 const fail=await context.newPage();await fail.route('**/__observations/**',r=>r.fulfill({status:503,contentType:'application/json',body:'{"error":"unavailable"}'}));await fail.goto(origin+'/?season=2026&week=1');await fail.getByRole('heading',{name:'Leituras indisponíveis nesta sessão.'}).waitFor();assert.equal(await fail.getByText('Leitura deste jogo',{exact:true}).count(),0);evidence.flows.catalogFailureNoFallback=true;await fail.close();
 const bad=new URL(nominalLinks.MIN);bad.searchParams.set('observation','sha256:'+'0'.repeat(64));await ready(bad.search,'.real-state');assert.equal(await p.locator('.real-reading').count(),0);evidence.flows.nominalMissingNoFallback=true;
 assert.deepEqual(evidence.externalRequests,[]);evidence.nominalLinks=nominalLinks;evidence.matrix={participants:64,relationships:768,documents:588,roundedValues:matrix.formats};
 fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify(evidence,null,2));console.log(JSON.stringify({matrix:evidence.matrix,layouts:evidence.layouts.length,screens:evidence.screens,flows:evidence.flows},null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
