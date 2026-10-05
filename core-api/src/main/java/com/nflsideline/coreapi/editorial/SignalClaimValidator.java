package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.JsonNode;
import com.nflsideline.coreapi.editorial.local.*;
import com.nflsideline.coreapi.llm.GenerationFailure;
import java.util.*;
import java.util.stream.Collectors;
import static com.nflsideline.coreapi.editorial.ClaimSelection.*;
import static com.nflsideline.coreapi.llm.GenerationFailure.Category.*;

/** Contract v5 invariants. Accepts any producer, never consults selector identity. */
final class SignalClaimValidator {
    record Resolved(Claim claim, MatchupAssessment.Candidate candidate) { }
    static final class Validated {
        final Map<String, List<Resolved>> sections;
        final Map<String, Relation> relations;
        final AnalysisContext context;
        private Validated(Map<String, List<Resolved>> sections, Map<String, Relation> relations, AnalysisContext context) {
            this.sections = Map.copyOf(sections); this.relations = Map.copyOf(relations); this.context = context;
        }
    }
    Validated validate(JsonNode root, AnalysisContext context) {
        try { return check(FrozenContext.MAPPER.treeToValue(root, ClaimDocument.class), context); }
        catch (GenerationFailure failure) { throw failure; }
        catch (Exception failure) { throw new GenerationFailure(INVALID_REFERENCE); }
    }
    private Validated check(ClaimDocument doc, AnalysisContext context) {
        if (doc.version() != 5 || !"NONE".equals(doc.thesisTeam()) || !"INCONCLUSIVE".equals(doc.verdict())) fail();
        FrozenContext.check(context, FrozenContext.parameters(context));
        var candidates = MatchupAssessment.enumerateV5(context, FrozenContext.parameters(context));
        var claims = new LinkedHashMap<String, Resolved>();
        var facts = new HashSet<String>();
        for (Claim c : doc.claims()) {
            if (c.id() == null || c.id().isBlank() || c.evidenceIds() == null || c.role() == null
                    || c.period() == null || c.type() == null || c.predicate() == null || c.subject() == null
                    || new HashSet<>(c.evidenceIds()).size() != c.evidenceIds().size()) fail();
            MatchupAssessment.Candidate candidate = null;
            if (c.type() == Kind.LIMITATION) {
                if (c.signals() != null || c.period() != Period.NONE || c.role() != Role.LIMITATION
                        || !c.subject().equals("MATCHUP") || !c.evidenceIds().isEmpty()) fail();
                validateGlobal(c.predicate(), context);
            } else {
                candidate = candidates.stream().filter(x -> x.pairable() && x.evidenceIds().equals(c.evidenceIds())).findFirst().orElseThrow();
                if (!c.subject().equals(candidate.attackTeam()) || c.period() != (candidate.current() ? Period.CURRENT : Period.HISTORICAL)) fail();
                if (c.type() == Kind.MATCHUP) {
                    if (c.predicate() != Predicate.SIGNAL_PROFILE || !candidate.signals().equals(c.signals())
                            || c.role() != (candidate.signals().relation() == SignalDimensions.Relation.POSITIVE_CONVERGENCE
                            ? Role.OPPORTUNITY : Role.LIMITATION)) fail();
                } else if (c.type() == Kind.WINDOW_LIMITATION) {
                    if (c.signals() != null || c.role() != Role.LIMITATION || c.predicate() != SignalEditorialPolicy.internalLimit(candidate)) fail();
                } else fail();
            }
            if (claims.putIfAbsent(c.id(), new Resolved(c, candidate)) != null
                    || !facts.add(c.type() + ":" + c.predicate() + ":" + c.evidenceIds())) fail();
        }
        var sections = new LinkedHashMap<String, List<Resolved>>();
        var used = new HashSet<String>();
        if (!doc.sections().keySet().equals(Set.of("fator_chave", "vantagem_tatica", "alerta_vermelho", "veredito"))) fail();
        for (var entry : doc.sections().entrySet()) {
            if (entry.getValue().isEmpty() || entry.getValue().size() > 19 || new HashSet<>(entry.getValue()).size() != entry.getValue().size()) fail();
            var resolved = new ArrayList<Resolved>();
            for (String id : entry.getValue()) {
                if (!claims.containsKey(id)) fail();
                used.add(id); resolved.add(claims.get(id));
            }
            sections.put(entry.getKey(), List.copyOf(resolved));
        }
        if (!used.equals(claims.keySet())) fail();
        var key = sections.get("fator_chave"); var red = sections.get("alerta_vermelho"); var verdict = sections.get("veredito");
        if (!key.equals(sections.get("vantagem_tatica")) || key.size() > 6 || red.size() > 12
                || key.stream().anyMatch(c -> c.claim().type() == Kind.WINDOW_LIMITATION)
                || key.stream().anyMatch(c -> c.claim().type() == Kind.LIMITATION)
                    && (key.size() != 1 || candidates.stream().anyMatch(MatchupAssessment.Candidate::pairable))
                || !verdict.containsAll(key) || !verdict.containsAll(red)
                || verdict.stream().noneMatch(c -> c.claim().type() == Kind.LIMITATION)) fail();
        var relations = new HashMap<String, Relation>(); var edges = new HashSet<String>();
        for (Link link : doc.links()) {
            var from = claims.get(link.from()); var to = claims.get(link.to());
            if (from == null || to == null || from == to || !red.contains(from) || !key.contains(to)
                    || from.candidate() == null || to.candidate() == null
                    || !edges.add(link.from() + ":" + link.to())) fail();
            if (link.relation() == Relation.INTERNAL_LIMITATION) {
                if (from.claim().type() != Kind.WINDOW_LIMITATION || to.claim().type() != Kind.MATCHUP
                        || !from.claim().evidenceIds().equals(to.claim().evidenceIds())) fail();
            } else if (link.relation() == Relation.ADDITIONAL_RESTRICTION) {
                if (from.claim().type() != Kind.MATCHUP || key.contains(from)
                        || !SignalEditorialPolicy.restricts(from.candidate(), to.candidate())) fail();
            } else if (link.relation() == Relation.INDEPENDENT_OPPORTUNITY) {
                if (from.claim().type() != Kind.MATCHUP || key.contains(from) || from.claim().role() != Role.OPPORTUNITY
                        || from.claim().subject().equals(to.claim().subject())) fail();
            } else fail(); // DIRECT_CONFLICT belongs exclusively to v4.
            var prior = relations.putIfAbsent(link.from(), link.relation());
            if (prior != null && prior != link.relation()) fail();
        }
        for (var r : red) if (r.claim().type() != Kind.LIMITATION && !relations.containsKey(r.claim().id())) fail();
        for (var r : claims.values()) if (r.claim().type() == Kind.WINDOW_LIMITATION && !red.contains(r)) fail();
        var represented = verdict.stream().filter(r -> r.claim().type() == Kind.MATCHUP)
                .map(r -> r.candidate().id()).collect(Collectors.toSet());
        var omitted = new HashSet<String>();
        for (Grouping group : doc.groupings() == null ? List.<Grouping>of() : doc.groupings()) {
            var source = candidates.stream().filter(c -> c.id().equals(group.candidateId())).findFirst().orElseThrow();
            if (represented.contains(source.id()) || !omitted.add(source.id()) || group.representedBy().isEmpty()
                    || group.reason() != GroupReason.GENERAL_SAME_SIGNAL_AND_COVERAGE
                    || new HashSet<>(group.representedBy()).size() != group.representedBy().size()) fail();
            for (String id : group.representedBy()) {
                var target = claims.get(id);
                if (target == null || target.claim().type() != Kind.MATCHUP || !verdict.contains(target)
                        || !SignalEditorialPolicy.redundantGeneral(source, target.candidate())) fail();
            }
        }
        represented.addAll(omitted);
        if (!represented.equals(candidates.stream().filter(MatchupAssessment.Candidate::pairable)
                .map(MatchupAssessment.Candidate::id).collect(Collectors.toSet()))) fail();
        return new Validated(sections, relations, context);
    }
    private void validateGlobal(Predicate predicate, AnalysisContext context) {
        var items = context.evidence();
        var current = items.stream().filter(e -> e.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS).toList();
        var teams = List.of(context.homeTeam(), context.awayTeam());
        var home = weeks(current, teams.getFirst()); var away = weeks(current, teams.getLast());
        boolean valid = switch (predicate) {
            case NO_DATA -> items.isEmpty();
            case PARTIAL_DATA -> !items.isEmpty() && teams.stream().anyMatch(t -> items.stream().noneMatch(e -> e.team().equals(t)));
            case HISTORICAL_ONLY -> !items.isEmpty() && current.isEmpty();
            case SMALL_SAMPLE -> !current.isEmpty() && (home.size() <= 2 || away.size() <= 2);
            case UNEVEN_WINDOWS -> !home.isEmpty() && !away.isEmpty() && !home.equals(away);
            case LIMITED_WINDOW -> teams.stream().allMatch(t -> weeks(items, t).size() <= 3);
            default -> false;
        };
        if (!valid) fail();
    }
    private Set<Integer> weeks(List<Evidence> evidence, String team) {
        return evidence.stream().filter(e -> e.team().equals(team)).map(Evidence::week).collect(Collectors.toSet());
    }
    private void fail() { throw new GenerationFailure(INCOMPATIBLE_PREDICATE); }
}
