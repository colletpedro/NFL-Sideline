package com.nflsideline.coreapi.editorial.local;

import com.nflsideline.coreapi.editorial.*;
import java.util.*;
import static com.nflsideline.coreapi.editorial.ClaimSelection.*;
import static com.nflsideline.coreapi.editorial.local.MatchupAssessment.Classification.*;

/** No numeric ranking, cross-metric voting, provider, model, market or team-name merit. */
public final class LocalRuleSelector implements ClaimSelector {
    public static final String VERSION = "2.0.0";
    public SelectorIdentity identity() { return new SelectorIdentity("local-descriptive-rules", VERSION); }

    public ClaimSelection select(AnalysisContext context, EditorialParameters parameters) {
        FrozenContext.check(context, parameters);
        if (!parameters.equals(FrozenContext.parameters(context))) throw new IllegalArgumentException("Calendar mismatch");
        var candidates = MatchupAssessment.enumerateV5(context, parameters);
        var decisions = new ArrayList<Decision>();
        var eligible = candidates.stream().filter(MatchupAssessment.Candidate::pairable).toList();
        // Lexicographic categorical policy; never sum unrelated indicators.
        var best = eligible;
        if (best.stream().anyMatch(MatchupAssessment.Candidate::adequateCoverage))
            best = best.stream().filter(MatchupAssessment.Candidate::adequateCoverage).toList();
        else if (best.stream().anyMatch(MatchupAssessment.Candidate::current))
            best = best.stream().filter(MatchupAssessment.Candidate::current).toList();
        var coverageTier = best;
        if (best.stream().anyMatch(c -> c.adequateCoverage() && c.foundation() != MetricCatalog.OFF_EPA_PLAY))
            best = best.stream().filter(c -> c.foundation() != MetricCatalog.OFF_EPA_PLAY).toList();
        else if (best.stream().anyMatch(c -> c.foundation() == MetricCatalog.OFF_EPA_PLAY))
            best = best.stream().filter(c -> c.foundation() == MetricCatalog.OFF_EPA_PLAY).toList();
        var foundationTier = best;
        if (best.stream().anyMatch(c -> c.classification() == OPPORTUNITY))
            best = best.stream().filter(c -> c.classification() == OPPORTUNITY).toList();

        var claims = new LinkedHashMap<String, Claim>();
        var links = new ArrayList<Link>();
        for (var c : candidates) {
            Reason reason = !c.pairable() ? Reason.UNPAIRABLE : !coverageTier.contains(c) ? Reason.LOWER_COVERAGE
                    : !foundationTier.contains(c) ? Reason.FOUNDATION_COVERAGE_POLICY
                    : !best.contains(c) ? Reason.PROFILE_BEHIND_OPPORTUNITY
                    : best.size() > 1 ? Reason.EQUAL_ALTERNATIVE : Reason.PRIMARY;
            decisions.add(new Decision(c.id(), reason));
        }
        var key = new ArrayList<String>();
        for (var c : best) { claims.put(c.id(), matchup(c)); key.add(c.id()); }
        var groupings = new ArrayList<Grouping>();
        var visible = new ArrayList<MatchupAssessment.Candidate>();
        for (var c : eligible) {
            var represented = eligible.stream().filter(x -> x.foundation() != MetricCatalog.OFF_EPA_PLAY
                    && SignalEditorialPolicy.redundantGeneral(c, x)).toList();
            if (!best.contains(c) && !represented.isEmpty()) {
                groupings.add(new Grouping(c.id(), represented.stream().map(MatchupAssessment.Candidate::id).toList(),
                        GroupReason.GENERAL_SAME_SIGNAL_AND_COVERAGE));
                decisions.add(new Decision(c.id(), Reason.GENERAL_REDUNDANT));
            } else {
                visible.add(c); claims.put(c.id(), matchup(c));
                if (c.foundation() == MetricCatalog.OFF_EPA_PLAY) decisions.add(new Decision(c.id(), Reason.GENERAL_ADDS_INFORMATION));
            }
        }
        Claim limit = limitation(context);
        claims.put(limit.id(), limit);
        if (key.isEmpty()) key.add(limit.id());
        var red = new ArrayList<String>();
        // A separate factual claim describes the limit of a primary, never self-refutation.
        for (var c : best) {
            String id = "limit:" + c.id();
            var claim = new Claim(id, Kind.WINDOW_LIMITATION, c.attackTeam(), SignalEditorialPolicy.internalLimit(c),
                    c.current() ? Period.CURRENT : Period.HISTORICAL, c.evidenceIds(), Role.LIMITATION);
            claims.put(id, claim); red.add(id);
            links.add(new Link(id, c.id(), Relation.INTERNAL_LIMITATION));
            decisions.add(new Decision(c.id(), Reason.INTERNAL_RESTRICTION));
        }
        for (var c : visible) if (!best.contains(c)) {
            boolean included = false;
            for (var primary : best) {
                Relation relation = SignalEditorialPolicy.restricts(c, primary) ? Relation.ADDITIONAL_RESTRICTION
                        : c.classification() == OPPORTUNITY && !c.attackTeam().equals(primary.attackTeam())
                        ? Relation.INDEPENDENT_OPPORTUNITY : null;
                if (relation != null) {
                    links.add(new Link(c.id(), primary.id(), relation)); included = true;
                    decisions.add(new Decision(c.id(), relation == Relation.ADDITIONAL_RESTRICTION
                            ? Reason.DISTINCT_RESTRICTION : Reason.OPPONENT_OPPORTUNITY));
                }
            }
            if (included) red.add(c.id());
        }
        if (red.isEmpty()) red.add(limit.id());
        var conclusion = new ArrayList<String>();
        for (var c : visible) { conclusion.add(c.id()); decisions.add(new Decision(c.id(), Reason.GROUPED_BY_TEAM)); }
        conclusion.add(limit.id());
        for (var id : red) if (!conclusion.contains(id)) conclusion.add(id);
        var sections = new LinkedHashMap<String, List<String>>();
        sections.put("fator_chave", List.copyOf(key)); sections.put("vantagem_tatica", List.copyOf(key));
        sections.put("alerta_vermelho", List.copyOf(red)); sections.put("veredito", List.copyOf(conclusion));
        return new ClaimSelection(identity(), new ClaimDocument(5, "NONE", "INCONCLUSIVE", List.copyOf(claims.values()),
                Collections.unmodifiableMap(sections), List.copyOf(links), List.copyOf(groupings)), candidates, List.copyOf(decisions));
    }
    private Claim matchup(MatchupAssessment.Candidate c) {
        return new Claim(c.id(), Kind.MATCHUP, c.attackTeam(), Predicate.SIGNAL_PROFILE,
                c.current() ? Period.CURRENT : Period.HISTORICAL, c.evidenceIds(),
                c.classification() == OPPORTUNITY ? Role.OPPORTUNITY : Role.LIMITATION, c.signals());
    }
    private Claim limitation(AnalysisContext context) {
        var current = context.evidence().stream().filter(e -> e.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS).toList();
        var teams = List.of(context.homeTeam(), context.awayTeam());
        Predicate p;
        if (context.evidence().isEmpty()) p = Predicate.NO_DATA;
        else if (teams.stream().anyMatch(t -> context.evidence().stream().noneMatch(e -> e.team().equals(t)))) p = Predicate.PARTIAL_DATA;
        else if (current.isEmpty()) p = Predicate.HISTORICAL_ONLY;
        else if (!weeks(current, teams.get(0)).equals(weeks(current, teams.get(1)))
                && !weeks(current, teams.get(0)).isEmpty() && !weeks(current, teams.get(1)).isEmpty()) p = Predicate.UNEVEN_WINDOWS;
        else if (teams.stream().anyMatch(t -> weeks(current, t).size() <= 2)) p = Predicate.SMALL_SAMPLE;
        else p = Predicate.LIMITED_WINDOW;
        return new Claim("limitation", Kind.LIMITATION, "MATCHUP", p, Period.NONE, List.of(), Role.LIMITATION);
    }
    private Set<Integer> weeks(List<Evidence> items, String team) {
        var weeks = new TreeSet<Integer>(); items.stream().filter(e -> e.team().equals(team)).forEach(e -> weeks.add(e.week())); return weeks;
    }
}
