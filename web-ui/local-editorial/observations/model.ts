// DTO structure only: validation here never authenticates/revalidates source lineage.
export const HASH = /^sha256:[0-9a-f]{64}$/;
export const SLUG = /^[a-z0-9_-]{1,48}$/;
const ID = /^[A-Za-z0-9_:-]{1,128}$/;
const CODE = /^[A-Z][A-Z0-9_]{0,127}$/;
const DECIMAL = /^-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?$/;
export const FIELD_SCOPES = {
  unknownFilterFlagsN: 'GAME_CONTEXT: original.coverage.unknown_filter_flags_n; not measured by team/role/foundation; sum once per distinct game within one observation; never sum across observations/groups',
  generalEligibleN: 'same game/team/role/revisions: statistics foundation=general',
  'eligibleN,epaN,successN,epaMissingN,epaNonfiniteN,epaSum': 'original selected game/team/role/foundation statistics',
};
export const countKeys = ['eligibleN', 'epaN', 'successN', 'epaMissingN', 'epaNonfiniteN', 'generalEligibleN', 'unknownFilterFlagsN'] as const;
export type Stats = Record<typeof countKeys[number], string> & { epaSum: string | null };
export type Ratio = { numerator: string; denominator: string };
export type Subject = { team: string; role: 'off' | 'def'; foundation: 'general' | 'classified_pass' | 'classified_rush' };
export type Period = { season: number; phase: 'REG' | 'POST'; origin: 'CURRENT' | 'HISTORICAL_REFERENCE'; period: { kind: 'DECLARED_WEEKS'; weeks: number[] } };
type Assurance = { state: string; reasonCodes: string[] };
export interface DTO {
  dtoVersion: 'metrics-lab-observation-v1'; dtoId: string; entryId: string; bundleId: string; observationId: string;
  subject: Subject; request: Period; observed: { actualWeeks: number[]; includedGameIds: string[] };
  totals: Stats | null; values: Record<'epa' | 'successRate' | 'volume' | 'frequency', Ratio | null>;
  guarantees: { integrity: Assurance; completeness: Assurance; temporal: Assurance;
    compatibility: Assurance & { epaModel: { state: 'KNOWN' | 'UNKNOWN'; id: string | null } };
    coverage: Assurance & { expectedCount: string | null; coverageRatio: Ratio | null } };
  limitations: { code: string; subjectId: string }[];
  members: { gameId: string; week: number; round: string | null; sourceState: 'PRESENT' | 'ABSENT'; completeness: string; statistics: Stats | null }[];
  fieldScopes: Record<string, string>; presentation: { epaDecimals: number; ratePercentDecimals: number; rounding: 'HALF_UP' };
  scope: { aggregation: 'SINGLE_GAME' | 'MULTI_GAME' | 'NO_OBSERVATION'; population: 'OBSERVED_SAMPLE' | 'DECLARED_POPULATION' };
}
export type Summary = Pick<DTO, 'observationId' | 'dtoId' | 'subject' | 'request'>;
export type Entry = { entryId: string; label: string; dataKind: 'REAL_ARCHIVE' | 'SYNTHETIC'; status: 'READY' | 'ERROR'; bundleId: string | null; errorCode: string | null; observations: Summary[] };
export interface Catalog { transportVersion: 'metrics-lab-catalog-v1'; sessionId: string; errorCode: string | null; bundles: Entry[] }
export function check(ok: unknown): asserts ok { if (!ok) throw new Error('Transporte de observações incompatível.'); }
function fields(value: unknown, keys: string[]) {
  check(value !== null && typeof value === 'object' && !Array.isArray(value));
  check(Object.keys(value).sort().join('|') === [...keys].sort().join('|'));
}
function strings(v: unknown, pattern: RegExp): asserts v is string[] { check(Array.isArray(v) && v.every(x => typeof x === 'string' && pattern.test(x)) && new Set(v).size === v.length); }
function count(v: unknown): asserts v is string { check(typeof v === 'string' && /^(0|[1-9][0-9]*)$/.test(v)); }
function weeks(v: unknown) { check(Array.isArray(v) && v.every(x => Number.isSafeInteger(x) && x > 0) && new Set(v).size === v.length); }
function meta(v: { subject: Subject; request: Period }) {
  fields(v.subject, ['team', 'role', 'foundation']);
  check(/^[A-Z0-9]{2,4}$/.test(v.subject.team) && ['off', 'def'].includes(v.subject.role) && ['general', 'classified_pass', 'classified_rush'].includes(v.subject.foundation));
  fields(v.request, ['season', 'phase', 'origin', 'period']); fields(v.request.period, ['kind', 'weeks']);
  check(Number.isSafeInteger(v.request.season) && v.request.season >= 1999 && ['REG', 'POST'].includes(v.request.phase) && ['CURRENT', 'HISTORICAL_REFERENCE'].includes(v.request.origin) && v.request.period.kind === 'DECLARED_WEEKS');
  weeks(v.request.period.weeks); check(v.request.period.weeks.length > 0);
}
function stat(v: Stats | null) {
  if (v === null) return;
  fields(v, [...countKeys, 'epaSum']); countKeys.forEach(k => count(v[k]));
  check(v.epaSum === null || typeof v.epaSum === 'string' && DECIMAL.test(v.epaSum) && v.epaSum !== '-0');
  check(BigInt(v.eligibleN) === BigInt(v.epaN) + BigInt(v.epaMissingN) + BigInt(v.epaNonfiniteN));
  check(BigInt(v.successN) <= BigInt(v.epaN) && BigInt(v.eligibleN) <= BigInt(v.generalEligibleN));
  check((v.epaSum === null) === (v.epaN === '0'));
}
function ratio(v: Ratio | null) {
  if (v === null) return;
  fields(v, ['numerator', 'denominator']); count(v.denominator);
  check(v.denominator !== '0' && typeof v.numerator === 'string' && DECIMAL.test(v.numerator) && v.numerator !== '-0');
}
export function validateDTO(value: unknown): DTO {
  const d = value as DTO;
  fields(d, ['dtoVersion', 'dtoId', 'entryId', 'bundleId', 'observationId', 'subject', 'request', 'observed', 'totals', 'values', 'guarantees', 'limitations', 'members', 'fieldScopes', 'presentation', 'scope']);
  check(d.dtoVersion === 'metrics-lab-observation-v1' && typeof d.entryId === 'string' && SLUG.test(d.entryId) && [d.dtoId, d.bundleId, d.observationId].every(x => typeof x === 'string' && HASH.test(x)));
  meta(d); stat(d.totals); fields(d.values, ['epa', 'successRate', 'volume', 'frequency']); Object.values(d.values).forEach(ratio);
  const t = d.totals;
  const expected = { epa: t?.epaN !== '0' && t ? { numerator: t.epaSum, denominator: t.epaN } : null,
    successRate: t?.epaN !== '0' && t ? { numerator: t.successN, denominator: t.epaN } : null,
    volume: t ? { numerator: t.eligibleN, denominator: '1' } : null,
    frequency: t && t.generalEligibleN !== '0' && d.subject.foundation !== 'general' ? { numerator: t.eligibleN, denominator: t.generalEligibleN } : null };
  for (const k of ['epa', 'successRate', 'volume', 'frequency'] as const) check(d.values[k] === null ? expected[k] === null : d.values[k]?.numerator === expected[k]?.numerator && d.values[k]?.denominator === expected[k]?.denominator);
  fields(d.observed, ['actualWeeks', 'includedGameIds']); weeks(d.observed.actualWeeks); strings(d.observed.includedGameIds, ID);
  check(d.observed.actualWeeks.every(w => d.request.period.weeks.includes(w)));
  fields(d.guarantees, ['integrity', 'completeness', 'temporal', 'compatibility', 'coverage']);
  for (const [key, g] of Object.entries(d.guarantees)) {
    fields(g, ['state', 'reasonCodes', ...(key === 'coverage' ? ['expectedCount', 'coverageRatio'] : key === 'compatibility' ? ['epaModel'] : [])]);
    strings(g.reasonCodes, CODE); check(typeof g.state === 'string');
  }
  check(d.guarantees.integrity.state === 'RECONCILED' && d.guarantees.compatibility.state === 'KNOWN' && d.guarantees.temporal.state === 'UNKNOWN');
  check(['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(d.guarantees.completeness.state));
  const cov = d.guarantees.coverage; check(['KNOWN', 'PARTIAL', 'UNKNOWN'].includes(cov.state)); ratio(cov.coverageRatio);
  if (cov.expectedCount !== null) count(cov.expectedCount);
  if (cov.state !== 'UNKNOWN') check(cov.expectedCount !== null && (cov.expectedCount === '0' ? cov.coverageRatio === null : cov.coverageRatio?.denominator === cov.expectedCount && cov.coverageRatio?.numerator === String(d.observed.includedGameIds.length)));
  if (cov.state === 'UNKNOWN') check(cov.expectedCount === null && cov.coverageRatio === null);
  const model = d.guarantees.compatibility.epaModel; fields(model, ['state', 'id']);
  check(model.state === 'UNKNOWN' ? model.id === null : model.state === 'KNOWN' && typeof model.id === 'string' && /^[A-Za-z0-9_.:@+-]{1,128}$/.test(model.id));
  fields(d.fieldScopes, ['unknownFilterFlagsN', 'generalEligibleN', 'eligibleN,epaN,successN,epaMissingN,epaNonfiniteN,epaSum']);
  check(Object.entries(FIELD_SCOPES).every(([key, text]) => d.fieldScopes[key] === text));
  check(Array.isArray(d.limitations)); d.limitations.forEach(x => { fields(x, ['code', 'subjectId']); check(typeof x.code === 'string' && typeof x.subjectId === 'string' && CODE.test(x.code) && ID.test(x.subjectId)); });
  const reasons = new Set(d.limitations.map(x => x.code));
  check(reasons.has('ARCHIVED_OBSERVATION_NOT_POINT_IN_TIME') && (!t || reasons.has('UNKNOWN_FILTER_FLAGS_GAME_SCOPE')));
  check(['AVAILABLE_AT_UNKNOWN', 'INGESTED_AT_UNKNOWN', 'EVENT_TIME_UNKNOWN'].every(code => reasons.has(code) && d.guarantees.temporal.reasonCodes.includes(code)));
  if (d.members?.length && d.guarantees.completeness.state === 'UNKNOWN') check(reasons.has('COMPLETENESS_UNKNOWN'));
  if (model.state === 'UNKNOWN') check(reasons.has('EPA_MODEL_UNKNOWN'));
  if (cov.state === 'UNKNOWN') check(reasons.has('EXPECTATION_UNKNOWN'));
  check(Array.isArray(d.members)); const memberIds: string[] = [];
  d.members.forEach(m => { fields(m, ['gameId', 'week', 'round', 'sourceState', 'completeness', 'statistics']);
    check(ID.test(m.gameId) && Number.isSafeInteger(m.week) && d.request.period.weeks.includes(m.week) && ['REG', 'WC', 'DIV', 'CON', 'SB', null].includes(m.round));
    check(['PRESENT', 'ABSENT'].includes(m.sourceState) && ['COMPLETE', 'PARTIAL', 'UNKNOWN'].includes(m.completeness)); stat(m.statistics);
    check((m.statistics === null) === (m.sourceState === 'ABSENT')); memberIds.push(m.gameId); });
  check(new Set(memberIds).size === memberIds.length);
  check([...new Set(d.members.filter(m => m.sourceState === 'PRESENT').map(m => m.week))].sort((a, b) => a - b).join('|') === d.observed.actualWeeks.slice().sort((a, b) => a - b).join('|'));
  check(d.observed.includedGameIds.slice().sort().join('|') === d.members.filter(m => m.sourceState === 'PRESENT').map(m => m.gameId).sort().join('|'));
  check((d.totals === null) === (d.observed.includedGameIds.length === 0));
  fields(d.presentation, ['epaDecimals', 'ratePercentDecimals', 'rounding']);
  check(d.presentation.rounding === 'HALF_UP' && [d.presentation.epaDecimals, d.presentation.ratePercentDecimals].every(x => Number.isSafeInteger(x) && x >= 0 && x <= 12));
  fields(d.scope, ['aggregation', 'population']); check(['SINGLE_GAME', 'MULTI_GAME', 'NO_OBSERVATION'].includes(d.scope.aggregation) && ['OBSERVED_SAMPLE', 'DECLARED_POPULATION'].includes(d.scope.population));
  check(d.scope.aggregation === (d.observed.includedGameIds.length === 0 ? 'NO_OBSERVATION' : d.members.length === 1 ? 'SINGLE_GAME' : 'MULTI_GAME'));
  check(d.scope.population === (cov.state === 'KNOWN' && d.guarantees.completeness.state === 'COMPLETE' ? 'DECLARED_POPULATION' : 'OBSERVED_SAMPLE'));
  return d;
}
export function validateCatalog(value: unknown): Catalog {
  const c = value as Catalog;
  fields(c, ['transportVersion', 'sessionId', 'errorCode', 'bundles']);
  check(c.transportVersion === 'metrics-lab-catalog-v1' && HASH.test(c.sessionId) && (c.errorCode === null || CODE.test(c.errorCode)) && Array.isArray(c.bundles));
  const ids: string[] = [];
  c.bundles.forEach(e => { fields(e, ['entryId', 'label', 'dataKind', 'status', 'bundleId', 'errorCode', 'observations']);
    check(typeof e.entryId === 'string' && SLUG.test(e.entryId) && typeof e.label === 'string' && e.label.length <= 160 && !/[\\/<>\n\r]/.test(e.label) && ['REAL_ARCHIVE', 'SYNTHETIC'].includes(e.dataKind));
    check(Array.isArray(e.observations));
    check(e.status === 'READY' ? HASH.test(e.bundleId ?? '') && e.errorCode === null : e.status === 'ERROR' && e.bundleId === null && typeof e.errorCode === 'string' && CODE.test(e.errorCode) && e.observations.length === 0);
    e.observations.forEach(s => { fields(s, ['observationId', 'dtoId', 'subject', 'request']); check(HASH.test(s.observationId) && HASH.test(s.dtoId)); meta(s); });
    check(new Set(e.observations.map(s => s.observationId)).size === e.observations.length); ids.push(e.entryId); });
  check(new Set(ids).size === ids.length); return c;
}
