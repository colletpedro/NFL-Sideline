package com.nflsideline.coreapi.editorial.local;

import com.nflsideline.coreapi.editorial.*;
import java.util.*;
import static com.nflsideline.coreapi.editorial.ClaimSelection.*;
import static com.nflsideline.coreapi.editorial.local.MatchupAssessment.Classification.*;

/** No numeric ranking, cross-metric voting, provider, model, market or team-name merit. */
public final class LegacyLocalRuleSelector implements ClaimSelector {
    public static final String VERSION = "1.0.0";
    public SelectorIdentity identity() { return new SelectorIdentity("local-descriptive-rules", VERSION); }

    public ClaimSelection select(AnalysisContext context, EditorialParameters parameters) {
        FrozenContext.check(context, parameters);
        if (!parameters.equals(FrozenContext.parameters(context))) throw new IllegalArgumentException("Calendar mismatch");
        var candidates = MatchupAssessment.enumerate(context, parameters);
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
        for (var c : best) { Claim claim = matchup(c); claims.put(claim.id(), claim); key.add(claim.id()); }
        Claim limit = limitation(context);
        claims.put(limit.id(), limit);
        if (key.isEmpty()) key.add(limit.id());
        var red = new ArrayList<String>();
        // First examine the exact primary foundation/windows for sign contradiction.
        for (var c : best) if (c.classification() == CONFLICTING) {
            red.add(c.id());
            links.add(new Link(c.id(), c.id(), Relation.DIRECT_CONFLICT));
            decisions.add(new Decision(c.id(), Reason.DIRECT_OBJECTION));
        }
        if (red.isEmpty()) {
            decisions.add(new Decision("selection", Reason.NO_DIRECT_OBJECTION));
            var primaryTeams = best.stream().map(MatchupAssessment.Candidate::attackTeam).distinct().toList();
            if (primaryTeams.size() == 1) {
                for (var c : candidates) if (c.classification() == OPPORTUNITY && !c.attackTeam().equals(primaryTeams.getFirst())) {
                    claims.put(c.id(), matchup(c)); red.add(c.id());
                    // Every equally sustained primary is linked; no arbitrary tie break.
                    for (var primary : best) links.add(new Link(c.id(), primary.id(), Relation.INDEPENDENT_OPPORTUNITY));
                    decisions.add(new Decision(c.id(), Reason.OPPONENT_OPPORTUNITY));
                }
            }
        }
        if (red.isEmpty()) { red.add(limit.id()); decisions.add(new Decision(limit.id(), Reason.FACTUAL_LIMITATION)); }
        var conclusion = new ArrayList<String>();
        conclusion.add(limit.id());
        for (var c : candidates) if (c.classification() == OPPORTUNITY) {
            claims.put(c.id(), matchup(c)); conclusion.add(c.id());
            decisions.add(new Decision(c.id(), Reason.PRESERVED_IN_VERDICT));
        }
        // Keep actual objections in the conclusion, including within-window contradictions.
        for (var id : red) if (!conclusion.contains(id)) conclusion.add(id);
        var sections = new LinkedHashMap<String, List<String>>();
        sections.put("fator_chave", List.copyOf(key)); sections.put("vantagem_tatica", List.copyOf(key));
        sections.put("alerta_vermelho", List.copyOf(red)); sections.put("veredito", List.copyOf(conclusion));
        return new ClaimSelection(identity(), new ClaimDocument(4, "NONE", "INCONCLUSIVE", List.copyOf(claims.values()),
                Collections.unmodifiableMap(sections), List.copyOf(links)), candidates, List.copyOf(decisions));
    }
    private Claim matchup(MatchupAssessment.Candidate c) {
        return new Claim(c.id(), Kind.MATCHUP, c.attackTeam(), c.classification() == OPPORTUNITY ? Predicate.POSITIVE_EPA_CONVERGENCE
                : c.classification() == CONFLICTING ? Predicate.CONFLICTING_EPA_PROFILE : Predicate.ATTACK_DEFENSE_PROFILE,
                c.current() ? Period.CURRENT : Period.HISTORICAL, c.evidenceIds(),
                c.classification() == OPPORTUNITY ? Role.OPPORTUNITY : Role.LIMITATION);
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
