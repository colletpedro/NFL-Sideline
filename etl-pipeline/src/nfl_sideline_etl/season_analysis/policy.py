"""Operation-level decisions; never changes a legacy guarantee or policy."""
from fractions import Fraction

from . import POLICY, WEEKS

LIMITS = ['OBSERVED_SAMPLE_ONLY', 'COMPLETENESS_UNKNOWN', 'EXPECTED_COVERAGE_UNKNOWN',
          'HISTORICAL_AVAILABILITY_UNKNOWN', 'NO_QUALITY_CAUSAL_OR_PREDICTIVE_INFERENCE']


def fraction(value):
    return Fraction(str(value['numerator'])) / value['denominator']


def decision(operation, observations):
    """Descriptors are built only after operational readers and raw unit checks.

    SOURCE_ABSENT/INSUFFICIENT differ from a valid observed zero denominator.
    Game overlap is contextual; unit overlap prevents subtraction/pooling.
    """
    reasons = []
    if operation not in ('display', 'sideBySide', 'difference', 'leagueReference', 'editorialFact'):
        raise ValueError('Unknown comparison operation')
    if not observations or (operation == 'display' and len(observations) != 1) or (
            operation in ('sideBySide', 'difference', 'editorialFact') and len(observations) != 2):
        reasons.append('OPERATION_ARITY')
    games, units = set(), set()
    repeated_games, repeated_units = set(), set()
    for o in observations:
        if not o['integrityVerified'] or not o['provenanceVerified']:
            reasons.append('UNVERIFIED_SOURCE')
        if o['status'] not in ('AVAILABLE', 'NO_OPPORTUNITIES') or o['ambiguousIds']:
            reasons.append(o['status'] if o['status'] in ('SOURCE_ABSENT', 'INSUFFICIENT') else 'AMBIGUOUS_UNITS')
        if not all(o[k] for k in ('metric', 'definition', 'population', 'unit', 'sourceHash', 'sourceColumn', 'gameIds')):
            reasons.append('UNDEFINED_IDENTITY_OR_METRIC')
        if o['season'] != 2026 or o['phase'] != 'REG' or o['weeks'] not in [[w] for w in WEEKS] + [WEEKS]:
            reasons.append('OUTSIDE_W1_7_SCOPE')
        n, d = o['numerator'], o['denominator']
        if isinstance(d, bool) or not isinstance(d, int) or d < 0 or n is None:
            reasons.append('INVALID_NUMERATOR_DENOMINATOR')
        else:
            try:
                v = Fraction(str(n))
                if o['metric'] != 'epa' and (v.denominator != 1 or not 0 <= v <= d):
                    reasons.append('INVALID_NUMERATOR_DENOMINATOR')
                if (o['status'] == 'AVAILABLE' and d == 0 or o['status'] == 'NO_OPPORTUNITIES' and d != 0 or
                        len(o['unitIds']) != len(set(o['unitIds'])) or len(o['unitIds']) != d or
                        d == 0 and v != 0):
                    reasons.append('INVALID_NUMERATOR_DENOMINATOR')
            except (ValueError, ZeroDivisionError):
                reasons.append('INVALID_NUMERATOR_DENOMINATOR')
        if operation in ('sideBySide', 'difference', 'editorialFact') and not d:
            reasons.append('RATE_UNDEFINED_ZERO_DENOMINATOR')
        repeated_games |= games & set(o['gameIds']); games.update(o['gameIds'])
        repeated_units |= units & set(o['unitIds']); units.update(o['unitIds'])
    compatible = ('metric', 'definition', 'population', 'unit', 'sourceHash', 'sourceColumn', 'season', 'phase', 'weeks')
    if operation != 'display' and observations:
        for field in compatible:
            if any(o[field] != observations[0][field] for o in observations):
                reasons.append('INCOMPATIBLE_' + field.upper())
    if operation in ('difference', 'leagueReference', 'editorialFact') and repeated_units:
        reasons.append('OVERLAPPING_UNITS')
    if operation == 'leagueReference':
        if any(o['metric'] not in ('third', 'redZone') for o in observations):
            reasons.append('EPA_LEAGUE_OUT_OF_SCOPE')
        teams = [o['team'] for o in observations]
        if len(teams) != len(set(teams)) or any(o['perspective'] != 'off' for o in observations):
            reasons.append('ONE_OFFENSIVE_OBSERVATION_PER_TEAM_REQUIRED')
        if any(o['status'] != 'AVAILABLE' for o in observations):
            reasons.append('REFERENCE_REQUIRES_DEFINED_RATES')
    if operation == 'editorialFact' and any(o['metric'] not in ('third', 'thirdLong', 'redZone') for o in observations):
        reasons.append('FACT_FAMILY_OUT_OF_SCOPE')
    return dict(policyVersion=POLICY, operation=operation, allowed=not reasons,
                interpretation='OBSERVED_SAMPLE_DESCRIPTIVE', observationIds=[o['id'] for o in observations],
                reasonCodes=sorted(set(reasons)), commonGameIds=sorted(repeated_games),
                commonUnitIds=sorted(repeated_units), independence='NOT_ASSERTED', limitations=LIMITS)
