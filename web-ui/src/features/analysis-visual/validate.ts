import schemaText from '../../../../contracts/visual-analysis/v1/schema.json?raw';
import copyText from '../../../../contracts/visual-analysis/v1/copy-catalog.json?raw';
import { compareMagnitude, decimalParts, sign } from './decimal';
import type { Evidence, Series, VisualAnalysisDocument, VisualEnvelope } from './model';

const schema = JSON.parse(schemaText) as Schema;
const copy = JSON.parse(copyText) as { relations: Record<string, { title: string; summary: string }>; restrictions: Record<string, string> };
const hash = /^[0-9a-f]{64}$/;
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const supported = new Set(['$schema', 'title', 'definitions', '$ref', 'type', 'properties', 'additionalProperties',
  'required', 'items', 'minItems', 'maxItems', 'uniqueItems', 'minLength', 'maxLength', 'minimum', 'maximum', 'pattern', 'enum', 'anyOf']);
type Schema = { [key: string]: unknown; definitions?: Record<string, Schema>; properties?: Record<string, Schema>;
  required?: string[]; items?: Schema; anyOf?: Schema[]; enum?: unknown[]; type?: string; $ref?: string;
  minItems?: number; maxItems?: number; minLength?: number; maxLength?: number; minimum?: number; maximum?: number;
  pattern?: string; uniqueItems?: boolean };
function fail(message: string): never { throw new Error(`Documento visual incompatível: ${message}`); }
function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function assert(condition: unknown, message: string): asserts condition { if (!condition) fail(message); }
function check(value: unknown, rule: Schema, path = '$'): void {
  for (const key of Object.keys(rule)) assert(supported.has(key), `schema não suportado em ${path}`);
  if (rule.$ref) {
    const definition = schema.definitions?.[rule.$ref.split('/').pop() ?? ''];
    assert(definition, `referência de schema em ${path}`); check(value, definition, path); return;
  }
  if (rule.anyOf) {
    const valid = rule.anyOf.some(option => { try { check(value, option, path); return true; } catch { return false; } });
    assert(valid, path); return;
  }
  if (rule.enum) assert(rule.enum.some(item => item === value), path);
  if (rule.type === 'null') assert(value === null, path);
  if (rule.type === 'integer') assert(Number.isInteger(value), path);
  if (rule.type === 'string') assert(typeof value === 'string', path);
  if (rule.type === 'array') assert(Array.isArray(value), path);
  if (rule.type === 'object') assert(object(value), path);
  if (rule.type === 'object' && object(value)) {
    for (const key of rule.required ?? []) assert(key in value, `${path}.${key}`);
    for (const [key, child] of Object.entries(value)) {
      assert(rule.properties?.[key] !== undefined, `${path}.${key}`);
      check(child, rule.properties[key], `${path}.${key}`);
    }
  }
  if (rule.type === 'array' && Array.isArray(value)) {
    assert(value.length >= (rule.minItems ?? 0) && value.length <= (rule.maxItems ?? Infinity), path);
    if (rule.uniqueItems) assert(new Set(value.map(item => JSON.stringify(item))).size === value.length, path);
    value.forEach((item, index) => check(item, rule.items!, `${path}[${index}]`));
  }
  if (rule.type === 'string' && typeof value === 'string') {
    assert(value.length >= (rule.minLength ?? 0) && value.length <= (rule.maxLength ?? Infinity), path);
    if (rule.pattern) assert(new RegExp(rule.pattern).test(value), path);
  }
  if (rule.type === 'integer' && typeof value === 'number')
    assert(value >= (rule.minimum ?? -Infinity) && value <= (rule.maximum ?? Infinity), path);
}
function index<T extends { id: string }>(values: T[], name: string): Map<string, T> {
  const map = new Map(values.map(item => [item.id, item]));
  assert(map.size === values.length, `IDs duplicados em ${name}`); return map;
}
function display(value: string): string {
  const p = decimalParts(value);
  if (!p.sign) return '0,000';
  if (compareMagnitude(value, '0.0005') < 0) return p.sign > 0 ? '0 < EPA < 0,0005' : '-0,0005 < EPA < 0';
  const unsigned = value.replace(/^-/, '');
  const [whole, fraction = ''] = unsigned.split('.');
  const rounded = BigInt(whole) * 1000n + BigInt((fraction + '000').slice(0, 3)) + (Number(fraction[3] ?? '0') >= 5 ? 1n : 0n);
  const scaled = rounded.toString().padStart(4, '0');
  return `${p.sign > 0 ? '+' : '-'}${scaled.slice(0, -3)},${scaled.slice(-3)}`;
}
function pattern(rows: Evidence[]): string {
  const signs = new Set(rows.map(row => sign(row.value)));
  if (signs.size === 1) return signs.has(1) ? 'ALL_POSITIVE' : signs.has(-1) ? 'ALL_NEGATIVE' : 'ZERO_ONLY';
  if (signs.size === 2 && signs.has(0)) return signs.has(1) ? 'NONNEGATIVE_WITH_ZERO' : 'NONPOSITIVE_WITH_ZERO';
  return 'MIXED_SIGNS';
}
function same(a: unknown, b: unknown) { return JSON.stringify(a) === JSON.stringify(b); }
function rows(sid: string | null, series: Map<string, Series>, evidence: Map<string, Evidence>): Evidence[] {
  assert(sid === null || series.has(sid), 'série inexistente');
  return sid === null ? [] : series.get(sid)!.evidenceIds.map(id => {
    const row = evidence.get(id); assert(row, 'evidência inexistente'); return row;
  });
}
export function validateDocument(value: unknown, kind: 'fixture' | 'real'): VisualAnalysisDocument {
  check(value, schema);
  const doc = value as VisualAnalysisDocument;
  assert((kind === 'fixture' && doc.source.kind === 'CONTRACT_FIXTURE') ||
    (kind === 'real' && doc.source.kind === 'VALIDATED_LOCAL_RESULT'), 'origem inadequada');
  const game = doc.game, teams = new Set([game.awayTeam, game.homeTeam]);
  assert(teams.size === 2, 'times iguais');
  const expected = Array.from({ length: Math.min(3, game.week - 1) }, (_, i) => Math.max(1, game.week - 3) + i);
  assert(same(doc.scope.expectedCurrentWeeks, expected), 'semanas esperadas');
  if (doc.scope.declaredAsOfDate) {
    const day = doc.scope.declaredAsOfDate;
    assert(!Number.isNaN(Date.parse(`${day}T00:00:00Z`)) && new Date(`${day}T00:00:00Z`).toISOString().slice(0, 10) === day, 'data declarada');
  }
  const evidence = index(doc.evidence, 'evidências'), series = index(doc.series, 'séries');
  const encounters = index(doc.encounters, 'encontros'), findings = index(doc.findings, 'achados');
  const restrictions = index(doc.restrictions, 'restrições');
  const observations = new Set<string>(), usedEvidence = new Set<string>(), usedSeries = new Set<string>();
  for (const row of doc.evidence) {
    assert(teams.has(row.team), 'time da evidência');
    assert(row.origin === 'HISTORICAL_REFERENCE' ? row.season < game.season : row.season === game.season && row.week < game.week, 'semana futura');
    assert(row.metric.endsWith('_PLAY') || row.plays === null, 'volume inventado');
    assert(display(row.value) === row.displayValue, 'valor formatado divergente');
    const key = `${row.team}:${row.season}:${row.week}:${row.metric}`;
    assert(!observations.has(key), 'observação duplicada'); observations.add(key);
  }
  for (const item of doc.series) {
    const points = rows(item.id, series, evidence);
    assert(points.length > 0, 'série vazia');
    assert(points.every(row => row.team === points[0].team && row.season === points[0].season &&
      row.origin === points[0].origin && row.metric === points[0].metric), 'série inconsistente');
    assert(points.every((row, index) => index === 0 || row.week > points[index - 1].week), 'série fora de ordem');
    item.evidenceIds.forEach(id => usedEvidence.add(id));
  }
  assert(usedEvidence.size === evidence.size, 'evidência órfã');
  const positions = new Set<string>();
  for (const encounter of doc.encounters) {
    assert(teams.has(encounter.attackTeam) && teams.has(encounter.defenseTeam) && encounter.attackTeam !== encounter.defenseTeam, 'times do encontro');
    positions.add(`${encounter.attackTeam}:${encounter.foundation}`);
    const suffix = encounter.foundation === 'GENERAL' ? 'PLAY' : encounter.foundation;
    const attack = rows(encounter.attackSeriesId, series, evidence), defense = rows(encounter.defenseSeriesId, series, evidence);
    assert(attack.every(row => row.team === encounter.attackTeam && row.metric === `OFF_EPA_${suffix}`), 'papel do ataque');
    assert(defense.every(row => row.team === encounter.defenseTeam && row.metric === `DEF_EPA_${suffix}`), 'papel da defesa');
    if (encounter.attackSeriesId) usedSeries.add(encounter.attackSeriesId);
    if (encounter.defenseSeriesId) usedSeries.add(encounter.defenseSeriesId);
    const pairable = !!(attack.length && defense.length && attack[0].origin === defense[0].origin && attack[0].season === defense[0].season);
    assert((encounter.state !== 'UNAVAILABLE') === pairable, 'estado do encontro');
    const reason = !attack.length && !defense.length ? 'MISSING_BOTH' : !attack.length ? 'MISSING_ATTACK' :
      !defense.length ? 'MISSING_DEFENSE' : pairable ? null : 'INCOMPATIBLE_ORIGIN';
    assert(encounter.unavailableReason === reason, 'motivo de ausência');
    assert(encounter.state === 'REPRESENTED_BY' ? encounter.foundation === 'GENERAL' && encounter.representedByFindingIds.length > 0 :
      encounter.representedByFindingIds.length === 0, 'agrupamento');
  }
  assert(doc.encounters.length === 6 && positions.size === 6, 'grade de encontros');
  assert(usedSeries.size === series.size, 'série órfã');
  const seen = new Set<string>();
  for (const finding of doc.findings) {
    const encounter = encounters.get(finding.encounterId), restriction = restrictions.get(finding.primaryRestrictionId);
    assert(encounter && restriction && encounter.state === 'COMPARABLE' && !seen.has(encounter.id), 'achado sem encontro');
    seen.add(encounter.id);
    assert(!restriction.encounterIds.length || restriction.encounterIds.includes(encounter.id), 'limite do achado');
    const a = rows(encounter.attackSeriesId, series, evidence), d = rows(encounter.defenseSeriesId, series, evidence);
    const ap = pattern(a), dp = pattern(d);
    assert(ap === finding.attackPattern && dp === finding.defensePattern, 'padrão do achado');
    const allowed = ap === 'ALL_POSITIVE' && dp === 'ALL_POSITIVE' ? ['POSITIVE_CONVERGENCE', 'POSITIVE_COMPATIBILITY_ONLY'] :
      ap === 'ALL_POSITIVE' && dp === 'ALL_NEGATIVE' ? ['FAVORABLE_ATTACK_AND_DEFENSE'] :
      ap === 'ALL_NEGATIVE' && dp === 'ALL_POSITIVE' ? ['ATTACK_NOT_DEMONSTRATED'] :
      ap === 'ALL_NEGATIVE' && dp === 'ALL_NEGATIVE' ? ['BOTH_NEGATIVE'] :
      ap === 'MIXED_SIGNS' || dp === 'MIXED_SIGNS' ? ['WEEKLY_SIGN_VARIATION'] : ['ZERO_PROFILE'];
    assert(allowed.includes(finding.relation), 'relação do achado');
    if (finding.relation === 'POSITIVE_CONVERGENCE')
      assert(game.phase === 'REG' && [...a, ...d].every(row => row.origin === 'CURRENT_SEASON_PRIOR_WEEKS') &&
        same(a.map(row => row.week), expected) && same(d.map(row => row.week), expected), 'cobertura da oportunidade');
    assert(same({ title: finding.title, summary: finding.summary }, copy.relations[finding.relation]), 'texto do achado');
  }
  assert(seen.size === doc.encounters.filter(item => item.state === 'COMPARABLE').length, 'achado ausente');
  for (const restriction of doc.restrictions) {
    assert(restriction.encounterIds.every(id => encounters.has(id)) && restriction.evidenceIds.every(id => evidence.has(id)), 'referência de restrição');
    assert(restriction.text === copy.restrictions[restriction.code], 'texto da restrição');
    for (const encounterId of restriction.encounterIds) {
      const encounter = encounters.get(encounterId)!;
      const attack = rows(encounter.attackSeriesId, series, evidence);
      const defense = rows(encounter.defenseSeriesId, series, evidence);
      const related = [...attack, ...defense];
      switch (restriction.code) {
        case 'SAMPLE_LIMIT': assert(attack.length <= 2 || defense.length <= 2, 'amostra da restrição'); break;
        case 'SIGN_VARIATION_LIMIT': assert(pattern(attack) === 'MIXED_SIGNS' || pattern(defense) === 'MIXED_SIGNS', 'variação da restrição'); break;
        case 'HISTORICAL_ONLY': assert(related.some(row => row.origin === 'HISTORICAL_REFERENCE'), 'período histórico da restrição'); break;
        case 'UNEVEN_WINDOWS': assert(!same(attack.map(row => row.week), defense.map(row => row.week)), 'semanas da restrição'); break;
        case 'UNAVAILABLE_DENOMINATORS': assert(related.some(row => row.plays === null), 'volume da restrição'); break;
        case 'NO_DATA': assert(!related.length, 'ausência da restrição'); break;
        case 'PARTIAL_DATA': assert(!attack.length || !defense.length, 'ausência parcial da restrição'); break;
        case 'COVERAGE_LIMIT': assert(!same(attack.map(row => row.week), expected) || !same(defense.map(row => row.week), expected), 'cobertura da restrição'); break;
      }
    }
  }
  const presentation = doc.presentation;
  assert(presentation.highlightFindingIds.every(id => findings.has(id)) && presentation.globalRestrictionIds.every(id => restrictions.has(id)), 'referência de apresentação');
  const tied = presentation.equivalentHighlightGroups.flat();
  assert(presentation.highlightFindingIds.length > 1 ? presentation.equivalentHighlightGroups.length === 1 &&
    new Set(tied).size === tied.length && new Set(tied).size === presentation.highlightFindingIds.length && tied.every(id => presentation.highlightFindingIds.includes(id)) :
    tied.length === 0, 'destaques equivalentes');
  assert(presentation.globalRestrictionIds.every(id => restrictions.get(id)!.encounterIds.length === 0), 'limite global');
  assert(['TEMPORAL_AVAILABILITY_UNKNOWN', 'NO_OPPONENT_ADJUSTMENT'].every(code =>
    presentation.globalRestrictionIds.some(id => restrictions.get(id)!.code === code)), 'avisos globais');
  for (const encounter of doc.encounters) for (const id of encounter.representedByFindingIds) {
    const target = findings.get(id), targetEncounter = target && encounters.get(target.encounterId);
    assert(targetEncounter && targetEncounter.attackTeam === encounter.attackTeam && targetEncounter.foundation !== 'GENERAL', 'representação geral');
    for (const key of ['attackSeriesId', 'defenseSeriesId'] as const) {
      const current = rows(encounter[key], series, evidence), represented = rows(targetEncounter[key], series, evidence);
      const signature = (items: Evidence[]) => ({ period: items.map(row => [row.season, row.week, row.origin]), pattern: pattern(items) });
      assert(same(signature(current), signature(represented)), 'cobertura do panorama agrupado');
    }
  }
  for (const link of doc.links) {
    const from = findings.get(link.fromFindingId), to = findings.get(link.toFindingId);
    assert(from && to && from !== to && !presentation.highlightFindingIds.includes(from.id) &&
      presentation.highlightFindingIds.includes(to.id), 'link de achado');
    const fromEncounter = encounters.get(from.encounterId)!, toEncounter = encounters.get(to.encounterId)!;
    if (link.relation === 'INDEPENDENT_OPPORTUNITY')
      assert(from.relation === 'POSITIVE_CONVERGENCE' && fromEncounter.attackTeam !== toEncounter.attackTeam, 'oportunidade independente');
    else assert(fromEncounter.attackTeam === toEncounter.attackTeam && fromEncounter.foundation !== toEncounter.foundation &&
      from.relation !== 'POSITIVE_CONVERGENCE' && to.relation === 'POSITIVE_CONVERGENCE', 'limitação adicional');
  }
  return doc;
}
export function validateVisualEnvelope(value: unknown, expected: {
  gameId: string; attemptId: string; resultIdentity: string; homeTeam: string; awayTeam: string;
  season: number; week: number; phase: string;
}): VisualEnvelope {
  assert(object(value), 'envelope');
  assert(same(Object.keys(value).sort(), ['attemptId', 'document', 'gameId', 'mode', 'publicationApproved', 'resultIdentity', 'visualIdentity'].sort()), 'campos do envelope');
  assert(value.mode === 'LOCAL_RULES_DEVELOPMENT' && value.publicationApproved === false &&
    value.gameId === expected.gameId && value.attemptId === expected.attemptId && uuid.test(String(value.attemptId)) &&
    value.resultIdentity === expected.resultIdentity && hash.test(String(value.resultIdentity)) &&
    hash.test(String(value.visualIdentity)), 'identidade do envelope');
  const document = validateDocument(value.document, 'real');
  assert(document.game.gameId === expected.gameId && document.game.homeTeam === expected.homeTeam &&
    document.game.awayTeam === expected.awayTeam && document.game.season === expected.season &&
    document.game.week === expected.week && document.game.phase === expected.phase &&
    document.source.kind === 'VALIDATED_LOCAL_RESULT' && document.source.resultIdentity === expected.resultIdentity,
  'identidade do documento');
  return value as unknown as VisualEnvelope;
}
