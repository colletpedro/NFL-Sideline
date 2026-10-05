package com.nflsideline.coreapi.editorial;

import java.util.List;

/** Orthogonal observed signs. No strength, practical-significance threshold or inferred denominator. */
public record SignalDimensions(Weekly attack, Weekly defense, Relation relation) {
    public enum Pattern { ALL_POSITIVE, ALL_NEGATIVE, MIXED_SIGNS, ZERO_ONLY,
        NONNEGATIVE_WITH_ZERO, NONPOSITIVE_WITH_ZERO, MISSING }
    public enum Relation { POSITIVE_CONVERGENCE, POSITIVE_COMPATIBILITY_ONLY, FAVORABLE_ATTACK_AND_DEFENSE,
        ATTACK_NOT_DEMONSTRATED, BOTH_NEGATIVE, WEEKLY_SIGN_VARIATION, ZERO_PROFILE, UNAVAILABLE }
    public record Weekly(Pattern pattern, boolean valuesVary, boolean containsZero) { }
    public static SignalDimensions from(EvidenceWindow a, EvidenceWindow d, boolean pairable,
                                        boolean adequate, List<Evidence> evidence) {
        Weekly attack = weekly(a, evidence), defense = weekly(d, evidence);
        Pattern x = attack.pattern(), y = defense.pattern();
        Relation relation;
        if (!pairable) relation = Relation.UNAVAILABLE;
        else if (x == Pattern.ALL_POSITIVE && y == Pattern.ALL_POSITIVE)
            relation = adequate ? Relation.POSITIVE_CONVERGENCE : Relation.POSITIVE_COMPATIBILITY_ONLY;
        else if (x == Pattern.ALL_POSITIVE && y == Pattern.ALL_NEGATIVE) relation = Relation.FAVORABLE_ATTACK_AND_DEFENSE;
        else if (x == Pattern.ALL_NEGATIVE && y == Pattern.ALL_POSITIVE) relation = Relation.ATTACK_NOT_DEMONSTRATED;
        else if (x == Pattern.ALL_NEGATIVE && y == Pattern.ALL_NEGATIVE) relation = Relation.BOTH_NEGATIVE;
        else if (x == Pattern.MIXED_SIGNS || y == Pattern.MIXED_SIGNS) relation = Relation.WEEKLY_SIGN_VARIATION;
        else relation = Relation.ZERO_PROFILE;
        return new SignalDimensions(attack, defense, relation);
    }
    private static Weekly weekly(EvidenceWindow w, List<Evidence> evidence) {
        if (w == null) return new Weekly(Pattern.MISSING, false, false);
        boolean zero = evidence.stream().anyMatch(e -> w.evidenceIds().contains(e.id()) && e.value().signum() == 0);
        int min = w.minimum().signum(), max = w.maximum().signum();
        Pattern p = min > 0 ? Pattern.ALL_POSITIVE : max < 0 ? Pattern.ALL_NEGATIVE
                : min < 0 && max > 0 ? Pattern.MIXED_SIGNS : min == 0 && max == 0 ? Pattern.ZERO_ONLY
                : min == 0 ? Pattern.NONNEGATIVE_WITH_ZERO : Pattern.NONPOSITIVE_WITH_ZERO;
        return new Weekly(p, w.minimum().compareTo(w.maximum()) != 0, zero);
    }
}
