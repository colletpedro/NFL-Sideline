import {formatRatio} from '../../local-editorial/observations/format';
import type {Attempt,Campaign,CalendarEntry,Entry,Epa,Foundation,Metric,Permission,Production} from '../w12/model';
import {COLLECTION_PIN,loadDocument,loadIndex,resolveEntry} from '../w12/model';
import pin from './pin.json';
export const TEAM_PIN=pin.bundleId;
export const TEAM_ENDPOINT='/__team-w12/';
export type Status='AVAILABLE'|'NO_OPPORTUNITIES'|'SOURCE_ABSENT'|'INSUFFICIENT';
export interface AggregateMetric {
 descriptor:Omit<Metric['descriptor'],'numerator'|'denominator'> & {numerator:string|number|null;denominator:number|null;perspective:string};
 display:Permission; aggregation:Omit<Permission,'operation'>&{operation:'aggregate'};
 components:Metric[];
 observation:{byDistance:Record<Attempt['distance'],{numerator:number;denominator:number}>;byType:Record<string,{numerator:number;denominator:number}>;outcomes:Record<string,number>;exclusions:Record<string,number>};
 originalAggregateId:string;
}
export interface AggregateEpa extends Omit<AggregateMetric,'observation'|'originalAggregateId'|'components'> {
 foundation:Foundation;originalObservation:Epa['originalObservation'];eligibleUnitIds:string[];finiteEpaUnitIds:string[];components:Epa[];
 calculatedTotals:Record<string,string|number>;
}
export interface TeamProduction {
 team:string;perspective:'off'|'def';label:string;opponents:string[];gameIds:string[];
 components:{gameId:string;week:number;offense:string;defense:string;sourceDocumentHash:string;production:Production}[];
 metrics:Record<'third'|'redZone',AggregateMetric>;epa:AggregateEpa[];thirdAttempts:Attempt[];redZoneCampaigns:Campaign[];
 thirdDistanceByType:Production['thirdDistanceByType'];
}
export interface TeamDocument {
 contractVersion:string;projectionVersion:string;scope:{team:string;season:number;phase:string;weeks:number[]};
 games:Entry[];byeWeeks?:number[];productions:TeamProduction[];comparisons:Record<string,{sideBySide:Permission}>;
 facts:{text:string;observationId:string;numerator:number;denominator:number;unitIds:string[];permission:Permission}[];
 definitions:{document:string};policy:{document:string;version:string};guarantees:Record<string,string>;sources:Record<string,string>;limitations:string[];
}
export interface TeamEntry {team:string;gameIds:string[];opponents:string[];documentHash:string;path:string}
export interface TeamIndex {contractVersion:string;projectionVersion:string;sourceCollection:string;season:number;phase:string;weeks:number[];teams:TeamEntry[]}
function check(ok:unknown):asserts ok {if(!ok)throw new Error('A fonte do time não corresponde ao recorte 2026 REG W1–2.');}
const same=(a:string[],b:string[])=>a.length===b.length&&[...a].sort().join('|')===[...b].sort().join('|');
const hash=/^sha256:[0-9a-f]{64}$/;
export function validateTeamIndex(value:unknown):TeamIndex {
 const i=value as TeamIndex;check(i?.contractVersion==='broadcast-team-w12-v1'&&i.projectionVersion==='1.0.0'&&i.season===2026&&i.phase==='REG'&&i.weeks.join(',')==='1,2'&&i.sourceCollection===COLLECTION_PIN);
 check(i.teams.length===32&&new Set(i.teams.map(e=>e.team)).size===32);
 check(i.teams.every(e=>/^[A-Z]{2,3}$/.test(e.team)&&e.path===`teams/${e.team}.json`&&hash.test(e.documentHash)&&e.gameIds.length===2&&new Set(e.gameIds).size===2));return i;
}
export function displayed(m:AggregateMetric|AggregateEpa) {
 return m.aggregation?.allowed&&m.aggregation.operation==='aggregate'&&same(m.aggregation.observationIds,[m.descriptor.id])&&m.display?.allowed&&m.display.operation==='display'&&same(m.display.observationIds,[m.descriptor.id])&&m.display.interpretation==='OBSERVED_SAMPLE_DESCRIPTIVE';
}
export function defined(m:AggregateMetric|AggregateEpa) {return displayed(m)&&m.descriptor.status==='AVAILABLE'&&m.descriptor.denominator!==null&&m.descriptor.denominator>0&&m.descriptor.numerator!==null;}
export function metricText(m:AggregateMetric|AggregateEpa,epa=false) {
 if(!defined(m))return null;
 return formatRatio({numerator:String(m.descriptor.numerator),denominator:String(m.descriptor.denominator)},epa?3:1,!epa,epa);
}
export function validateTeamDocument(value:unknown,entry:TeamEntry):TeamDocument {
 const d=value as TeamDocument;check(d?.contractVersion==='broadcast-team-w12-v1'&&d.projectionVersion==='1.0.0'&&d.scope.team===entry.team&&d.scope.season===2026&&d.scope.phase==='REG'&&d.scope.weeks.join(',')==='1,2');
 check(d.games.length===2&&d.games[0].week===1&&d.games[1].week===2&&same(d.games.map(g=>g.gameId),entry.gameIds)&&d.games.every(g=>[g.away,g.home].includes(entry.team)));
 check(d.productions.length===2&&d.productions[0].perspective==='off'&&d.productions[1].perspective==='def');
 for(const p of d.productions){
  check(p.team===entry.team&&same(p.gameIds,entry.gameIds)&&p.components.length===2);
  for(const c of p.components)check(entry.gameIds.includes(c.gameId)&&(p.perspective==='off'?c.offense===entry.team:c.defense===entry.team));
  check(p.epa.length===3&&same(p.epa.map(e=>e.foundation),['general','classified_pass','classified_rush']));
  for(const m of [...Object.values(p.metrics),...p.epa]){
   const x=m.descriptor;check(x.team===entry.team&&x.perspective===p.perspective);check(['AVAILABLE','NO_OPPORTUNITIES','SOURCE_ABSENT','INSUFFICIENT'].includes(x.status)&&x.weeks.join(',')==='1,2'&&same(x.gameIds,entry.gameIds));
   check(new Set(x.unitIds).size===x.unitIds.length);
   if(['AVAILABLE','NO_OPPORTUNITIES'].includes(x.status))check(Number.isSafeInteger(x.denominator)&&x.denominator!==null&&x.denominator>=0&&x.numerator!==null&&x.denominator===x.unitIds.length);
   if(x.status==='NO_OPPORTUNITIES')check(x.denominator===0&&Number(x.numerator)===0);
   if(['SOURCE_ABSENT','INSUFFICIENT'].includes(x.status))check(x.denominator===null&&x.numerator===null&&!m.aggregation.allowed);
  }
  for(const [units,family] of [[p.thirdAttempts,'third'],[p.redZoneCampaigns,'redZone']] as const)check(same(units.map(u=>u.id),p.metrics[family].descriptor.unitIds)&&units.every(u=>entry.gameIds.includes(u.gameId)&&(p.perspective==='off'?u.offense===entry.team:u.defense===entry.team)));
 }
 check(Object.values(d.guarantees).every(v=>v==='UNKNOWN'));return d;
}
async function teamRequest(path:string,expected:string,signal?:AbortSignal,fetcher:typeof fetch=window.fetch.bind(window)) {
 const r=await fetcher(path,{method:'GET',signal,credentials:'same-origin',headers:{'X-Local-Team-W12':'1','X-Team-Collection':TEAM_PIN}});
 if(!r.ok)throw new Error('Os dados W1–2 deste time não puderam ser validados. Os jogos individuais continuam acessíveis pela semana.');
 const bytes=await r.text(),digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(bytes));
 const actual='sha256:'+Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
 check(r.headers.get('X-Team-Collection')===TEAM_PIN&&r.headers.get('X-Team-Document')===expected&&actual===expected);return JSON.parse(bytes);
}
export async function loadTeamIndex(signal?:AbortSignal,fetcher?:typeof fetch) {return validateTeamIndex(await teamRequest(TEAM_ENDPOINT,TEAM_PIN,signal,fetcher));}
export async function loadTeam(entry:TeamEntry,signal?:AbortSignal,fetcher?:typeof fetch) {return validateTeamDocument(await teamRequest(TEAM_ENDPOINT+entry.team,entry.documentHash,signal,fetcher),entry);}
export function validateContext(q:URLSearchParams) {
 for(const k of ['view','game','team','season','week','returnWeek','weeks','phase'])if(q.getAll(k).length>1)throw new Error('Endereço com identificador ou período repetido.');
 if(q.has('season')&&q.get('season')!=='2026'||q.has('phase')&&q.get('phase')!=='REG'||q.has('returnWeek')&&!['1','2'].includes(q.get('returnWeek')!))throw new Error('Esta entrada está disponível somente em 2026 REG W1–2.');
}
export function resolveTeam(index:TeamIndex,q:URLSearchParams) {
 validateContext(q);if(q.has('game'))throw new Error('O endereço do time contém um confronto incompatível. Abra somente o time escolhido.');if(q.has('week')||q.has('weeks')&&q.get('weeks')!=='1,2')throw new Error('A página do time usa explicitamente W1–2. A semana de retorno não altera esse recorte.');
 const entry=index.teams.find(e=>e.team===q.get('team'));if(!entry)throw new Error('Time desconhecido neste acervo. Nenhum time substituto foi escolhido.');return entry;
}
function context(q:URLSearchParams) {const out=new URLSearchParams();for(const k of ['q','scope','filter','page'])if(q.has(k))out.set(k,q.get(k)!);return out;}
export function weekHref(q:URLSearchParams,week:number) {const out=context(q);out.set('season','2026');out.set('week',String(week));return '/?'+out;}
export function backHref(q:URLSearchParams,week=1) {const value=Number(q.get('returnWeek')??q.get('week')??week);return weekHref(q,[1,2].includes(value)?value:1);}
export function gameHref(q:URLSearchParams,g:CalendarEntry) {const out=context(q);out.set('view','matchup-w12');out.set('game',g.gameId);out.set('season','2026');out.set('week',String(g.week));out.set('returnWeek',q.get('returnWeek')??q.get('week')??String(g.week));return '/?'+out;}
export function teamHref(q:URLSearchParams,team:string) {const out=context(q);out.set('view','team-w12');out.set('team',team);out.set('season','2026');out.set('returnWeek',q.get('returnWeek')??q.get('week')??'1');return '/?'+out;}
export type RouteData={kind:'team';d:TeamDocument}|{kind:'matchup';d:Awaited<ReturnType<typeof loadDocument>>;index:Awaited<ReturnType<typeof loadIndex>>}|{kind:'hub';index:Awaited<ReturnType<typeof loadIndex>>};
export async function readRoute(q:URLSearchParams,signal?:AbortSignal):Promise<RouteData> {
 validateContext(q);const view=q.get('view');
 if(view==='team-w12'){const i=await loadTeamIndex(signal);return {kind:'team',d:await loadTeam(resolveTeam(i,q),signal)};}
 if(view!==null&&view!=='matchup-w12')throw new Error('Entrada desconhecida. Volte a uma semana do acervo.');
 const index=await loadIndex(signal);
 if(view==='matchup-w12'&&q.has('team'))throw new Error('O endereço do confronto contém um time incompatível. Abra somente a partida escolhida.');
 if(view==='matchup-w12')return {kind:'matchup',index,d:await loadDocument(resolveEntry(index,q),signal)};
 if(q.has('week')&&!['1','2'].includes(q.get('week')!)||q.has('weeks')||q.has('game')||q.has('team'))throw new Error('Semana ou identificador incompatível com o hub W1–2.');
 return {kind:'hub',index};
}
// Identity gate used by the route: late responses cannot replace a newer entity.
export class RequestGate {
 private revision=0;
 begin(){return ++this.revision;}
 current(revision:number){return this.revision===revision;}
 cancel(){this.revision++;}
}
export function teamFacts(d:TeamDocument) {
 return d.facts.filter(f=>{const m=Object.values(d.productions[0].metrics).find(m=>m.descriptor.id===f.observationId);return !!m&&displayed(m)&&f.permission.allowed&&f.permission.operation==='display'&&f.permission.interpretation==='OBSERVED_SAMPLE_DESCRIPTIVE'&&same(f.permission.observationIds,[f.observationId])&&m.descriptor.numerator===f.numerator&&m.descriptor.denominator===f.denominator&&same(m.descriptor.unitIds,f.unitIds);});
}

export function pairAllowed(d:TeamDocument,family:string) {
 const ms=d.productions.map(p=>family==='third'||family==='redZone'?p.metrics[family]:p.epa.find(e=>e.foundation===family)!);
 const perm=d.comparisons[family]?.sideBySide;
 return ms.every(defined)&&!!perm&&perm.allowed&&perm.operation==='sideBySide'&&perm.interpretation==='OBSERVED_SAMPLE_DESCRIPTIVE'&&same(perm.observationIds,ms.map(m=>m.descriptor.id));
}
