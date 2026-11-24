package com.nflsideline.coreapi.editorial.local;

import com.nflsideline.coreapi.editorial.*;
import java.util.*;

/** Public omission and relation conditions shared by all contract-v5 producers and the validator. */
public final class SignalEditorialPolicy {
    private SignalEditorialPolicy() { }
    public static boolean redundantGeneral(MatchupAssessment.Candidate general, MatchupAssessment.Candidate specific) {
        if (!general.pairable() || !specific.pairable() || general.foundation() != MetricCatalog.OFF_EPA_PLAY
                || specific.foundation() == MetricCatalog.OFF_EPA_PLAY || !general.attackTeam().equals(specific.attackTeam())) return false;
        return general.signals().relation() == specific.signals().relation()
                && general.signals().attack().pattern() == specific.signals().attack().pattern()
                && general.signals().defense().pattern() == specific.signals().defense().pattern()
                && general.signals().attack().containsZero() == specific.signals().attack().containsZero()
                && general.signals().defense().containsZero() == specific.signals().defense().containsZero()
                && general.attack().season() == specific.attack().season() && general.attack().origin() == specific.attack().origin()
                && general.attack().weeks().equals(specific.attack().weeks()) && general.defense().weeks().equals(specific.defense().weeks())
                && coverage(general).equals(coverage(specific));
    }
    private static Set<MatchupAssessment.Limitation> coverage(MatchupAssessment.Candidate c) {
        var set = new HashSet<>(c.limitations());
        // Aggregation values/volumes differ by metric; omission asserts neither numerical equivalence nor reconstruction.
        set.remove(MatchupAssessment.Limitation.WEEKLY_VARIATION);
        set.remove(MatchupAssessment.Limitation.UNAVAILABLE_DENOMINATORS);
        return set;
    }
    public static boolean restricts(MatchupAssessment.Candidate source, MatchupAssessment.Candidate target) {
        return source.pairable() && target.pairable() && !source.id().equals(target.id())
                && source.attackTeam().equals(target.attackTeam()) && source.foundation() != target.foundation()
                && source.attack().season() == target.attack().season() && source.attack().origin() == target.attack().origin()
                && target.signals().relation() == SignalDimensions.Relation.POSITIVE_CONVERGENCE
                && source.signals().relation() != SignalDimensions.Relation.POSITIVE_CONVERGENCE;
    }
    public static ClaimSelection.Predicate internalLimit(MatchupAssessment.Candidate c) {
        if (!c.adequateCoverage()) return ClaimSelection.Predicate.COVERAGE_LIMIT;
        if (c.signals().attack().pattern() == SignalDimensions.Pattern.MIXED_SIGNS
                || c.signals().defense().pattern() == SignalDimensions.Pattern.MIXED_SIGNS)
            return ClaimSelection.Predicate.SIGN_VARIATION_LIMIT;
        if (c.attack().weeks().size() <= 2 || c.defense().weeks().size() <= 2) return ClaimSelection.Predicate.SAMPLE_LIMIT;
        return ClaimSelection.Predicate.LIMITED_SCOPE;
    }
}
