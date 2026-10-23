export type Fraction = { numerator: number; denominator: number };
export type Measure = Fraction & {
  status: 'AVAILABLE' | 'NO_OPPORTUNITIES' | 'INSUFFICIENT'; denominatorState: 'POSITIVE' | 'ZERO'; ratio: Fraction | null;
  unitIds: string[]; excludedIds: string[]; exclusions: Record<string,number>; ambiguousIds: string[];
};
export type Third = Measure & { byType: Record<string,Fraction>; byDistance: Record<string,Fraction>; penaltyFirstDowns: { included: number; excluded: number }; sacks: number; scrambles: number };
export type RedZone = Measure & { outcomes: Record<string,number>; observedEntries: number };
export type SituationalDocument = { id: string; team: string; perspective: 'off'|'def'; season: number; phase: 'REG'; weeks: number[];
  games: {gameId:string; week:number;home:string;away:string;opponent:string}[]; third: Third; redZone: RedZone };
export type Snapshot = { transportVersion: 'situational-response-v1'; bundleId: string; data: {
  contractVersion: 'situational-v1'; definitionsVersion: string; calculationVersion: string; ledgerHash: string;
  provenance: {rawHash:string; materializationId:string; inputId:string}; guarantees: Record<string,'UNKNOWN'>;
  documents: SituationalDocument[];
} };
function assert(condition: unknown): asserts condition { if (!condition) throw new Error('Artefato situacional inválido.'); }
const hash = (s: unknown) => typeof s === 'string' && /^sha256:[0-9a-f]{64}$/.test(s);
const count = (n: unknown) => Number.isSafeInteger(n) && Number(n) >= 0;
function fraction(f: Fraction) { assert(f && count(f.numerator) && count(f.denominator) && f.numerator <= f.denominator); }
function measure(m: Measure) {
  fraction(m); assert(['AVAILABLE','NO_OPPORTUNITIES','INSUFFICIENT'].includes(m.status));
  assert(m.denominatorState === (m.denominator ? 'POSITIVE':'ZERO'));
  for (const ids of [m.unitIds,m.excludedIds,m.ambiguousIds]) assert(Array.isArray(ids) && ids.every(x=>typeof x==='string') && new Set(ids).size === ids.length);
  assert(m.unitIds.length === m.denominator && !m.unitIds.some(id=>m.excludedIds.includes(id)));
  assert(m.exclusions && Object.values(m.exclusions).every(count) && Object.values(m.exclusions).reduce((a,b)=>a+b,0)===m.excludedIds.length);
  assert(m.status === 'AVAILABLE' ? m.denominator>0 && m.ratio?.numerator===m.numerator && m.ratio?.denominator===m.denominator && m.ambiguousIds.length===0 : m.ratio === null);
  assert(m.status !== 'NO_OPPORTUNITIES' || m.denominator === 0 && m.ambiguousIds.length === 0);
}
export function validateSnapshot(value: unknown): Snapshot {
  const s = value as Snapshot;
  assert(s && s.transportVersion === 'situational-response-v1' && hash(s.bundleId));
  const d = s.data; assert(d && d.contractVersion==='situational-v1' && d.definitionsVersion==='1.0.0' && d.calculationVersion==='1.0.0' && hash(d.ledgerHash));
  assert(d.provenance && hash(d.provenance.rawHash) && hash(d.provenance.materializationId) && hash(d.provenance.inputId));
  assert(d.guarantees && ['completeness','expectedCoverage','epaModel','temporalKnowledge'].every(k=>d.guarantees[k]==='UNKNOWN'));
  assert(Array.isArray(d.documents) && d.documents.length===192 && new Set(d.documents.map(x=>x.id)).size===192);
  const teams = new Set(d.documents.map(x=>x.team)); assert(teams.size===32);
  for (const t of teams) for (const side of ['off','def']) for (const period of ['1','2','1-2']) assert(d.documents.some(x=>x.id===`${t}/${side}/${period}`));
  for (const x of d.documents) {
    assert(x && /^[A-Z]{2,3}$/.test(x.team) && ['off','def'].includes(x.perspective) && x.season===2026 && x.phase==='REG');
    assert(['1','2','1-2'].includes(x.weeks.join('-')) && x.id===`${x.team}/${x.perspective}/${x.weeks.join('-')}`);
    assert(x.games.length===x.weeks.length && new Set(x.games.map(g=>g.gameId)).size===x.games.length);
    assert(x.games.every(g=>x.weeks.includes(g.week) && [g.home,g.away].includes(x.team) && g.opponent === (g.home===x.team ? g.away:g.home)));
    measure(x.third); measure(x.redZone);
    for (const group of [x.third.byType,x.third.byDistance]) {
      assert(group && Object.values(group).length>0); Object.values(group).forEach(fraction);
      assert(Object.values(group).reduce((n,f)=>n+f.numerator,0)===x.third.numerator && Object.values(group).reduce((n,f)=>n+f.denominator,0)===x.third.denominator);
    }
    assert(['pass','run'].every(k=>k in x.third.byType) && ['short','medium','long','unknown'].every(k=>k in x.third.byDistance));
    assert(count(x.third.penaltyFirstDowns.included) && count(x.third.penaltyFirstDowns.excluded) && count(x.third.sacks) && count(x.third.scrambles));
    assert(Object.values(x.redZone.outcomes).every(count) && Object.values(x.redZone.outcomes).reduce((a,b)=>a+b,0)===x.redZone.denominator && (x.redZone.outcomes.TOUCHDOWN??0)===x.redZone.numerator && count(x.redZone.observedEntries));
  }
  return s;
}
// Integer half-up to one decimal percent; counts/ratios remain exact in the artifact.
export function percent(f: Fraction | null) {
  if (!f || f.denominator===0) return null;
  const tenth = (BigInt(f.numerator)*1000n*2n+BigInt(f.denominator))/(BigInt(f.denominator)*2n);
  return `${tenth/10n},${tenth%10n}%`;
}
export type Selection = {document?:SituationalDocument;error?:string;absent?:boolean};
export function selectDocument(snapshot: Snapshot, game: {gameId:string;season:number;week:number;gameType?:string;homeTeam:{teamAbbr:string};awayTeam:{teamAbbr:string}}, q:URLSearchParams, defaultTeam:string): Selection {
  const team=q.get('team')??defaultTeam, side=q.get('side')??'off', period=q.get('reading')??'game';
  if (![game.homeTeam.teamAbbr,game.awayTeam.teamAbbr].includes(team) || !['off','def'].includes(side) || !['game','2026/REG/1,2'].includes(period) || q.has('entry') || q.has('observation')) return {error:'O time, lado, período ou identidade da URL não corresponde a esta análise.'};
  if (game.season!==2026 || (game.gameType!==undefined && game.gameType!=='REG') || ![1,2].includes(game.week)) return {absent:true};
  const weeks=period==='game' ? String(game.week):'1-2';
  const matches=snapshot.data.documents.filter(d=>d.id===`${team}/${side}/${weeks}` && d.games.some(g=>g.gameId===game.gameId && g.week===game.week && g.home===game.homeTeam.teamAbbr && g.away===game.awayTeam.teamAbbr && [g.home,g.away].includes(team)));
  return matches.length===1 ? {document:matches[0]} : {error:'Não há uma única análise confirmada para esta seleção.'};
}
