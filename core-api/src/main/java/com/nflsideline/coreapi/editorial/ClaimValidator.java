package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.JsonNode;
import com.nflsideline.coreapi.llm.GenerationFailure;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static com.nflsideline.coreapi.llm.GenerationFailure.Category.*;

/** Versioned semantic validation, independent of selector identity and controlled realization. */
public final class ClaimValidator {
    private static final List<String> SECTIONS = List.of("fator_chave", "vantagem_tatica", "alerta_vermelho", "veredito");

    public ClaimValidator() { }

    public ValidatedClaims validate(JsonNode root, AnalysisContext context) {
        if (root != null && root.path("contract_version").isIntegralNumber() && root.path("contract_version").asInt() == 5)
            return new ValidatedClaims(new SignalClaimValidator().validate(root, context));
        if (root == null || !root.isObject() || !root.path("contract_version").isIntegralNumber()
                || !List.of(3, 4).contains(root.path("contract_version").asInt(-1))
                || !root.path("claims").isArray() || !root.path("sections").isObject()) fail(MISSING_FIELDS);
        int version = root.path("contract_version").asInt();
        String thesis = required(root, "thesis_team");
        if (!thesis.equals(context.homeTeam()) && !thesis.equals(context.awayTeam()) && !thesis.equals("NONE")) fail(INVALID_REFERENCE);
        String verdict = required(root, "verdict");
        if (!List.of("INCONCLUSIVE", "SLIGHT_HOME", "SLIGHT_AWAY").contains(verdict)) fail(INCOMPATIBLE_PREDICATE);
        String favored = verdict.equals("SLIGHT_HOME") ? context.homeTeam() : verdict.equals("SLIGHT_AWAY") ? context.awayTeam() : "NONE";
        if (!verdict.equals("INCONCLUSIVE") && !favored.equals(thesis)) fail(INCOMPATIBLE_PREDICATE);
        Map<String, Evidence> evidence = new HashMap<>();
        for (Evidence item : context.evidence()) {
            if (!item.team().equals(context.homeTeam()) && !item.team().equals(context.awayTeam())) fail(INVALID_REFERENCE);
            if (item.value() == null || item.unit() != item.metric().unit()
                    || !item.id().equals(Evidence.observed(item.team(), item.metric(), item.season(), item.week(),
                    item.origin() == Evidence.Origin.HISTORICAL_REFERENCE, item.value(), item.volume()).id()))
                fail(INVALID_REFERENCE);
            Evidence previous = evidence.putIfAbsent(item.id(), item);
            if (previous != null && (version == 3 || !previous.equals(item))) fail(INVALID_REFERENCE);
        }
        Map<String, Claim> claims = new HashMap<>();
        Map<String, EvidenceWindow> windows = new HashMap<>();
        context.windows().forEach(window -> windows.put(window.id(), window));
        for (JsonNode node : root.path("claims")) {
            Claim claim = validate(node, evidence, windows, context, version);
            if (claims.put(claim.id, claim) != null) fail(INVALID_REFERENCE);
        }
        Map<String, List<Claim>> sections = new HashMap<>();
        Set<String> used = new HashSet<>();
        for (String name : SECTIONS) {
            JsonNode ids = root.path("sections").path(name);
            if (!ids.isArray() || ids.isEmpty()) fail(MISSING_FIELDS);
            List<Claim> resolved = new ArrayList<>();
            Set<String> sectionIds = new HashSet<>();
            for (JsonNode id : ids) {
                if (!id.isTextual() || !sectionIds.add(id.asText())) fail(INVALID_REFERENCE);
                used.add(id.asText());
                Claim claim = claims.get(id.asText());
                if (claim == null) fail(INVALID_REFERENCE);
                resolved.add(claim);
            }
            sections.put(name, resolved);
        }
        if (used.size() != claims.size()) fail(INVALID_REFERENCE);
        if (version == 4) {
            var relations = validateNeutral(root, context, claims, sections);
            return new ValidatedClaims(version, thesis, verdict, sections, relations);
        }
        List<Claim> key = sections.get("fator_chave");
        if (key.size() != 1 || key.getFirst().role == Role.COUNTER) fail(INCOMPATIBLE_PREDICATE);
        if (!thesis.equals("NONE") && key.getFirst().type != Type.LIMITATION
                && !key.getFirst().subject.equals(thesis)) fail(INCOMPATIBLE_PREDICATE);
        List<Claim> advantage = sections.get("vantagem_tatica");
        boolean demonstrated = advantage.stream().anyMatch(c -> c.predicate == Predicate.POSITIVE_EPA_CONVERGENCE);
        if (demonstrated) {
            if (advantage.size() != 1 || thesis.equals("NONE")
                    || advantage.stream().anyMatch(c -> c.type != Type.MATCHUP || c.role != Role.SUPPORT
                    || !c.subject.equals(thesis) || c.period != Period.CURRENT)) fail(INCOMPATIBLE_PREDICATE);
        } else if (advantage.size() != 1 || !List.of(Predicate.NO_MATCHUP_SUPPORT, Predicate.ATTACK_DEFENSE_PROFILE)
                .contains(advantage.getFirst().predicate)) {
            fail(INCOMPATIBLE_PREDICATE);
        }
        if (!verdict.equals("INCONCLUSIVE") && !demonstrated) fail(INCOMPATIBLE_PREDICATE);
        List<Claim> red = sections.get("alerta_vermelho");
        if (red.size() != 1 || (red.getFirst().role != Role.COUNTER && red.getFirst().role != Role.LIMITATION)) fail(INCOMPATIBLE_PREDICATE);
        if (red.getFirst().role == Role.COUNTER) {
            Claim counter = red.getFirst();
            if (thesis.equals("NONE") || !List.of(Type.COMPARISON, Type.WINDOW_COMPARISON, Type.MATCHUP).contains(counter.type)
                    || counter.subject.equals(thesis) || counter.period != Period.CURRENT
                    || !counter.thesisId.equals(key.getFirst().id) || key.getFirst().role != Role.SUPPORT)
                fail(INCOMPATIBLE_PREDICATE);
        }
        List<Claim> conclusion = sections.get("veredito");
        if (conclusion.size() != 1 || conclusion.getFirst().type != Type.LIMITATION) fail(INCOMPATIBLE_PREDICATE);
        return new ValidatedClaims(version, thesis, verdict, sections);
    }

    private Claim validate(JsonNode node, Map<String, Evidence> evidence, Map<String, EvidenceWindow> windows,
                           AnalysisContext context, int version) {
        String id = required(node, "claim_id");
        Type type = value(Type.class, required(node, "type"));
        Predicate predicate = value(Predicate.class, required(node, "predicate"));
        Role role = value(Role.class, required(node, "role"));
        if (version == 3 && (role == Role.OPPORTUNITY || predicate == Predicate.CONFLICTING_EPA_PROFILE)) fail(INCOMPATIBLE_PREDICATE);
        Period period = value(Period.class, required(node, "period"));
        String subject = required(node, "subject");
        String thesisId = node.path("thesis_id").isTextual() ? node.path("thesis_id").asText() : "";
        JsonNode refs = node.path("evidence_ids");
        if (!refs.isArray()) fail(MISSING_FIELDS);
        List<Evidence> items = new ArrayList<>();
        List<EvidenceWindow> slices = new ArrayList<>();
        Set<String> ids = new HashSet<>();
        for (JsonNode ref : refs) {
            if (!ref.isTextual() || !ids.add(ref.asText())) fail(INVALID_REFERENCE);
            if (type == Type.WINDOW_COMPARISON || type == Type.MATCHUP) {
                EvidenceWindow found = windows.get(ref.asText());
                if (found == null) fail(INVALID_REFERENCE);
                validateOrigin(period, found.origin());
                slices.add(found);
                continue;
            }
            if (!evidence.containsKey(ref.asText())) fail(INVALID_REFERENCE);
            Evidence found = evidence.get(ref.asText());
            validateOrigin(period, found.origin());
            items.add(found);
        }
        MetricCatalog metric = !slices.isEmpty() ? slices.getFirst().metric() : items.isEmpty() ? null : items.getFirst().metric();
        if (type == Type.OBSERVATION) {
            if (period == Period.NONE || predicate != Predicate.RECORDED || items.size() != 1
                    || !subject.equals(items.getFirst().team())) fail(INCOMPATIBLE_PREDICATE);
        } else if (type == Type.COMPARISON) {
            if (period == Period.NONE || !List.of(Predicate.GREATER_THAN, Predicate.LESS_THAN).contains(predicate) || items.size() != 2
                    || !subject.equals(items.getFirst().team()) || items.get(0).team().equals(items.get(1).team())
                    || !items.get(0).metric().equals(items.get(1).metric())
                    || items.get(0).season() != items.get(1).season() || items.get(0).week() != items.get(1).week())
                fail(INCOMPATIBLE_PREDICATE);
            int result = items.get(0).value().compareTo(items.get(1).value());
            if (predicate == Predicate.GREATER_THAN && result <= 0 || predicate == Predicate.LESS_THAN && result >= 0)
                fail(FALSE_COMPARISON);
            if (role != Role.LIMITATION && (metric.direction() == MetricCatalog.Direction.NONE
                    || predicate == Predicate.GREATER_THAN && metric.direction() != MetricCatalog.Direction.HIGHER
                    || predicate == Predicate.LESS_THAN && metric.direction() != MetricCatalog.Direction.LOWER))
                fail(INCOMPATIBLE_PREDICATE);
        } else if (type == Type.WINDOW_COMPARISON || type == Type.MATCHUP) {
            if (period == Period.NONE || slices.size() != 2 || !subject.equals(slices.getFirst().team()))
                fail(INCOMPATIBLE_PREDICATE);
            EvidenceWindow first = slices.get(0), second = slices.get(1);
            if (first.team().equals(second.team()) || first.season() != second.season()
                    || first.origin() != second.origin()) fail(INCOMPATIBLE_PREDICATE);
            if (type == Type.WINDOW_COMPARISON) {
                if (first.metric() != second.metric() || first.aggregation() != second.aggregation()
                        || !List.of(Predicate.GREATER_THAN, Predicate.LESS_THAN).contains(predicate))
                    fail(INCOMPATIBLE_PREDICATE);
                int result = first.value().compareTo(second.value());
                if (predicate == Predicate.GREATER_THAN && result <= 0 || predicate == Predicate.LESS_THAN && result >= 0)
                    fail(FALSE_COMPARISON);
                if (role != Role.LIMITATION && (metric.direction() == MetricCatalog.Direction.NONE
                        || predicate == Predicate.GREATER_THAN && metric.direction() != MetricCatalog.Direction.HIGHER
                        || predicate == Predicate.LESS_THAN && metric.direction() != MetricCatalog.Direction.LOWER))
                    fail(INCOMPATIBLE_PREDICATE);
            } else {
                if (first.metric().defensiveCounterpart() != second.metric()) fail(INCOMPATIBLE_PREDICATE);
                if (predicate == Predicate.POSITIVE_EPA_CONVERGENCE) {
                    if (period != Period.CURRENT || role == Role.LIMITATION || !converges(first, second))
                        fail(INCOMPATIBLE_PREDICATE);
                } else if (predicate == Predicate.CONFLICTING_EPA_PROFILE) {
                    if (version != 4 || role != Role.LIMITATION
                            || !com.nflsideline.coreapi.editorial.local.MatchupAssessment.conflicting(first, second))
                        fail(INCOMPATIBLE_PREDICATE);
                } else if (predicate != Predicate.ATTACK_DEFENSE_PROFILE || role != Role.LIMITATION)
                    fail(INCOMPATIBLE_PREDICATE);
            }
        } else {
            if (period != Period.NONE || items.size() != 0 || !subject.equals("MATCHUP") || role != Role.LIMITATION
                    || !List.of(Predicate.NO_DATA, Predicate.HISTORICAL_ONLY, Predicate.SMALL_SAMPLE, Predicate.LIMITED_WINDOW,
                            Predicate.NO_MATCHUP_SUPPORT, Predicate.UNEVEN_WINDOWS, Predicate.MIXED_SIGNALS,
                            Predicate.PARTIAL_DATA).contains(predicate)) fail(INCOMPATIBLE_PREDICATE);
            long current = context.evidence().stream().filter(e -> e.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS).count();
            if (predicate == Predicate.NO_MATCHUP_SUPPORT && hasMatchupSignal(context)
                    || predicate == Predicate.PARTIAL_DATA && (context.evidence().isEmpty()
                    || List.of(context.homeTeam(), context.awayTeam()).stream().allMatch(team -> context.evidence().stream().anyMatch(e -> e.team().equals(team))))
                    || predicate == Predicate.UNEVEN_WINDOWS && !unevenWindows(context)
                    || predicate == Predicate.MIXED_SIGNALS && context.windows().stream().noneMatch(w -> w.metric().unit() == MetricCatalog.Unit.EPA
                            && w.minimum().signum() < 0 && w.maximum().signum() > 0)
                    || predicate == Predicate.NO_DATA && !context.evidence().isEmpty()
                    || predicate == Predicate.HISTORICAL_ONLY && (current != 0 || context.evidence().isEmpty())
                    || predicate == Predicate.LIMITED_WINDOW && List.of(context.homeTeam(), context.awayTeam())
                    .stream().anyMatch(team -> context.evidence().stream().filter(e -> e.team().equals(team))
                            .map(Evidence::week).distinct().count() > 3)
                    || predicate == Predicate.SMALL_SAMPLE && (current == 0 || List.of(context.homeTeam(), context.awayTeam())
                    .stream().noneMatch(team -> context.evidence().stream()
                            .filter(e -> e.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS && e.team().equals(team))
                            .map(Evidence::week).distinct().count() <= 2))) fail(INCOMPATIBLE_PREDICATE);
        }
        if (role == Role.COUNTER && thesisId.isBlank()) fail(INVALID_REFERENCE);
        return new Claim(id, type, subject, predicate, period, items, slices, role, thesisId, metric);
    }

    private void validateOrigin(Period period, Evidence.Origin origin) {
        if (period == Period.CURRENT && origin != Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS
                || period == Period.HISTORICAL && origin != Evidence.Origin.HISTORICAL_REFERENCE)
            fail(INVALID_REFERENCE);
    }

    private boolean converges(EvidenceWindow attack, EvidenceWindow defense) {
        return attack.metric().defensiveCounterpart() == defense.metric()
                && !attack.team().equals(defense.team()) && attack.season() == defense.season()
                && attack.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS && defense.origin() == attack.origin()
                && attack.missingMetricWeeks().isEmpty() && defense.missingMetricWeeks().isEmpty()
                && attack.positiveInEveryObservedWeek() && defense.positiveInEveryObservedWeek();
    }

    private boolean hasMatchupSignal(AnalysisContext context) {
        List<EvidenceWindow> windows = context.windows();
        return windows.stream().anyMatch(a -> windows.stream().anyMatch(d -> converges(a, d)));
    }

    private boolean unevenWindows(AnalysisContext context) {
        Set<Integer> home = new HashSet<>(), away = new HashSet<>();
        context.evidence().stream().filter(e -> e.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS)
                .forEach(e -> (e.team().equals(context.homeTeam()) ? home : away).add(e.week()));
        return !home.isEmpty() && !away.isEmpty() && !home.equals(away);
    }

    /** Only this validator can construct the value consumed by the renderer. */
    public static final class ValidatedClaims {
        private final SignalClaimValidator.Validated signals;
        private ValidatedClaims(SignalClaimValidator.Validated signals) {
            this.version = 5; this.thesis = "NONE"; this.verdict = "INCONCLUSIVE";
            this.sections = Map.of(); this.relations = Map.of(); this.signals = signals;
        }
        SignalClaimValidator.Validated signals() { return signals; }
        private final int version;
        private final String thesis, verdict;
        private final Map<String, List<Claim>> sections;
        private final Map<String, String> relations;
        private ValidatedClaims(int version, String thesis, String verdict, Map<String, List<Claim>> sections) {
            this(version, thesis, verdict, sections, Map.of());
        }
        private ValidatedClaims(int version, String thesis, String verdict, Map<String, List<Claim>> sections, Map<String, String> relations) {
            this.version = version; this.thesis = thesis; this.verdict = verdict; this.signals = null;
            var copy = new HashMap<String, List<Claim>>(); sections.forEach((k,v) -> copy.put(k, List.copyOf(v)));
            this.sections = Map.copyOf(copy); this.relations = Map.copyOf(relations);
        }
        public int version() { return version; }
        String thesis() { return thesis; }
        String verdict() { return verdict; }
        Map<String, List<Claim>> sections() { return sections; }
        Map<String, String> relations() { return relations; }
    }

    private Map<String, String> validateNeutral(JsonNode root, AnalysisContext context, Map<String, Claim> claims,
                                              Map<String, List<Claim>> sections) {
        if (!root.path("thesis_team").asText().equals("NONE") || !root.path("verdict").asText().equals("INCONCLUSIVE"))
            fail(INCOMPATIBLE_PREDICATE);
        var parameters = com.nflsideline.coreapi.editorial.local.FrozenContext.parameters(context);
        com.nflsideline.coreapi.editorial.local.FrozenContext.check(context, parameters);
        var candidates = com.nflsideline.coreapi.editorial.local.MatchupAssessment.enumerate(context, parameters);
        for (var claim : claims.values()) {
            if (!List.of(Type.MATCHUP, Type.LIMITATION).contains(claim.type)
                    || !List.of(Role.OPPORTUNITY, Role.LIMITATION).contains(claim.role)
                    || !claim.thesisId.isEmpty()) fail(INCOMPATIBLE_PREDICATE);
            if (claim.type == Type.MATCHUP) {
                if (claim.predicate == Predicate.POSITIVE_EPA_CONVERGENCE) {
                    if (claim.role != Role.OPPORTUNITY || candidates.stream().noneMatch(c -> c.adequateCoverage()
                            && c.evidenceIds().equals(claim.windows.stream().map(EvidenceWindow::id).toList())))
                        fail(INCOMPATIBLE_PREDICATE);
                } else if (claim.role != Role.LIMITATION) fail(INCOMPATIBLE_PREDICATE);
            }
        }
        var key = sections.get("fator_chave");
        var advantage = sections.get("vantagem_tatica");
        var red = sections.get("alerta_vermelho");
        var conclusion = sections.get("veredito");
        if (key.size() > 6 || !key.equals(advantage) || red.size() > 6 || conclusion.size() > 13
                || key.size() > 1 && key.stream().anyMatch(c -> c.type != Type.MATCHUP)
                || conclusion.stream().noneMatch(c -> c.type == Type.LIMITATION)
                || !conclusion.containsAll(red)) fail(INCOMPATIBLE_PREDICATE);
        // A neutral verdict must preserve every eligible opportunity, even outside the primary tier.
        var expected = candidates.stream().filter(c -> c.classification()
                        == com.nflsideline.coreapi.editorial.local.MatchupAssessment.Classification.OPPORTUNITY)
                .map(c -> c.evidenceIds()).collect(java.util.stream.Collectors.toSet());
        var actual = conclusion.stream().filter(c -> c.predicate == Predicate.POSITIVE_EPA_CONVERGENCE)
                .map(c -> c.windows.stream().map(EvidenceWindow::id).toList()).collect(java.util.stream.Collectors.toSet());
        if (!actual.equals(expected)) fail(INCOMPATIBLE_PREDICATE);
        // Multiple IDs for the same fact cannot manufacture additional support.
        var facts = new HashSet<String>();
        for (var c : claims.values()) if (!facts.add(c.type + ":" + c.predicate + ":" + c.subject + ":"
                + c.windows.stream().map(EvidenceWindow::id).toList())) fail(INVALID_REFERENCE);
        if (!root.path("links").isArray()) fail(MISSING_FIELDS);
        var relations = new HashMap<String, String>();
        var seenLinks = new HashSet<String>();
        for (JsonNode link : root.path("links")) {
            String from = required(link, "from"), to = required(link, "to"), relation = required(link, "relation");
            Claim source = claims.get(from), target = claims.get(to);
            if (source == null || target == null || !red.contains(source) || !key.contains(target)
                    || source.type != Type.MATCHUP || target.type != Type.MATCHUP
                    || !seenLinks.add(from + ":" + to)) fail(INVALID_REFERENCE);
            if (relation.equals("DIRECT_CONFLICT")) {
                if (source.predicate != Predicate.CONFLICTING_EPA_PROFILE || !source.windows.equals(target.windows))
                    fail(INCOMPATIBLE_PREDICATE);
            } else if (relation.equals("INDEPENDENT_OPPORTUNITY")) {
                if (source.predicate != Predicate.POSITIVE_EPA_CONVERGENCE || source.subject.equals(target.subject))
                    fail(INCOMPATIBLE_PREDICATE);
            } else fail(INCOMPATIBLE_PREDICATE);
            String prior = relations.putIfAbsent(from, relation);
            if (prior != null && !prior.equals(relation)) fail(INCOMPATIBLE_PREDICATE);
        }
        if (red.stream().anyMatch(c -> c.type == Type.MATCHUP && !relations.containsKey(c.id))) fail(INVALID_REFERENCE);
        return relations;
    }

    private String required(JsonNode node, String key) {
        JsonNode value = node.path(key);
        if (!value.isTextual() || value.asText().isBlank()) fail(MISSING_FIELDS);
        return value.asText();
    }
    private <T extends Enum<T>> T value(Class<T> type, String raw) {
        try { return Enum.valueOf(type, raw); }
        catch (IllegalArgumentException failure) { throw new GenerationFailure(INCOMPATIBLE_PREDICATE); }
    }
    private void fail(GenerationFailure.Category category) { throw new GenerationFailure(category); }
    enum Type { OBSERVATION, COMPARISON, WINDOW_COMPARISON, MATCHUP, LIMITATION }
    enum Predicate { RECORDED, GREATER_THAN, LESS_THAN, ATTACK_DEFENSE_PROFILE, POSITIVE_EPA_CONVERGENCE, CONFLICTING_EPA_PROFILE,
        NO_DATA, HISTORICAL_ONLY, SMALL_SAMPLE, LIMITED_WINDOW, NO_MATCHUP_SUPPORT, UNEVEN_WINDOWS, MIXED_SIGNALS, PARTIAL_DATA }
    enum Role { SUPPORT, COUNTER, LIMITATION, OPPORTUNITY }
    enum Period { CURRENT, HISTORICAL, NONE }
    record Claim(String id, Type type, String subject, Predicate predicate, Period period,
                         List<Evidence> items, List<EvidenceWindow> windows, Role role, String thesisId, MetricCatalog metric) { }
}
