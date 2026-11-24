package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.editorial.local.FrozenContext;
import com.nflsideline.coreapi.editorial.local.LocalGenerationService;
import com.nflsideline.coreapi.editorial.local.MatchupAssessment;
import com.nflsideline.coreapi.editorial.local.SignalEditorialPolicy;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;
import static com.nflsideline.coreapi.editorial.ClaimSelection.*;

/** A factual projection of the already resolved v5 claims and their frozen evidence. */
public final class VisualAnalysisProjector {
    public static final String VERSION = "visual-projector-1.0.0";
    public static final class UnsupportedVisualContract extends RuntimeException {
        public UnsupportedVisualContract(String message) { super(message); }
    }
    private static final JsonNode COPY = copy();
    private VisualAnalysisProjector() { }

    private static JsonNode copy() {
        try (var stream = VisualAnalysisProjector.class.getResourceAsStream("/visual-analysis-v1-copy-catalog.json")) {
            if (stream == null) throw new IllegalStateException("Missing visual copy catalog");
            return FrozenContext.MAPPER.readTree(stream);
        } catch (IOException e) { throw new IllegalStateException("Invalid visual copy catalog", e); }
    }
    private static ObjectNode obj() { return FrozenContext.MAPPER.createObjectNode(); }
    private static ArrayNode array(Collection<String> values) { return FrozenContext.MAPPER.valueToTree(values); }
    private static String foundation(MetricCatalog metric) {
        return switch (metric) {
            case OFF_EPA_PASS -> "PASS";
            case OFF_EPA_RUSH -> "RUSH";
            case OFF_EPA_PLAY -> "GENERAL";
            default -> throw new IllegalArgumentException("Unsupported foundation");
        };
    }
    private static String seriesId(EvidenceWindow window) {
        return "s:" + window.team() + ":" + (window.metric().isOffenseEpa() ? "OFF" : "DEF") + ":"
                + foundation(window.metric().isOffenseEpa() ? window.metric() : switch (window.metric()) {
                    case DEF_EPA_PASS -> MetricCatalog.OFF_EPA_PASS;
                    case DEF_EPA_RUSH -> MetricCatalog.OFF_EPA_RUSH;
                    case DEF_EPA_PLAY -> MetricCatalog.OFF_EPA_PLAY;
                    default -> throw new IllegalArgumentException("Unsupported metric");
                });
    }
    private static String display(BigDecimal value) {
        if (value.signum() != 0 && value.abs().compareTo(new BigDecimal("0.0005")) < 0)
            return value.signum() > 0 ? "0 < EPA < 0,0005" : "-0,0005 < EPA < 0";
        String rounded = value.setScale(3, RoundingMode.HALF_UP).toPlainString().replace('.', ',');
        return value.signum() > 0 ? "+" + rounded : rounded;
    }
    private static String decimal(BigDecimal value) {
        if (value.signum() == 0) return "0";
        return value.stripTrailingZeros().toPlainString();
    }
    private static ObjectNode restriction(String id, String claimId, String code, List<String> encounters, List<String> evidence) {
        JsonNode text = COPY.path("restrictions").path(code);
        if (!text.isTextual()) throw new IllegalArgumentException("Unknown restriction");
        var node = obj().put("id", id);
        if (claimId == null) node.putNull("claimId"); else node.put("claimId", claimId);
        node.put("code", code).set("encounterIds", array(encounters));
        node.set("evidenceIds", array(evidence)); node.put("text", text.asText());
        return node;
    }
    private static List<String> evidenceIds(MatchupAssessment.Candidate c) {
        var ids = new ArrayList<String>();
        if (c.attack() != null) ids.addAll(c.attack().evidenceIds());
        if (c.defense() != null) ids.addAll(c.defense().evidenceIds());
        return List.copyOf(ids);
    }
    private static String restrictionCode(Predicate predicate) {
        return switch (predicate) {
            case COVERAGE_LIMIT -> "COVERAGE_LIMIT";
            case SAMPLE_LIMIT, SMALL_SAMPLE -> "SAMPLE_LIMIT";
            case SIGN_VARIATION_LIMIT -> "SIGN_VARIATION_LIMIT";
            case LIMITED_SCOPE, LIMITED_WINDOW -> "LIMITED_SCOPE";
            case HISTORICAL_ONLY -> "HISTORICAL_ONLY";
            case NO_DATA -> "NO_DATA";
            case PARTIAL_DATA -> "PARTIAL_DATA";
            case UNEVEN_WINDOWS -> "UNEVEN_WINDOWS";
            default -> throw new IllegalArgumentException("Unsupported restriction predicate");
        };
    }
    private static String secondaryCode(MatchupAssessment.Candidate c) {
        if (c.attack().origin() == Evidence.Origin.HISTORICAL_REFERENCE) return "HISTORICAL_ONLY";
        if (!c.adequateCoverage()) return "COVERAGE_LIMIT";
        if (c.signals().attack().pattern() == SignalDimensions.Pattern.MIXED_SIGNS
                || c.signals().defense().pattern() == SignalDimensions.Pattern.MIXED_SIGNS) return "SIGN_VARIATION_LIMIT";
        if (c.attack().weeks().size() <= 2 || c.defense().weeks().size() <= 2) return "SAMPLE_LIMIT";
        return "LIMITED_SCOPE";
    }
    public static ObjectNode project(AnalysisContext context, EditorialParameters parameters,
                                     ClaimValidator.ValidatedClaims validated, ClaimDocument claims,
                                     LocalGenerationService.Identity identity, String declaredAsOfDate) {
        if (validated.version() != 5 || claims.version() != 5 || !"2.0.0".equals(identity.selector().version()))
            throw new IllegalArgumentException("Visual projection requires validated local v5");
        FrozenContext.check(context, parameters);
        if (!parameters.equals(FrozenContext.parameters(context))) throw new IllegalArgumentException("Calendar mismatch");
        if (parameters.season() > 2200 || context.evidence().stream().anyMatch(e -> e.metric().name().matches("(OFF|DEF)_EPA_(PASS|RUSH|PLAY)")
                && e.volume() != null && e.volume() <= 0))
            throw new UnsupportedVisualContract("Calendar or denominator is outside visual v1 schema");
        var resolved = validated.signals();
        var candidates = MatchupAssessment.enumerateV5(context, parameters);
        var byId = new LinkedHashMap<String, MatchupAssessment.Candidate>();
        candidates.forEach(c -> byId.put(c.id(), c));
        var resolvedClaims = new LinkedHashMap<String, SignalClaimValidator.Resolved>();
        resolved.sections.values().forEach(section -> section.forEach(r -> resolvedClaims.put(r.claim().id(), r)));
        var grouped = new HashMap<String, Grouping>();
        for (var grouping : claims.groupings()) {
            var source = byId.get(grouping.candidateId());
            if (source == null || grouping.reason() != GroupReason.GENERAL_SAME_SIGNAL_AND_COVERAGE
                    || grouping.representedBy().stream().anyMatch(id -> !SignalEditorialPolicy.redundantGeneral(source, byId.get(id))))
                throw new IllegalArgumentException("Invalid validated grouping");
            grouped.put(source.id(), grouping);
        }
        JsonNode game;
        try { game = FrozenContext.MAPPER.readTree(context.canonicalJson()).path("game"); }
        catch (IOException e) { throw new IllegalArgumentException("Invalid context", e); }
        if (game.path("game_id").asText().length() > 180)
            throw new UnsupportedVisualContract("Game id exceeds visual v1 schema");
        if (declaredAsOfDate != null) {
            try {
                if (!java.time.LocalDate.parse(declaredAsOfDate).toString().equals(declaredAsOfDate))
                    throw new IllegalArgumentException("Invalid declared date");
            } catch (java.time.format.DateTimeParseException e) { throw new IllegalArgumentException("Invalid declared date", e); }
        }
        String phase = parameters.phase();
        if (!Set.of("REG", "POST").contains(phase)) throw new UnsupportedVisualContract("Visual contract cannot represent phase " + phase);
        var out = obj().put("schemaVersion", "visual-analysis-1.0.0").put("projectorVersion", VERSION)
                .put("mode", "LOCAL_RULES_DEVELOPMENT").put("publicationApproved", false);
        out.set("source", obj().put("kind", "VALIDATED_LOCAL_RESULT").put("resultIdentity", identity.hash())
                .put("contextSha256", identity.contextSha256()).put("claimsContractVersion", 5)
                .put("selectorVersion", identity.selector().version()));
        out.set("game", obj().put("gameId", game.path("game_id").asText()).put("season", parameters.season())
                .put("week", parameters.gameWeek()).put("phase", phase)
                .put("awayTeam", context.awayTeam()).put("homeTeam", context.homeTeam()));
        var scope = obj().put("moment", "PREGAME");
        if (declaredAsOfDate == null) scope.putNull("declaredAsOfDate"); else scope.put("declaredAsOfDate", declaredAsOfDate);
        scope.put("temporalGuarantee", "WEEK_ORDER_ONLY").set("expectedCurrentWeeks", FrozenContext.MAPPER.valueToTree(parameters.expectedRecentWeeks()));
        scope.put("opponentAdjusted", false); out.set("scope", scope);
        var evidence = out.putArray("evidence");
        var eligible = context.evidence().stream().filter(e -> Set.of(MetricCatalog.OFF_EPA_PASS, MetricCatalog.OFF_EPA_RUSH,
                MetricCatalog.OFF_EPA_PLAY, MetricCatalog.DEF_EPA_PASS, MetricCatalog.DEF_EPA_RUSH,
                MetricCatalog.DEF_EPA_PLAY).contains(e.metric())).sorted(Comparator.comparing(Evidence::id)).toList();
        if (eligible.stream().map(Evidence::id).distinct().count() != eligible.size()) throw new IllegalArgumentException("Duplicate evidence");
        for (var e : eligible) {
            var node = obj().put("id", e.id()).put("metric", e.metric().name()).put("team", e.team())
                    .put("season", e.season()).put("week", e.week()).put("origin", e.origin().name())
                    .put("value", decimal(e.value())).put("displayValue", display(e.value())).put("unit", "EPA_PER_PLAY");
            if (e.metric().hasTotalPlayDenominator() && e.volume() != null) node.put("plays", e.volume()); else node.putNull("plays");
            evidence.add(node);
        }
        var series = out.putArray("series");
        var windows = context.windows().stream().filter(w -> eligible.stream().anyMatch(e -> e.metric() == w.metric() && e.team().equals(w.team())))
                .sorted(Comparator.comparing(VisualAnalysisProjector::seriesId)).toList();
        var seriesIds = new HashSet<String>();
        for (var w : windows) {
            if (!seriesIds.add(seriesId(w))) throw new IllegalArgumentException("Duplicate series");
            series.add(obj().put("id", seriesId(w)).set("evidenceIds", array(w.evidenceIds())));
        }
        var matchupClaims = new HashMap<String, SignalClaimValidator.Resolved>();
        var windowClaims = new HashMap<String, SignalClaimValidator.Resolved>();
        for (var r : resolvedClaims.values()) {
            if (r.claim().type() == Kind.MATCHUP) matchupClaims.put(r.candidate().id(), r);
            if (r.claim().type() == Kind.WINDOW_LIMITATION) windowClaims.put(r.candidate().id(), r);
        }
        var encounters = out.putArray("encounters"); var findings = out.putArray("findings");
        var restrictions = out.putArray("restrictions");
        restrictions.add(restriction("r:temporal", null, "TEMPORAL_AVAILABILITY_UNKNOWN", List.of(), List.of()));
        restrictions.add(restriction("r:adjustment", null, "NO_OPPONENT_ADJUSTMENT", List.of(), List.of()));
        var globalIds = new ArrayList<>(List.of("r:temporal", "r:adjustment"));
        var globalClaim = resolvedClaims.values().stream().filter(r -> r.claim().type() == Kind.LIMITATION).findFirst().orElseThrow();
        String globalCode = restrictionCode(globalClaim.claim().predicate());
        restrictions.add(restriction("r:global", globalClaim.claim().id(), globalCode, List.of(),
                globalCode.equals("NO_DATA") ? List.of() : eligible.stream().map(Evidence::id).toList()));
        globalIds.add("r:global");
        for (String team : List.of(context.awayTeam(), context.homeTeam())) {
            for (var metric : List.of(MetricCatalog.OFF_EPA_PASS, MetricCatalog.OFF_EPA_RUSH, MetricCatalog.OFF_EPA_PLAY)) {
                var c = byId.get(team + ":" + metric);
                String id = team + ":" + foundation(metric);
                var node = obj().put("id", id).put("attackTeam", team).put("defenseTeam", c.defenseTeam())
                        .put("foundation", foundation(metric));
                if (c.attack() == null) node.putNull("attackSeriesId"); else node.put("attackSeriesId", seriesId(c.attack()));
                if (c.defense() == null) node.putNull("defenseSeriesId"); else node.put("defenseSeriesId", seriesId(c.defense()));
                var group = grouped.get(c.id());
                node.put("state", !c.pairable() ? "UNAVAILABLE" : group == null ? "COMPARABLE" : "REPRESENTED_BY");
                if (c.pairable()) node.putNull("unavailableReason");
                else node.put("unavailableReason", c.attack() == null && c.defense() == null ? "MISSING_BOTH"
                        : c.attack() == null ? "MISSING_ATTACK" : c.defense() == null ? "MISSING_DEFENSE" : "INCOMPATIBLE_ORIGIN");
                node.set("representedByFindingIds", array(group == null ? List.of() : group.representedBy().stream().map(x -> "f:" + byId.get(x).attackTeam() + ":" + foundation(byId.get(x).foundation())).toList()));
                encounters.add(node);
                if (!c.pairable() || group != null) continue;
                var claim = matchupClaims.get(c.id());
                if (claim == null || !claim.candidate().equals(c) || !claim.claim().signals().equals(c.signals()))
                    throw new IllegalArgumentException("Missing resolved matchup");
                String relation = c.signals().relation().name();
                var copy = COPY.path("relations").path(relation);
                if (!copy.isObject()) throw new IllegalArgumentException("Missing relation copy");
                String restrictionId = "r:" + id;
                var finding = obj().put("id", "f:" + id).put("claimId", claim.claim().id()).put("encounterId", id)
                        .put("relation", relation).put("attackPattern", c.signals().attack().pattern().name())
                        .put("defensePattern", c.signals().defense().pattern().name())
                        .put("title", copy.path("title").asText()).put("summary", copy.path("summary").asText())
                        .put("primaryRestrictionId", restrictionId);
                findings.add(finding);
                var windowClaim = windowClaims.get(c.id());
                String code = windowClaim == null ? secondaryCode(c) : restrictionCode(windowClaim.claim().predicate());
                restrictions.add(restriction(restrictionId, windowClaim == null ? null : windowClaim.claim().id(),
                        code, List.of(id), evidenceIds(c)));
                if (c.attack().volume() == null || c.defense().volume() == null)
                    restrictions.add(restriction("r:denominator:" + id, null, "UNAVAILABLE_DENOMINATORS", List.of(id), evidenceIds(c)));
                if (!c.attack().weeks().equals(c.defense().weeks()))
                    restrictions.add(restriction("r:uneven:" + id, null, "UNEVEN_WINDOWS", List.of(id), evidenceIds(c)));
            }
        }
        var links = out.putArray("links");
        for (var link : claims.links()) if (link.relation() != Relation.INTERNAL_LIMITATION) {
            if (!Set.of(Relation.ADDITIONAL_RESTRICTION, Relation.INDEPENDENT_OPPORTUNITY).contains(link.relation())
                    || resolved.relations.get(link.from()) != link.relation() || !resolvedClaims.containsKey(link.to()))
                throw new IllegalArgumentException("Invalid resolved relation");
            var from = resolvedClaims.get(link.from()).candidate(); var to = resolvedClaims.get(link.to()).candidate();
            links.add(obj().put("fromFindingId", "f:" + from.attackTeam() + ":" + foundation(from.foundation()))
                    .put("toFindingId", "f:" + to.attackTeam() + ":" + foundation(to.foundation()))
                    .put("relation", link.relation().name()));
        }
        var highlights = resolved.sections.get("fator_chave").stream().filter(r -> r.claim().type() == Kind.MATCHUP)
                .map(r -> "f:" + r.candidate().attackTeam() + ":" + foundation(r.candidate().foundation())).toList();
        var presentation = obj(); presentation.set("highlightFindingIds", array(highlights));
        var equivalent = presentation.putArray("equivalentHighlightGroups"); if (highlights.size() > 1) equivalent.add(array(highlights));
        presentation.set("globalRestrictionIds", array(globalIds)); presentation.put("chartPolicy", "SHARED_SYMMETRIC_ZERO_V1");
        out.set("presentation", presentation);
        if (links.size() > 12 || eligible.stream().anyMatch(e -> decimal(e.value()).length() > 400))
            throw new UnsupportedVisualContract("Visual v1 collection or decimal limit exceeded");
        return out;
    }
    /** Refuse any altered projection before a successful attempt can be persisted. */
    public static void verify(AnalysisContext context, EditorialParameters parameters,
                              ClaimValidator.ValidatedClaims validated, ClaimDocument claims,
                              LocalGenerationService.Identity identity, String declaredAsOfDate, JsonNode document) {
        if (!project(context, parameters, validated, claims, identity, declaredAsOfDate).equals(document))
            throw new IllegalArgumentException("Visual document does not reconcile with validated source");
    }
}
