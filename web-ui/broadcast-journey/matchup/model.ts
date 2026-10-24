// Private presentation adapter, never a replacement for the Python source reader.
import type { Game } from '../../src/services/types';
import { formatRatio } from '../../local-editorial/observations/format';
import type { Third, RedZone } from '../situational/model';

export const GAME_ID = '2026_01_NYJ_TEN';
export const FOUNDATION_PIN = 'sha256:b10a2028f26d6acc229f80bbd27269016dd2e6b2e4b432a6d8a9109f643e5ee4';
export const ENDPOINT = '/__matchup-reading/';
export type Foundation = 'general' | 'classified_pass' | 'classified_rush';
export type Family = 'third' | 'redZone';
export type Ratio = { numerator: string | number; denominator: number };
export type Permission = { allowed: boolean; operation: 'display' | 'sideBySide' | 'difference' | 'leagueReference'; observationIds: string[]; reasonCodes: string[]; interpretation: string };
export type Descriptor = Ratio & { id: string; status: 'AVAILABLE' | 'NO_OPPORTUNITIES' | 'INSUFFICIENT' | 'SOURCE_ABSENT'; unitIds: string[]; gameIds: string[]; weeks: number[]; team: string; sourceHash: string };
export type Metric = { descriptor: Descriptor; display: Permission };
export type Attempt = { id: string; gameId: string; offense: string; defense: string; week: number; included: boolean; uncertain: boolean; converted: 0 | 1; distance: 'short' | 'medium' | 'long' | 'unknown'; yardsToGo: number | null; kind: 'pass' | 'run'; playId: number; sourceOrder: number; sack: boolean; scramble: boolean };
type Evidence = { game_id: string; play_id: number; yardline_100: number; desc: string; order_sequence: number };
export type Campaign = { id: string; gameId: string; offense: string; defense: string; week: number; included: boolean; uncertain: boolean; fixedDrive: number; sourceOrder: number; outcome: string; entryPlayIds: string[]; entryEvidence: Evidence[]; outcomeEvidence: Evidence[]; chronologicalPlayIds: string[] };
export type Epa = Metric & { foundation: Foundation; eligibleUnitIds: string[]; finiteEpaUnitIds: string[]; originalObservation: { observationId: string; subject: { team: string; role: string; foundation: Foundation }; values: { epa: { numerator: string; denominator: number } | null }; totals: { eligibleN: number; epaN: number; epaMissingN: number; epaNonfiniteN: number; epaSum: string }; presentation: { epaDecimals: number } } };
export type Production = { offense: string; defense: string; label: string; gameId: string; metrics: { third: Metric & { observation: Third }; redZone: Metric & { observation: RedZone }; thirdLong: Metric }; epa: Epa[]; thirdAttempts: Attempt[]; redZoneCampaigns: Campaign[]; thirdDistanceByType: { distance: Attempt['distance']; kind: Attempt['kind']; numerator: number; denominator: number; unitIds: string[] }[] };
export type Point = { team: string; perspective: string; observationId: string; numerator: number; denominator: number; ratio: { numerator: number; denominator: number } | null; status: Descriptor['status']; unitIds: string[]; includedInRateDistribution: boolean; reasonCodes: string[] };
export type Reference = { season: number; phase: string; weeks: number[]; population: string; candidateTeams: string[]; representedTeams: string[]; inventory: Point[]; teamsWithoutRate: Point[]; teamRateDistribution: { points: Point[] }; pooledRate: { numerator: number; denominator: number; method: string }; permission: Permission; pilotTeamsIncluded: string[]; pilotIndependentOfReference: boolean };
export type Fact = { id: string; metric: 'third' | 'thirdLong' | 'redZone'; text: string; participants: string[]; scope: { season: number; phase: string; weeks: number[]; gameIds: string[] }; evidence: { observationId: string; numerator: number; denominator: number; unitIds: string[] }[]; permission: Permission; limitations: string[] };
export type Comparison = { sideBySide: Permission; difference: Permission; differenceAminusB: Ratio | null };
export interface Document {
  contractVersion: string; projectionVersion: string; game: { gameId: string; season: number; phase: string; weeks: number[]; offenses: string[] };
  productions: Production[]; comparisons: Record<Foundation | Family | 'thirdLong', Comparison>; facts: Fact[];
  leagueReferences: Record<Family, Reference>; definitions: { document: string }; policy: { document: string; version: string };
  guarantees: Record<string, string>; sources: { pbpHash: string; situationalBundleId: string; observationBundleId: string };
  temporalContext: { mode: string; w2ContextAllowed: boolean; historicalAvailability: string; previousRegularSeasonGames: { status: string; reason: string; weeks: number[] } };
  market: { status: string; records: Record<string, string | number | null>[]; sources: { sourceRevisionId: string; origin: string }[]; captureTime: string; provider: string; preKickoffOrClosingClaimAllowed: boolean };
  unavailableOperations: { operation: string; reason: string }[];
}
function check(ok: unknown): asserts ok { if (!ok) throw new Error('A base comparável não corresponde ao piloto NYJ × TEN W1.'); }
const equalIds = (a: string[], b: string[]) => a.length === b.length && [...a].sort().join('|') === [...b].sort().join('|');
const count = (n: unknown) => Number.isSafeInteger(n) && Number(n) >= 0;
const period = (weeks: number[]) => Array.isArray(weeks) && weeks.length === 1 && weeks[0] === 1;
export function permitted(p: Permission | undefined, op: Permission['operation'], ids: string[]) {
  return !!p && p.allowed === true && p.operation === op && p.interpretation === 'OBSERVED_SAMPLE_DESCRIPTIVE' && equalIds(p.observationIds, ids);
}
function metric(m: Metric) {
  check(m?.descriptor && m.display && typeof m.display.allowed === 'boolean');
  const d = m.descriptor;
  check(['AVAILABLE','NO_OPPORTUNITIES','INSUFFICIENT','SOURCE_ABSENT'].includes(d.status));
  check(count(d.denominator) && typeof d.numerator !== 'undefined' && period(d.weeks) && equalIds(d.gameIds, [GAME_ID]));
  check(Array.isArray(d.unitIds) && new Set(d.unitIds).size === d.unitIds.length);
}
export function validateDocument(value: unknown): Document {
  const d = value as Document;
  check(d && d.contractVersion === 'broadcast-comparison-foundation-v1' && d.projectionVersion === '1.0.0');
  check(d.game?.gameId === GAME_ID && d.game.season === 2026 && d.game.phase === 'REG' && period(d.game.weeks));
  check(equalIds(d.game.offenses, ['NYJ','TEN']) && d.productions?.length === 2 && equalIds(d.productions.map(p => p.offense), ['NYJ','TEN']));
  for (const p of d.productions) {
    check(p.gameId === GAME_ID && p.defense === (p.offense === 'NYJ' ? 'TEN' : 'NYJ'));
    for (const name of ['third','thirdLong','redZone'] as const) metric(p.metrics[name]);
    check(p.epa.length === 3 && equalIds(p.epa.map(e => e.foundation), ['general','classified_pass','classified_rush']));
    for (const e of p.epa) {
      metric(e); const o = e.originalObservation;
      check(o.subject.team === p.offense && o.subject.role === 'off' && o.subject.foundation === e.foundation && o.observationId === e.descriptor.id);
      check(o.values.epa === null || o.values.epa.numerator === e.descriptor.numerator && o.values.epa.denominator === e.descriptor.denominator);
    }
    for (const [marks,m] of [[p.thirdAttempts,p.metrics.third],[p.redZoneCampaigns,p.metrics.redZone]] as const) {
      check(Array.isArray(marks) && equalIds(marks.map(u => u.id), m.descriptor.unitIds));
      check(marks.every(u => u.gameId === GAME_ID && u.offense === p.offense && u.defense === p.defense && u.week === 1 && u.included && !u.uncertain));
    }
    check(p.thirdAttempts.every(u => ['pass','run'].includes(u.kind) && ['short','medium','long','unknown'].includes(u.distance) && [0,1].includes(u.converted)));
    check(p.redZoneCampaigns.every((u,i,a) => u.entryEvidence.length > 0 && u.outcomeEvidence.length > 0 && (i === 0 || u.sourceOrder > a[i-1].sourceOrder)));
  }
  for (const family of ['third','redZone'] as const) {
    const r = d.leagueReferences[family];
    check(r && r.season === 2026 && r.phase === 'REG' && period(r.weeks));
    check(r.inventory.length === r.candidateTeams.length && equalIds(r.inventory.map(p => p.team), r.candidateTeams));
    const points = r.teamRateDistribution.points;
    check(new Set(points.map(p => p.team)).size === points.length && equalIds(points.map(p => p.team), r.representedTeams));
    check(points.every(p => p.perspective === 'off' && p.denominator > 0 && p.ratio?.numerator === p.numerator && p.ratio?.denominator === p.denominator && p.status === 'AVAILABLE'));
    check(r.pilotIndependentOfReference === false && equalIds(r.pilotTeamsIncluded, ['NYJ','TEN']));
  }
  check(d.temporalContext?.mode === 'RETROSPECTIVE' && !d.temporalContext.w2ContextAllowed && d.temporalContext.previousRegularSeasonGames.weeks.length === 0);
  check(d.definitions.document && d.policy.document && Object.values(d.guarantees).every(v => v === 'UNKNOWN'));
  check(d.market && d.market.preKickoffOrClosingClaimAllowed === false);
  return d;
}
export function matchCalendar(games: Game[], d: Document): Game {
  const matches = games.filter(g => g.gameId === d.game.gameId);
  check(matches.length === 1); const g = matches[0];
  check(g.season === d.game.season && g.gameType === d.game.phase && g.week === d.game.weeks[0]);
  check(g.awayTeam.teamAbbr === 'NYJ' && g.homeTeam.teamAbbr === 'TEN' && !!g.awayTeam.teamName && !!g.homeTeam.teamName);
  return g;
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
    return f.scope.season === 2026 && f.scope.phase === 'REG' && period(f.scope.weeks) && equalIds(f.scope.gameIds,[GAME_ID]) &&
      equalIds(f.participants,['NYJ','TEN']) && sideAllowed(d,f.metric) &&
      permitted(f.permission,'difference',ms.map(m => m.descriptor.id)) && permitted(d.comparisons[f.metric].difference,'difference',ms.map(m => m.descriptor.id)) &&
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
export async function loadDocument(signal?: AbortSignal, fetcher: typeof fetch = window.fetch.bind(window)) {
  const response = await fetcher(ENDPOINT, { method: 'GET', credentials: 'same-origin', signal, headers: { 'X-Local-Matchup': '1' } });
  if (!response.ok) throw new Error('A base comparável não está disponível nesta sessão. Nenhum outro recorte foi usado.');
  if (response.headers.get('X-Comparison-Bundle') !== FOUNDATION_PIN) throw new Error('A identidade da fonte recebida diverge do piloto.');
  return validateDocument(await response.json());
}
