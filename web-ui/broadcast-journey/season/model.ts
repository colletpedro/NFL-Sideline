import type {Document,Index,Entry,CalendarEntry,Foundation} from '../w12/model';
import type {TeamDocument} from '../hub-team/model';
import {validateReading,type EpaData} from '../redzone-epa/model';
import pin from './pin.json';
export const PIN=pin.bundleId;
export const ENDPOINT='/__season-analysis/';
export type WeekInventory={week:number;games:number;participants:string[];byes:string[];pbpGames:number};
export type SeasonIndex=Index&{season:number;phase:string;weeks:number[];weekInventory:WeekInventory[];teams:{team:string;gameIds:string[];path:string;documentHash:string}[];sources:{pbpHash:string;scheduleHash:string;receiptsHash:string}};
export type Matchup=Document&{redzoneEpa:EpaData['games'][string]};
export type SeasonTeam=TeamDocument&{redzoneEpa:EpaData['teams'][string]};
export const WEEKS=[1,2,3,4,5,6,7];
const same=(a:unknown[],b:unknown[])=>a.length===b.length&&[...a].sort().join('|')===[...b].sort().join('|');
function check(ok:unknown):asserts ok {if(!ok)throw new Error('Fonte incompatível com o acervo 2026 REG W1–7. Nenhum outro recorte foi usado.');}
function count(v:unknown):asserts v is number {check(Number.isSafeInteger(v)&&Number(v)>=0);}
const hash=(s:string)=>/^sha256:[0-9a-f]{64}$/.test(s);
export function validateIndex(v:unknown):SeasonIndex {
 const i=v as SeasonIndex;check(i?.contractVersion==='broadcast-season-analysis-v1'&&i.projectionVersion==='1.0.0'&&i.season===2026&&i.phase==='REG'&&same(i.weeks,WEEKS));
 check(Array.isArray(i.games)&&i.games.length>0&&i.counts.games===i.games.length&&i.counts.offensiveProductions===i.games.length*2&&new Set(i.games.map(g=>g.gameId)).size===i.games.length);
 check(i.teams.length===32&&new Set(i.teams.map(t=>t.team)).size===32&&hash(i.sources.pbpHash)&&hash(i.sources.scheduleHash)&&hash(i.sources.receiptsHash));
 for(const g of i.games){check(g.season===2026&&g.phase==='REG'&&WEEKS.includes(g.week)&&g.away!==g.home&&g.gameId===`2026_0${g.week}_${g.away}_${g.home}`&&g.path===`games/${g.gameId}.json`&&hash(g.documentHash)&&g.calendarSourceHash===i.sources.scheduleHash);const s=[g.awayScore,g.homeScore,g.result];check(s.every(v=>v===null)||s.every(v=>Number.isSafeInteger(v))&&g.awayScore!>=0&&g.homeScore!>=0&&g.result===g.homeScore!-g.awayScore!);}
 check(i.weekInventory.length===7&&same(i.weekInventory.map(w=>w.week),WEEKS));
 for(const w of i.weekInventory){const gs=i.games.filter(g=>g.week===w.week),teams=gs.flatMap(g=>[g.away,g.home]);check(gs.length===w.games&&new Set(teams).size===teams.length&&same(teams,w.participants)&&same([...w.participants,...w.byes],i.teams.map(t=>t.team))&&new Set([...w.participants,...w.byes]).size===32);}
 for(const t of i.teams)check(t.path===`teams/${t.team}.json`&&hash(t.documentHash)&&same(t.gameIds,i.games.filter(g=>[g.away,g.home].includes(t.team)).map(g=>g.gameId)));
 return i;
}
function metric(m:{descriptor:{status:string;gameIds:string[];weeks:number[];sourceHash:string;unitIds:string[];denominator:number|null;numerator:string|number|null;id:string};display:Document['productions'][number]['metrics']['third']['display']},games:string[],weeks:number[],source:string) {
 const x=m?.descriptor;check(x&&['AVAILABLE','NO_OPPORTUNITIES','INSUFFICIENT','SOURCE_ABSENT'].includes(x.status)&&same(x.gameIds,games)&&same(x.weeks,weeks)&&x.sourceHash===source&&new Set(x.unitIds).size===x.unitIds.length);
 if(x.status==='AVAILABLE'||x.status==='NO_OPPORTUNITIES'){count(x.denominator);check(x.denominator===x.unitIds.length);if(x.status==='AVAILABLE')check(x.denominator>0);else check(x.denominator===0&&Number(x.numerator)===0);}
 check(m.display?.operation==='display'&&same(m.display.observationIds,[x.id])&&m.display.interpretation==='OBSERVED_SAMPLE_DESCRIPTIVE');
 if(x.status==='SOURCE_ABSENT'||x.status==='INSUFFICIENT')check(!m.display.allowed);
}
export function validateMatchup(v:unknown,g:Entry,i:SeasonIndex):Matchup {
 const d=v as Matchup;check(d?.contractVersion===i.contractVersion&&d.game.gameId===g.gameId&&d.game.season===2026&&d.game.phase==='REG'&&same(d.game.weeks,[g.week])&&d.game.away===g.away&&d.game.home===g.home&&same(d.game.offenses,[g.away,g.home])&&d.productions.length===2&&same(d.productions.map(p=>p.offense),[g.away,g.home]));
 const calendar=Object.fromEntries(Object.entries(g).filter(([k])=>!['documentHash','path'].includes(k)));check(JSON.stringify(d.calendar)===JSON.stringify(calendar));
 for(const p of d.productions){check(p.gameId===g.gameId&&p.defense===(p.offense===g.away?g.home:g.away)&&p.epa.length===3);for(const m of [...Object.values(p.metrics),...p.epa])metric(m,[g.gameId],[g.week],i.sources.pbpHash);
 for(const [us,m] of [[p.thirdAttempts,p.metrics.third],[p.redZoneCampaigns,p.metrics.redZone]] as const)check(same(us.map(u=>u.id),m.descriptor.unitIds)&&us.every(u=>u.gameId===g.gameId&&u.week===g.week&&u.offense===p.offense&&u.defense===p.defense&&u.included&&!u.uncertain));
 for(const e of p.epa){const o=e.originalObservation;check(o.observationId===e.descriptor.id&&o.subject.team===p.offense&&o.subject.role==='off'&&o.subject.foundation===e.foundation&&o.totals.epaN===e.descriptor.denominator&&same(e.finiteEpaUnitIds,e.descriptor.unitIds)&&e.eligibleUnitIds.length===o.totals.eligibleN&&new Set(e.eligibleUnitIds).size===e.eligibleUnitIds.length);if(e.descriptor.status==='AVAILABLE')check(o.values.epa?.numerator===e.descriptor.numerator&&o.values.epa?.denominator===e.descriptor.denominator);else check(o.values.epa===null);}
 }
 for(const f of ['third','redZone'] as const){const r=d.leagueReferences[f],w=i.weekInventory.find(w=>w.week===g.week)!;check(r.season===2026&&r.phase==='REG'&&same(r.weeks,[g.week])&&same(r.candidateTeams,w.participants)&&same(r.inventory.map(p=>p.team),w.participants)&&same(r.participantsIncluded,[g.away,g.home]));check(same(r.teamRateDistribution.points.map(p=>p.team),r.representedTeams)&&same([...r.representedTeams,...r.teamsWithoutRate.map(p=>p.team)],w.participants));for(const p of r.teamRateDistribution.points){count(p.numerator);count(p.denominator);check(p.denominator>0&&p.numerator<=p.denominator&&p.status==='AVAILABLE'&&p.unitIds.length===p.denominator);}}
 check(d.temporalContext.referenceWeeks.join()===String(g.week)&&!d.temporalContext.otherGamesContextAllowed&&d.market.preKickoffOrClosingClaimAllowed===false&&Object.values(d.guarantees).every(v=>v==='UNKNOWN'));
 check(d.redzoneEpa.gameId===g.gameId&&d.redzoneEpa.productions.length===2);for(const p of d.redzoneEpa.productions){validateReading(p,WEEKS);check(p.units.every(u=>u.gameId===g.gameId&&u.offense===p.offense&&u.defense===p.defense)&&[g.away,g.home].includes(p.offense));}
 return d;
}
export function validateTeam(v:unknown,team:string,i:SeasonIndex):SeasonTeam {
 const d=v as SeasonTeam;const gs=i.games.filter(g=>[g.away,g.home].includes(team));check(d?.contractVersion===i.contractVersion&&d.scope.team===team&&d.scope.season===2026&&d.scope.phase==='REG'&&same(d.scope.weeks,WEEKS)&&same(d.games.map(g=>g.gameId),gs.map(g=>g.gameId))&&same(d.byeWeeks??[],WEEKS.filter(w=>!gs.some(g=>g.week===w)))&&d.productions.length===2);
 for(const [n,p] of d.productions.entries()){check(p.team===team&&p.perspective===['off','def'][n]&&same(p.gameIds,gs.map(g=>g.gameId))&&p.components.length===gs.length);for(const c of p.components)check(gs.some(g=>g.gameId===c.gameId&&g.week===c.week)&&c[n===0?'offense':'defense']===team);for(const m of [...Object.values(p.metrics),...p.epa]){metric(m,p.gameIds,WEEKS,i.sources.pbpHash);check(m.components.length===gs.length&&m.aggregation.operation==='aggregate'&&same(m.aggregation.observationIds,[m.descriptor.id]));if(['AVAILABLE','NO_OPPORTUNITIES'].includes(m.descriptor.status))check(m.descriptor.denominator===m.components.reduce((sum,c)=>sum+c.descriptor.denominator,0));}
 check(same(p.thirdAttempts.map(u=>u.id),p.metrics.third.descriptor.unitIds)&&same(p.redZoneCampaigns.map(u=>u.id),p.metrics.redZone.descriptor.unitIds));}
 check(d.redzoneEpa.team===team&&d.redzoneEpa.productions.length===2);for(const p of d.redzoneEpa.productions){validateReading(p,WEEKS);check(p.components.length===gs.length&&same(p.gameIds,gs.map(g=>g.gameId)));}
 return d;
}
async function request(path:string,expected:string,signal?:AbortSignal){
 let r:Response;
 try{r=await fetch(ENDPOINT+path,{signal,method:'GET',credentials:'same-origin',headers:{'X-Local-Season-Analysis':'1','X-Season-Collection':PIN}});}catch{throw new Error('A fonte local não pôde ser carregada. Nenhum outro jogo ou período foi usado.');}
 if(!r.ok)throw new Error('Esta fonte local não está disponível. Não usamos outro jogo ou período.');
 const bytes=await r.text(),sha=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(bytes));
 check(r.headers.get('X-Season-Collection')===PIN&&r.headers.get('X-Season-Document')===expected&&'sha256:'+Array.from(new Uint8Array(sha),b=>b.toString(16).padStart(2,'0')).join('')===expected);
 try{return JSON.parse(bytes);}catch{throw new Error('A fonte local não contém uma leitura validada. Nenhum dado substituto foi escolhido.');}
}
export type RouteData={kind:'hub';index:SeasonIndex}|{kind:'matchup';index:SeasonIndex;d:Matchup}|{kind:'team';index:SeasonIndex;d:SeasonTeam};
export function validateRoute(q:URLSearchParams){for(const key of ['view','game','team','season','phase','week','weeks','returnWeek','foundation','rank'])check(q.getAll(key).length<=1);check(!q.has('season')||q.get('season')==='2026');check(!q.has('phase')||q.get('phase')==='REG');check(!q.has('returnWeek')||WEEKS.map(String).includes(q.get('returnWeek')!));check(!q.has('foundation')||['general','classified_pass','classified_rush'].includes(q.get('foundation')!));check(!q.has('rank')||['season','week'].includes(q.get('rank')!));const view=q.get('view');check([null,'matchup-season','team-season'].includes(view));if(view==='team-season'){check(q.has('team')&&!q.has('game')&&!q.has('week')&&(!q.has('weeks')||q.get('weeks')===WEEKS.join()));}else{check(!q.has('team')&&!q.has('weeks'));check(!q.has('week')||WEEKS.map(String).includes(q.get('week')!));check(view==='matchup-season'?q.has('game'):!q.has('game'));}}
export async function readRoute(q:URLSearchParams,signal?:AbortSignal):Promise<RouteData>{validateRoute(q);const index=validateIndex(await request('',PIN,signal));if(q.get('view')==='team-season'){const e=index.teams.find(t=>t.team===q.get('team'));check(e);return {kind:'team',index,d:validateTeam(await request(e.path.slice(0,-5),e.documentHash,signal),e.team,index)};}if(q.get('view')==='matchup-season'){const e=index.games.find(g=>g.gameId===q.get('game'));check(e&&(!q.has('week')||q.get('week')===String(e.week)));return {kind:'matchup',index,d:validateMatchup(await request(e.path.slice(0,-5),e.documentHash,signal),e,index)};}return {kind:'hub',index};}
function context(q:URLSearchParams){const out=new URLSearchParams();for(const k of ['q','scope','filter','rank'])if(q.has(k))out.set(k,q.get(k)!);return out;}
export function originWeek(q:URLSearchParams){const inferred=q.get('view')==='matchup-season'?Number(q.get('game')?.split('_')[1]):7;const n=Number(q.get('returnWeek')??q.get('week')??inferred);return WEEKS.includes(n)?n:7;}
export function weekHref(q:URLSearchParams,week:number){const out=context(q);out.set('season','2026');out.set('week',String(week));return '/?'+out;}
export function gameHref(q:URLSearchParams,g:CalendarEntry){const out=context(q);out.set('view','matchup-season');out.set('game',g.gameId);out.set('season','2026');out.set('week',String(g.week));out.set('returnWeek',String(originWeek(q)));return '/?'+out;}
export function teamHref(q:URLSearchParams,team:string){const out=context(q);out.set('view','team-season');out.set('team',team);out.set('season','2026');out.set('returnWeek',String(originWeek(q)));return '/?'+out;}
export function foundation(q:URLSearchParams):Foundation {return (q.get('foundation')??'general') as Foundation;}
