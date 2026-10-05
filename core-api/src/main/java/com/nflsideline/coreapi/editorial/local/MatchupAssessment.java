package com.nflsideline.coreapi.editorial.local;

import com.nflsideline.coreapi.editorial.*;
import java.util.*;

/** Mechanical, descriptive predicates, also used by the versioned semantic validator. */
public final class MatchupAssessment {
    private MatchupAssessment() { }
    public enum Classification { OPPORTUNITY, CONFLICTING, PROFILE, INSUFFICIENT_OR_INCOMPATIBLE,
        OPPOSING_FAVORABLE_SIGNS, UNDEMONSTRATED_ATTACK, WEEKLY_SIGN_VARIATION, ZERO_PROFILE, NEGATIVE_PROFILE }
    public enum Limitation { MISSING_ATTACK, MISSING_DEFENSE, INCOMPATIBLE_PERIOD, HISTORICAL,
        MISSING_METRIC_WEEKS, IDENTIFIABLE_CALENDAR_GAPS, NOT_RECENT_COMPLETE, DIFFERENT_WEEKS,
        DIFFERENT_AGGREGATION, UNAVAILABLE_DENOMINATORS, SMALL_OBSERVED_WINDOW, WEEKLY_VARIATION }
    public record Candidate(String id, String attackTeam, String defenseTeam, MetricCatalog foundation,
                            EvidenceWindow attack, EvidenceWindow defense, Classification classification,
                            boolean pairable, boolean adequateCoverage, List<Limitation> limitations,
                            @com.fasterxml.jackson.annotation.JsonInclude(com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL)
                            SignalDimensions signals) {
        public Candidate(String id, String attackTeam, String defenseTeam, MetricCatalog foundation,
                         EvidenceWindow attack, EvidenceWindow defense, Classification classification,
                         boolean pairable, boolean adequateCoverage, List<Limitation> limitations) {
            this(id, attackTeam, defenseTeam, foundation, attack, defense, classification, pairable, adequateCoverage, limitations, null);
        }
        public List<String> evidenceIds() {
            var ids = new ArrayList<String>();
            if (attack != null) ids.add(attack.id());
            if (defense != null) ids.add(defense.id());
            return List.copyOf(ids);
        }
        public boolean current() { return pairable && attack.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS; }
    }
    public static List<Candidate> enumerate(AnalysisContext context, EditorialParameters parameters) {
        var windows = context.windows();
        var result = new ArrayList<Candidate>();
        // This ordering is presentation only. The selector retains the whole best equivalence class.
        for (String team : List.of(context.homeTeam(), context.awayTeam()).stream().sorted().toList()) {
            String opponent = team.equals(context.homeTeam()) ? context.awayTeam() : context.homeTeam();
            for (var metric : List.of(MetricCatalog.OFF_EPA_PASS, MetricCatalog.OFF_EPA_RUSH, MetricCatalog.OFF_EPA_PLAY)) {
                var attacks = windows.stream().filter(w -> w.team().equals(team) && w.metric() == metric).toList();
                var defenses = windows.stream().filter(w -> w.team().equals(opponent) && w.metric() == metric.defensiveCounterpart()).toList();
                // The frozen three-record context has at most one origin/season per team and metric.
                if (attacks.size() > 1 || defenses.size() > 1) throw new IllegalArgumentException("Ambiguous frozen slice");
                result.add(assess(team, opponent, metric, attacks.isEmpty() ? null : attacks.getFirst(),
                        defenses.isEmpty() ? null : defenses.getFirst(), parameters));
            }
        }
        return List.copyOf(result);
    }
    /** Version 5 dimensions; legacy enumeration/classification remains unchanged for v4 documents. */
    public static List<Candidate> enumerateV5(AnalysisContext context, EditorialParameters parameters) {
        return enumerate(context, parameters).stream().map(c -> {
            var signals = SignalDimensions.from(c.attack(), c.defense(), c.pairable(), c.adequateCoverage(), context.evidence());
            var classification = switch (signals.relation()) {
                case POSITIVE_CONVERGENCE -> Classification.OPPORTUNITY;
                case FAVORABLE_ATTACK_AND_DEFENSE -> Classification.OPPOSING_FAVORABLE_SIGNS;
                case ATTACK_NOT_DEMONSTRATED -> Classification.UNDEMONSTRATED_ATTACK;
                case WEEKLY_SIGN_VARIATION -> Classification.WEEKLY_SIGN_VARIATION;
                case BOTH_NEGATIVE -> Classification.NEGATIVE_PROFILE;
                case ZERO_PROFILE -> Classification.ZERO_PROFILE;
                case UNAVAILABLE -> Classification.INSUFFICIENT_OR_INCOMPATIBLE;
                default -> Classification.PROFILE;
            };
            return new Candidate(c.id(), c.attackTeam(), c.defenseTeam(), c.foundation(), c.attack(), c.defense(),
                    classification, c.pairable(), c.adequateCoverage(), c.limitations(), signals);
        }).toList();
    }

    public static Candidate assess(String team, String opponent, MetricCatalog metric, EvidenceWindow a,
                                   EvidenceWindow d, EditorialParameters p) {
        var limits = new ArrayList<Limitation>();
        if (a == null) limits.add(Limitation.MISSING_ATTACK);
        if (d == null) limits.add(Limitation.MISSING_DEFENSE);
        boolean pairable = a != null && d != null && a.season() == d.season() && a.origin() == d.origin();
        boolean adequate = false;
        Classification classification = Classification.INSUFFICIENT_OR_INCOMPATIBLE;
        if (a != null && d != null) {
            if (!pairable) limits.add(Limitation.INCOMPATIBLE_PERIOD);
            if (a.origin() == Evidence.Origin.HISTORICAL_REFERENCE || d.origin() == Evidence.Origin.HISTORICAL_REFERENCE)
                limits.add(Limitation.HISTORICAL);
            if (!a.missingMetricWeeks().isEmpty() || !d.missingMetricWeeks().isEmpty()) limits.add(Limitation.MISSING_METRIC_WEEKS);
            if (gaps(a) || gaps(d)) limits.add(Limitation.IDENTIFIABLE_CALENDAR_GAPS);
            if (!a.weeks().equals(p.expectedRecentWeeks()) || !d.weeks().equals(p.expectedRecentWeeks())) limits.add(Limitation.NOT_RECENT_COMPLETE);
            if (!a.weeks().equals(d.weeks())) limits.add(Limitation.DIFFERENT_WEEKS);
            if (a.aggregation() != d.aggregation()) limits.add(Limitation.DIFFERENT_AGGREGATION);
            if (a.volume() == null || d.volume() == null) limits.add(Limitation.UNAVAILABLE_DENOMINATORS);
            if (a.weeks().size() < 3 || d.weeks().size() < 3) limits.add(Limitation.SMALL_OBSERVED_WINDOW);
            if (a.minimum().compareTo(a.maximum()) != 0 || d.minimum().compareTo(d.maximum()) != 0) limits.add(Limitation.WEEKLY_VARIATION);
            adequate = pairable && p.phase().equals("REG") && a.season() == p.season()
                    && a.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS
                    && a.missingMetricWeeks().isEmpty() && d.missingMetricWeeks().isEmpty()
                    && a.weeks().equals(p.expectedRecentWeeks()) && d.weeks().equals(p.expectedRecentWeeks())
                    && a.aggregation() == d.aggregation();
            // Coverage is not statistical sufficiency. Unknown denominators remain explicit, unweighted.
            if (pairable) {
                if (adequate && a.positiveInEveryObservedWeek() && d.positiveInEveryObservedWeek()) classification = Classification.OPPORTUNITY;
                else if (conflicting(a, d)) classification = Classification.CONFLICTING;
                else if (a.origin() == Evidence.Origin.HISTORICAL_REFERENCE || adequate) classification = Classification.PROFILE;
            }
        }
        return new Candidate(team + ":" + metric, team, opponent, metric, a, d, classification, pairable, adequate, List.copyOf(limits));
    }
    public static boolean conflicting(EvidenceWindow a, EvidenceWindow d) {
        return (a.maximum().signum() > 0 || d.maximum().signum() > 0)
                && (a.minimum().signum() < 0 || d.minimum().signum() < 0);
    }
    private static boolean gaps(EvidenceWindow w) { return w.weeks().getLast() - w.weeks().getFirst() + 1 != w.weeks().size(); }
}
