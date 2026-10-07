export type Foundation = 'PASS' | 'RUSH' | 'GENERAL';
export type Relation = 'POSITIVE_CONVERGENCE' | 'POSITIVE_COMPATIBILITY_ONLY' |
  'FAVORABLE_ATTACK_AND_DEFENSE' | 'ATTACK_NOT_DEMONSTRATED' | 'BOTH_NEGATIVE' |
  'WEEKLY_SIGN_VARIATION' | 'ZERO_PROFILE';
export interface Evidence {
  id: string; metric: string; team: string; season: number; week: number;
  origin: 'CURRENT_SEASON_PRIOR_WEEKS' | 'HISTORICAL_REFERENCE';
  value: string; displayValue: string; unit: 'EPA_PER_PLAY'; plays: number | null;
}
export interface Series { id: string; evidenceIds: string[] }
export interface Encounter {
  id: string; attackTeam: string; defenseTeam: string; foundation: Foundation;
  attackSeriesId: string | null; defenseSeriesId: string | null;
  state: 'COMPARABLE' | 'UNAVAILABLE' | 'REPRESENTED_BY';
  unavailableReason: 'MISSING_ATTACK' | 'MISSING_DEFENSE' | 'MISSING_BOTH' | 'INCOMPATIBLE_ORIGIN' | null;
  representedByFindingIds: string[];
}
export interface Finding {
  id: string; claimId: string; encounterId: string; relation: Relation;
  attackPattern: string; defensePattern: string; title: string; summary: string;
  primaryRestrictionId: string;
}
export interface Restriction {
  id: string; claimId: string | null; code: string; encounterIds: string[];
  evidenceIds: string[]; text: string;
}
export interface VisualAnalysisDocument {
  schemaVersion: 'visual-analysis-1.0.0'; projectorVersion: 'visual-projector-1.0.0';
  mode: 'LOCAL_RULES_DEVELOPMENT'; publicationApproved: false;
  source: { kind: 'CONTRACT_FIXTURE'; fixtureId: string } | {
    kind: 'VALIDATED_LOCAL_RESULT'; resultIdentity: string; contextSha256: string;
    claimsContractVersion: 5; selectorVersion: '2.0.0';
  };
  game: { gameId: string; season: number; week: number; phase: 'REG' | 'POST'; awayTeam: string; homeTeam: string };
  scope: { moment: 'PREGAME'; declaredAsOfDate: string | null; temporalGuarantee: 'WEEK_ORDER_ONLY';
    expectedCurrentWeeks: number[]; opponentAdjusted: false };
  evidence: Evidence[]; series: Series[]; encounters: Encounter[]; findings: Finding[];
  restrictions: Restriction[];
  links: { fromFindingId: string; toFindingId: string; relation: 'ADDITIONAL_RESTRICTION' | 'INDEPENDENT_OPPORTUNITY' }[];
  presentation: { highlightFindingIds: string[]; equivalentHighlightGroups: string[][];
    globalRestrictionIds: string[]; chartPolicy: 'SHARED_SYMMETRIC_ZERO_V1' };
}
export interface VisualEnvelope {
  mode: 'LOCAL_RULES_DEVELOPMENT'; publicationApproved: false; gameId: string;
  attemptId: string; resultIdentity: string; visualIdentity: string;
  document: VisualAnalysisDocument;
}
