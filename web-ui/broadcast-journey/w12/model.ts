// Private presentation adapter, never a replacement for the Python source reader.
import { formatRatio } from '../../local-editorial/observations/format';
import type { Third, RedZone } from '../situational/model';

import pin from './pin.json';
export const COLLECTION_PIN = pin.bundleId;
export const ENDPOINT = '/__matchup-w12/';
export type Foundation = 'general' | 'classified_pass' | 'classified_rush';
export type Family = 'third' | 'redZone';
export type Ratio = { numerator: string | number; denominator: number };
export type Permission = { allowed: boolean; operation: 'display' | 'sideBySide' | 'difference' | 'leagueReference' | 'editorialFact'; observationIds: string[]; reasonCodes: string[]; interpretation: string };
export type Descriptor = Ratio & { id: string; status: 'AVAILABLE' | 'NO_OPPORTUNITIES' | 'INSUFFICIENT' | 'SOURCE_ABSENT'; unitIds: string[]; gameIds: string[]; weeks: number[]; team: string; sourceHash: string };
export type Metric = { descriptor: Descriptor; display: Permission };
export type Attempt = { id: string; gameId: string; offense: string; defense: string; week: number; included: boolean; uncertain: boolean; converted: 0 | 1; distance: 'short' | 'medium' | 'long' | 'unknown'; yardsToGo: number | null; kind: 'pass' | 'run'; playId: number; sourceOrder: number; sack: boolean; scramble: boolean };
type Evidence = { game_id: string; play_id: number; yardline_100: number; desc: string; order_sequence: number };
export type Campaign = { id: string; gameId: string; offense: string; defense: string; week: number; included: boolean; uncertain: boolean; fixedDrive: number; sourceOrder: number; outcome: string; entryPlayIds: string[]; entryEvidence: Evidence[]; outcomeEvidence: Evidence[]; chronologicalPlayIds: string[] };
export type Epa = Metric & { foundation: Foundation; eligibleUnitIds: string[]; finiteEpaUnitIds: string[]; originalObservation: { observationId: string; subject: { team: string; role: string; foundation: Foundation }; values: { epa: { numerator: string; denominator: number } | null }; totals: { eligibleN: number; epaN: number; epaMissingN: number; epaNonfiniteN: number; epaSum: string }; presentation: { epaDecimals: number } } };
export type Production = { offense: string; defense: string; label: string; gameId: string; metrics: { third: Metric & { observation: Third }; redZone: Metric & { observation: RedZone }; thirdLong: Metric }; epa: Epa[]; thirdAttempts: Attempt[]; redZoneCampaigns: Campaign[]; thirdDistanceByType: { distance: Attempt['distance']; kind: Attempt['kind']; numerator: number; denominator: number; unitIds: string[] }[] };
export type Point = { team: string; perspective: string; observationId: string; numerator: number; denominator: number; ratio: { numerator: number; denominator: number } | null; status: Descriptor['status']; unitIds: string[]; includedInRateDistribution: boolean; reasonCodes: string[] };
export type Reference = { season: number; phase: string; weeks: number[]; population: string; candidateTeams: string[]; representedTeams: string[]; inventory: Point[]; teamsWithoutRate: Point[]; teamRateDistribution: { points: Point[] }; pooledRate: { numerator: number; denominator: number; method: string }; permission: Permission; participantsIncluded: string[]; participantsIndependentOfReference: boolean };
export type Fact = { id: string; metric: 'third' | 'thirdLong' | 'redZone'; text: string; participants: string[]; scope: { season: number; phase: string; weeks: number[]; gameIds: string[] }; evidence: { observationId: string; numerator: number; denominator: number; unitIds: string[] }[]; permission: Permission; limitations: string[] };
export type Comparison = { sideBySide: Permission; difference: Permission; differenceAminusB: Ratio | null };
export interface Document {
  contractVersion: string; projectionVersion: string; game: { gameId: string; season: number; phase: string; weeks: number[]; offenses: string[]; away:string; home:string }; calendar: CalendarEntry;
  productions: Production[]; comparisons: Record<Foundation | Family | 'thirdLong', Comparison>; facts: Fact[];
  leagueReferences: Record<Family, Reference>; definitions: { document: string }; policy: { document: string; version: string };
  guarantees: Record<string, string>; sources: { pbpHash: string; situationalBundleId: string; observationBundleId: string };
  temporalContext: { mode: string; otherGamesContextAllowed: boolean; referenceWeeks:number[]; historicalAvailability: string; previousRegularSeasonGames: { status: string; reason: string; weeks: number[] } };
  market: { status: string; records: Record<string, string | number | null>[]; sources: { sourceRevisionId: string; origin: string }[]; captureTime: string; provider: string; preKickoffOrClosingClaimAllowed: boolean };
  unavailableOperations: { operation: string; reason: string }[];
}
function check(ok: unknown): asserts ok { if (!ok) throw new Error('A coleção, o documento ou a identidade do confronto são incompatíveis.'); }
const equalIds = (a: string[], b: string[]) => a.length === b.length && [...a].sort().join('|') === [...b].sort().join('|');
const count = (n: unknown) => Number.isSafeInteger(n) && Number(n) >= 0;
const period = (weeks: number[]) => Array.isArray(weeks) && weeks.length === 1 && [1,2].includes(weeks[0]);
export function permitted(p: Permission | undefined, op: Permission['operation'], ids: string[]) {
  return !!p && p.allowed === true && p.operation === op && p.interpretation === 'OBSERVED_SAMPLE_DESCRIPTIVE' && equalIds(p.observationIds, ids);
}
function metric(m: Metric, gameId:string, week:number) {
  check(m?.descriptor && m.display && typeof m.display.allowed === 'boolean');
  const d = m.descriptor;
  check(['AVAILABLE','NO_OPPORTUNITIES','INSUFFICIENT','SOURCE_ABSENT'].includes(d.status));
  check(count(d.denominator) && typeof d.numerator !== 'undefined' && period(d.weeks) && equalIds(d.gameIds, [gameId]) && d.weeks[0]===week);
  check(Array.isArray(d.unitIds) && new Set(d.unitIds).size === d.unitIds.length);
}
export function validateDocument(value: unknown, expected: CalendarEntry): Document {
  const d = value as Document;
  check(d && d.contractVersion === 'broadcast-matchup-w12-v1' && d.projectionVersion === '1.0.0');
  check(d.game?.gameId === expected.gameId && d.game.season === 2026 && d.game.phase === 'REG' && period(d.game.weeks));
  check(equalIds(d.game.offenses, [expected.away,expected.home]) && d.game.weeks[0]===expected.week && d.game.away===expected.away && d.game.home===expected.home && d.productions?.length === 2 && equalIds(d.productions.map(p => p.offense), [expected.away,expected.home]));
  for (const p of d.productions) {
    check(p.gameId === expected.gameId && p.defense === (p.offense === expected.away ? expected.home : expected.away));
    for (const name of ['third','thirdLong','redZone'] as const) metric(p.metrics[name],expected.gameId,expected.week);
    check(p.epa.length === 3 && equalIds(p.epa.map(e => e.foundation), ['general','classified_pass','classified_rush']));
    for (const e of p.epa) {
      metric(e,expected.gameId,expected.week); const o = e.originalObservation;
      check(o.subject.team === p.offense && o.subject.role === 'off' && o.subject.foundation === e.foundation && o.observationId === e.descriptor.id);
      check(o.values.epa === null || o.values.epa.numerator === e.descriptor.numerator && o.values.epa.denominator === e.descriptor.denominator);
    }
    for (const [marks,m] of [[p.thirdAttempts,p.metrics.third],[p.redZoneCampaigns,p.metrics.redZone]] as const) {
      check(Array.isArray(marks) && equalIds(marks.map(u => u.id), m.descriptor.unitIds));
      check(marks.every(u => u.gameId === expected.gameId && u.offense === p.offense && u.defense === p.defense && u.week === expected.week && u.included && !u.uncertain));
    }
    check(p.thirdAttempts.every(u => ['pass','run'].includes(u.kind) && ['short','medium','long','unknown'].includes(u.distance) && [0,1].includes(u.converted)));
    check(p.redZoneCampaigns.every((u,i,a) => u.entryEvidence.length > 0 && u.outcomeEvidence.length > 0 && (i === 0 || u.sourceOrder > a[i-1].sourceOrder)));
  }
  for (const family of ['third','redZone'] as const) {
    const r = d.leagueReferences[family];
    check(r && r.season === 2026 && r.phase === 'REG' && period(r.weeks) && r.weeks[0]===expected.week);
    check(r.inventory.length === r.candidateTeams.length && equalIds(r.inventory.map(p => p.team), r.candidateTeams));
    const points = r.teamRateDistribution.points;
    check(new Set(points.map(p => p.team)).size === points.length && equalIds(points.map(p => p.team), r.representedTeams));
    check(points.every(p => p.perspective === 'off' && p.denominator > 0 && p.ratio?.numerator === p.numerator && p.ratio?.denominator === p.denominator && p.status === 'AVAILABLE'));
    check(r.participantsIndependentOfReference === false && equalIds(r.participantsIncluded, [expected.away,expected.home]));
  }
  check(d.temporalContext?.mode === 'RETROSPECTIVE' && !d.temporalContext.otherGamesContextAllowed && d.temporalContext.referenceWeeks.length===1 && d.temporalContext.referenceWeeks[0]===expected.week && d.temporalContext.previousRegularSeasonGames.weeks.length === 0);
  check(d.definitions.document && d.policy.document && Object.values(d.guarantees).every(v => v === 'UNKNOWN'));
  check(d.market && d.market.preKickoffOrClosingClaimAllowed === false);
  check(JSON.stringify(d.calendar)===JSON.stringify(Object.fromEntries(Object.entries(expected).filter(([k])=>!['documentHash','path'].includes(k)))));
  return d;
}
export const rational = (r: Ratio) => ({ numerator: String(r.numerator), denominator: String(r.denominator) });
export const rate = (r: Ratio | null) => r && r.denominator > 0 ? formatRatio(rational(r), 1, true) : null;
export const epaText = (e: Epa) => e.originalObservation.values.epa ? formatRatio(rational(e.originalObservation.values.epa), e.originalObservation.presentation.epaDecimals, false, true) : null;
// Geometry only: quantize the rational with BigInt before converting to Number.
// Decimal sums never pass through a floating-point conversion for display.
export function coordinate(r: Ratio) {
  const negative = String(r.numerator).startsWith('-');
  const [whole, fraction = ''] = String(r.numerator).replace('-', '').split('.');
  const n = BigInt(whole + fraction) * 1000000n;
  const den = BigInt(r.denominator) * 10n ** BigInt(fraction.length);
  if (den <= 0n) throw new Error('Razão sem denominador válido.');
  return (negative ? -1 : 1) * Number(n / den) / 1000000;
}
export function sideAllowed(d: Document, family: Foundation | Family | 'thirdLong') {
  const ms = d.productions.map(p => family in p.metrics ? p.metrics[family as keyof Production['metrics']] : p.epa.find(e => e.foundation === family)!);
  return ms.every(m => permitted(m.display,'display',[m.descriptor.id])) && permitted(d.comparisons[family]?.sideBySide,'sideBySide',ms.map(m => m.descriptor.id));
}
export function linkedFacts(d: Document) {
  return d.facts.filter(f => {
    if (!['third','thirdLong','redZone'].includes(f.metric)) return false;
    const ms = d.productions.map(p => p.metrics[f.metric]);
    return f.scope.season === 2026 && f.scope.phase === 'REG' && period(f.scope.weeks) && equalIds(f.scope.gameIds,[d.game.gameId]) && f.scope.weeks[0]===d.game.weeks[0] &&
      equalIds(f.participants,d.game.offenses) && sideAllowed(d,f.metric) &&
      permitted(f.permission,'editorialFact',ms.map(m => m.descriptor.id)) && permitted(d.comparisons[f.metric].difference,'difference',ms.map(m => m.descriptor.id)) &&
      f.evidence.length === ms.length && f.evidence.every(e => ms.some(m => e.observationId === m.descriptor.id && e.numerator === m.descriptor.numerator && e.denominator === m.descriptor.denominator && equalIds(e.unitIds,m.descriptor.unitIds)));
  });
}
// Visual lanes change only Y. A 6% separation keeps nearby dots legible at 320px.
export function leaguePositions(points:Point[]) {
  const lanes:number[][]=[];
  return [...points].sort((a,b)=>coordinate(a)-coordinate(b)||a.team.localeCompare(b.team)).map(p=>{
    const x=coordinate(p)*1000;let lane=lanes.findIndex(xs=>xs.every(v=>Math.abs(v-x)>=60));
    if(lane<0){lane=lanes.length;lanes.push([]);}lanes[lane].push(x);
    return {point:p,x,lane};
  });
}
export interface CalendarEntry {
  gameId:string; season:number; phase:string; week:number; away:string; home:string; gameday:string|null;
  awayScore:number|null; homeScore:number|null; result:number|null; calendarSourceHash:string; calendarOrigin:string;
}
export type Entry = CalendarEntry & {documentHash:string;path:string};
export interface Index {contractVersion:string;projectionVersion:string;games:Entry[];counts:{games:number;offensiveProductions:number};historicalAvailability:string}
const hashPattern=/^sha256:[0-9a-f]{64}$/;
export function validateIndex(value:unknown):Index {
  const i=value as Index;
  check(i?.contractVersion==='broadcast-matchup-w12-v1' && i.projectionVersion==='1.0.0' && Array.isArray(i.games));
  check(i.games.length===32 && new Set(i.games.map(g=>g.gameId)).size===32 && i.counts.games===i.games.length && i.counts.offensiveProductions===i.games.length*2);
  for(const g of i.games) {
    check(g.season===2026 && g.phase==='REG' && [1,2].includes(g.week) && g.away!==g.home && g.gameId===`2026_0${g.week}_${g.away}_${g.home}`);
    check(hashPattern.test(g.documentHash) && hashPattern.test(g.calendarSourceHash) && g.path===`games/${g.gameId}.json`);
    const trio=[g.awayScore,g.homeScore,g.result];
    check(trio.every(v=>v===null)||trio.every(v=>Number.isSafeInteger(v))&&g.awayScore!>=0&&g.homeScore!>=0&&g.result===g.homeScore!-g.awayScore!);
  }
  for(const week of [1,2]) { const games=i.games.filter(g=>g.week===week);check(games.length===16&&new Set(games.flatMap(g=>[g.away,g.home])).size===32); }
  return i;
}
async function sha(bytes:string) {
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(bytes));
  return 'sha256:'+Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('');
}
async function request(path:string, expectedHash:string, signal?:AbortSignal, fetcher:typeof fetch=window.fetch.bind(window)) {
  let r:Response;
  try {r=await fetcher(path,{method:'GET',signal,credentials:'same-origin',headers:{'X-Local-Matchup-W12':'1','X-Matchup-Collection':COLLECTION_PIN}});}
  catch {throw new Error('Fonte local indisponível. Nenhum outro jogo ou período foi usado.');}
  if(!r.ok)throw new Error('Fonte local indisponível. Nenhum outro jogo ou período foi usado.');
  const bytes=await r.text();
  check(r.headers.get('X-Matchup-Collection')===COLLECTION_PIN && r.headers.get('X-Matchup-Document')===expectedHash && await sha(bytes)===expectedHash);
  return JSON.parse(bytes);
}
export async function loadIndex(signal?:AbortSignal, fetcher?:typeof fetch) {return validateIndex(await request(ENDPOINT,COLLECTION_PIN,signal,fetcher));}
export async function loadDocument(entry:Entry,signal?:AbortSignal,fetcher?:typeof fetch) {
  return validateDocument(await request(ENDPOINT+entry.gameId,entry.documentHash,signal,fetcher),entry);
}
export function resolveEntry(index:Index,q:URLSearchParams) {
  const id=q.get('game'); const e=index.games.find(g=>g.gameId===id);
  if(!e)throw new Error('Identificador de confronto desconhecido. Nenhum jogo substituto foi escolhido.');
  if(q.getAll('game').length!==1||q.getAll('season').length>1||q.getAll('week').length>1 ||
    q.has('season')&&q.get('season')!==String(e.season)||q.has('week')&&q.get('week')!==String(e.week))throw new Error('Temporada ou semana incompatível com este confronto.');
  return e;
}
export function calendarHref(q:URLSearchParams,week:number) {
  const out=new URLSearchParams();out.set('season','2026');out.set('week',q.get('returnWeek')??String(week));
  for(const k of ['q','scope','filter','page'])if(q.has(k))out.set(k,q.get(k)!);
  return '/?'+out;
}
export function matchupHref(q:URLSearchParams,e:CalendarEntry) {
  const out=new URLSearchParams(q);out.set('view','matchup-w12');out.set('game',e.gameId);out.set('season','2026');out.set('week',String(e.week));
  if(!out.has('returnWeek'))out.set('returnWeek',q.get('week')??String(e.week));
  for(const k of ['team','side','analysis','question','reading','entry','observation'])out.delete(k);
  return '/?'+out;
}
