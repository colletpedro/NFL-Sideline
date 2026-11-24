package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.editorial.local.*;
import org.junit.jupiter.api.Test;
import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;
import static org.assertj.core.api.Assertions.*;

class VisualAnalysisProjectorTest {
    private static final Path ROOT = Path.of("..").toAbsolutePath().normalize();
    private static final Path CONTEXTS = ROOT.resolve("editorial/evaluations/2026-09-26/contexts");
    private static AnalysisContext read(Path file) throws Exception {
        return FrozenContext.read(FrozenContext.MAPPER.readTree(file.toFile()));
    }
    private static JsonNode find(JsonNode array, String id) {
        for (var item : array) if (id.equals(item.path("id").asText())) return item;
        throw new AssertionError("Missing " + id);
    }
    @Test void everyKnownRealContextReconcilesToValidatedClaimsAndExactWeeklyRows() throws Exception {
        try (var resource = VisualAnalysisProjector.class.getResourceAsStream("/visual-analysis-v1-copy-catalog.json")) {
            assertThat(FrozenContext.MAPPER.readTree(resource)).isEqualTo(FrozenContext.MAPPER.readTree(
                    ROOT.resolve("contracts/visual-analysis/v1/copy-catalog.json").toFile()));
        }
        int count = 0;
        try (var files = Files.list(CONTEXTS)) {
            var contexts = new ArrayList<>(files.filter(p -> p.toString().endsWith(".json")).sorted().toList());
            contexts.add(ROOT.resolve("editorial/coverage-clarity-v1/batch-01/2025_08_CHI_BAL/context.json"));
            for (Path file : contexts) {
                count++;
                var context = read(file);
                String declaredDate = FrozenContext.MAPPER.readTree(file.toFile()).path("game").path("as_of_date_utc").asText();
                if (declaredDate.isBlank()) declaredDate = null;
                var result = new LocalGenerationService().generate(context, FrozenContext.parameters(context), new LocalRuleSelector(), declaredDate);
                JsonNode d = result.insights();
                String gameId = FrozenContext.MAPPER.readTree(context.canonicalJson()).path("game").path("game_id").asText();
                assertThat(d).isEqualTo(FrozenContext.MAPPER.readTree(ROOT.resolve(
                        "editorial/evaluations/2026-10-06-visual-e2/documents/" + gameId + ".json").toFile()));
                assertThat(d.path("source").path("kind").asText()).isEqualTo("VALIDATED_LOCAL_RESULT");
                assertThat(d.path("source").path("resultIdentity").asText()).isEqualTo(result.identity().hash());
                assertThat(d.path("source").path("contextSha256").asText()).isEqualTo(result.identity().contextSha256());
                var visualRows = context.evidence().stream().filter(e -> e.metric().name().matches("(OFF|DEF)_EPA_(PASS|RUSH|PLAY)")).toList();
                assertThat(d.path("evidence").size()).isEqualTo(visualRows.size());
                for (Evidence row : visualRows) {
                    JsonNode e = find(d.path("evidence"), row.id());
                    assertThat(e.path("metric").asText()).isEqualTo(row.metric().name());
                    assertThat(e.path("team").asText()).isEqualTo(row.team());
                    assertThat(e.path("season").asInt()).isEqualTo(row.season());
                    assertThat(e.path("week").asInt()).isEqualTo(row.week());
                    assertThat(e.path("origin").asText()).isEqualTo(row.origin().name());
                    assertThat(new java.math.BigDecimal(e.path("value").asText())).isEqualByComparingTo(row.value());
                    if (row.metric().hasTotalPlayDenominator() && row.volume() != null)
                        assertThat(e.path("plays").asInt()).isEqualTo(row.volume());
                    else assertThat(e.path("plays").isNull()).isTrue();
                }
                var windows = context.windows().stream().filter(w -> w.metric().name().matches("(OFF|DEF)_EPA_(PASS|RUSH|PLAY)"))
                        .collect(Collectors.toMap(EvidenceWindow::id, w -> w));
                for (var s : d.path("series")) {
                    var matches = windows.values().stream().filter(w -> s.path("evidenceIds").equals(FrozenContext.MAPPER.valueToTree(w.evidenceIds()))).toList();
                    assertThat(matches).hasSize(1);
                }
                var candidates = MatchupAssessment.enumerateV5(context, FrozenContext.parameters(context));
                var claims = result.selection().document().claims().stream().collect(Collectors.toMap(ClaimSelection.Claim::id, x -> x));
                assertThat(d.path("encounters").size()).isEqualTo(6);
                for (var f : d.path("findings")) {
                    var claim = claims.get(f.path("claimId").asText());
                    assertThat(claim).isNotNull();
                    assertThat(claim.type()).isEqualTo(ClaimSelection.Kind.MATCHUP);
                    var encounter = find(d.path("encounters"), f.path("encounterId").asText());
                    var candidate = candidates.stream().filter(c -> c.attackTeam().equals(encounter.path("attackTeam").asText())
                            && c.foundation().name().endsWith(encounter.path("foundation").asText().equals("GENERAL") ? "PLAY" : encounter.path("foundation").asText()))
                            .findFirst().orElseThrow();
                    assertThat(candidate.signals().relation().name()).isEqualTo(f.path("relation").asText());
                    assertThat(candidate.signals().attack().pattern().name()).isEqualTo(f.path("attackPattern").asText());
                    assertThat(candidate.signals().defense().pattern().name()).isEqualTo(f.path("defensePattern").asText());
                    assertThat(find(d.path("restrictions"), f.path("primaryRestrictionId").asText()).path("encounterIds").get(0).asText())
                            .isEqualTo(encounter.path("id").asText());
                }
                assertThat(d.path("scope").path("declaredAsOfDate").isNull() ? null : d.path("scope").path("declaredAsOfDate").asText())
                        .isEqualTo(declaredDate);
            }
        }
        assertThat(count).isEqualTo(17);
    }
    @Test void mutatedOutputOrClaimCannotPassTheValidationBoundary() throws Exception {
        var context = read(CONTEXTS.resolve("2026_03_BAL_DAL.json"));
        var p = FrozenContext.parameters(context);
        var result = new LocalGenerationService().generate(context, p, new LocalRuleSelector());
        var validated = new ClaimValidator().validate(FrozenContext.MAPPER.valueToTree(result.selection().document()), context);
        List<java.util.function.Consumer<ObjectNode>> changes = List.of(
                d -> ((ObjectNode)d.path("evidence").get(0)).put("value", "9"),
                d -> ((ObjectNode)d.path("evidence").get(0)).put("team", "OTHER"),
                d -> ((ObjectNode)d.path("evidence").get(0)).put("origin", "HISTORICAL_REFERENCE"),
                d -> ((ObjectNode)d.path("evidence").get(0)).put("week", 19),
                d -> ((ObjectNode)d.path("source")).put("resultIdentity", "0".repeat(64)),
                d -> ((ObjectNode)d.path("findings").get(0)).put("claimId", "missing"),
                d -> ((ObjectNode)d.path("findings").get(0)).put("relation", "ZERO_PROFILE"),
                d -> ((ObjectNode)d.path("restrictions").get(0)).put("code", "NO_DATA"),
                d -> ((ObjectNode)d.path("encounters").get(0)).put("state", "REPRESENTED_BY"),
                d -> ((ObjectNode)d.path("game")).put("gameId", "OTHER")
        );
        for (var change : changes) {
            ObjectNode mutated = result.insights().deepCopy(); change.accept(mutated);
            assertThatThrownBy(() -> VisualAnalysisProjector.verify(context, p, validated,
                    result.selection().document(), result.identity(), null, mutated)).isInstanceOf(IllegalArgumentException.class);
        }
        ObjectNode wrongRole = FrozenContext.MAPPER.valueToTree(result.selection().document());
        String role = wrongRole.path("claims").get(0).path("role").asText();
        ((ObjectNode)wrongRole.path("claims").get(0)).put("role", role.equals("OPPORTUNITY") ? "LIMITATION" : "OPPORTUNITY");
        assertThatThrownBy(() -> new ClaimValidator().validate(wrongRole, context)).isInstanceOf(RuntimeException.class);
        ObjectNode wrongPredicate = FrozenContext.MAPPER.valueToTree(result.selection().document());
        ((ObjectNode)wrongPredicate.path("claims").get(0)).put("predicate", "NO_DATA");
        assertThatThrownBy(() -> new ClaimValidator().validate(wrongPredicate, context)).isInstanceOf(RuntimeException.class);
    }
    @Test void duplicateSourceIdsAndCanonicalDriftAreRejected() throws Exception {
        var source = FrozenContext.MAPPER.readTree(CONTEXTS.resolve("2026_03_BAL_DAL.json").toFile());
        ((com.fasterxml.jackson.databind.node.ArrayNode)source.path("evidence")).add(source.path("evidence").get(0));
        assertThatThrownBy(() -> FrozenContext.read(source)).isInstanceOf(IllegalArgumentException.class);
        var original = read(CONTEXTS.resolve("2026_03_BAL_DAL.json"));
        var changed = new ArrayList<>(original.evidence());
        var first = changed.get(0);
        changed.set(0, new Evidence(first.id(), first.team(), first.metric(), first.season(), first.week(), first.origin(),
                first.value().add(java.math.BigDecimal.ONE), first.unit(), first.volume(), first.sourceTable(), first.sourceKey()));
        var drift = new AnalysisContext(original.canonicalJson(), original.quality(), changed, original.homeTeam(), original.awayTeam());
        assertThatThrownBy(() -> new LocalGenerationService().generate(drift, FrozenContext.parameters(drift), new LocalRuleSelector()))
                .isInstanceOf(IllegalArgumentException.class);
    }
    private static List<Evidence> rows(String team, MetricCatalog metric, int season, boolean historical,
                                       int[] weeks, String... values) {
        var result = new ArrayList<Evidence>();
        for (int i = 0; i < weeks.length; i++) result.add(Evidence.observed(team, metric, season, weeks[i], historical,
                new java.math.BigDecimal(values[i]), metric.hasTotalPlayDenominator() ? 10 : null));
        return result;
    }
    private static AnalysisContext synthetic(List<Evidence> rows) throws Exception {
        var root = FrozenContext.MAPPER.createObjectNode().put("contract_version", 3)
                .put("home_team", "AAA").put("away_team", "BBB");
        root.putObject("game").put("game_id", "synthetic").put("season", 2026).put("week", 4).put("phase", "REG");
        root.set("evidence", FrozenContext.MAPPER.valueToTree(rows));
        return FrozenContext.read(root);
    }
    private static JsonNode visual(AnalysisContext c) {
        return new LocalGenerationService().generate(c, FrozenContext.parameters(c), new LocalRuleSelector()).insights();
    }
    @Test void syntheticUnitCasesCoverAbsenceUnevenWeeksZeroTinySignsTieAndIndependentRelation() throws Exception {
        // These are unit cases, never API examples or editorial holdout.
        var missing = synthetic(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2026, false, new int[]{1}, "0.2"));
        assertThat(visual(missing).path("encounters").get(0).path("state").asText()).isEqualTo("UNAVAILABLE");
        assertThat(visual(synthetic(List.of())).path("restrictions").toString()).contains("NO_DATA");
        var uneven = new ArrayList<>(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2026, false, new int[]{1,2}, "0.1", "0.2"));
        uneven.addAll(rows("AAA", MetricCatalog.DEF_EPA_PASS, 2026, false, new int[]{1,3}, "0.2", "0.3"));
        JsonNode unevenDoc = visual(synthetic(uneven));
        assertThat(find(unevenDoc.path("encounters"), "BBB:PASS").path("state").asText()).isEqualTo("COMPARABLE");
        assertThat(unevenDoc.path("restrictions").toString()).contains("UNEVEN_WINDOWS");
        var tiny = new ArrayList<>(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2026, false, new int[]{1,2,3},
                "0", "0.000000001", "-0.000000001"));
        tiny.addAll(rows("AAA", MetricCatalog.DEF_EPA_PASS, 2026, false, new int[]{1,2,3}, "0.1", "0.2", "0.3"));
        JsonNode tinyDoc = visual(synthetic(tiny));
        assertThat(tinyDoc.path("evidence").toString()).contains("0,000", "0 < EPA < 0,0005", "-0,0005 < EPA < 0");
        var historical = new ArrayList<>(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2025, true,
                new int[]{1,2}, "0.1", "0.2"));
        historical.addAll(rows("AAA", MetricCatalog.DEF_EPA_PASS, 2025, true,
                new int[]{1,2}, "0.2", "0.3"));
        JsonNode historicalDoc = visual(synthetic(historical));
        assertThat(historicalDoc.path("restrictions").toString()).contains("HISTORICAL_ONLY");
        assertThat(historicalDoc.path("evidence").get(0).path("origin").asText()).isEqualTo("HISTORICAL_REFERENCE");
        var incompatible = new ArrayList<>(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2026, false,
                new int[]{1}, "0.1"));
        incompatible.addAll(rows("AAA", MetricCatalog.DEF_EPA_PASS, 2025, true,
                new int[]{1}, "0.2"));
        assertThat(find(visual(synthetic(incompatible)).path("encounters"), "BBB:PASS").path("unavailableReason").asText())
                .isEqualTo("INCOMPATIBLE_ORIGIN");
        var tie = new ArrayList<>(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2026, false, new int[]{1,2,3}, "0.1", "0.1", "0.1"));
        tie.addAll(rows("AAA", MetricCatalog.DEF_EPA_PASS, 2026, false, new int[]{1,2,3}, "0.2", "0.2", "0.2"));
        tie.addAll(rows("AAA", MetricCatalog.OFF_EPA_RUSH, 2026, false, new int[]{1,2,3}, "0.3", "0.3", "0.3"));
        tie.addAll(rows("BBB", MetricCatalog.DEF_EPA_RUSH, 2026, false, new int[]{1,2,3}, "0.4", "0.4", "0.4"));
        JsonNode tieDoc = visual(synthetic(tie));
        assertThat(tieDoc.path("presentation").path("highlightFindingIds").size()).isEqualTo(2);
        assertThat(tieDoc.path("presentation").path("equivalentHighlightGroups").get(0).size()).isEqualTo(2);
        var independent = new ArrayList<>(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2026, false, new int[]{1,2,3}, "0.1", "0.1", "0.1"));
        independent.addAll(rows("AAA", MetricCatalog.DEF_EPA_PASS, 2026, false, new int[]{1,2,3}, "0.2", "0.2", "0.2"));
        independent.addAll(rows("AAA", MetricCatalog.OFF_EPA_PLAY, 2026, false, new int[]{1,2,3}, "0.3", "0.3", "0.3"));
        independent.addAll(rows("BBB", MetricCatalog.DEF_EPA_PLAY, 2026, false, new int[]{1,2,3}, "0.4", "0.4", "0.4"));
        assertThat(visual(synthetic(independent)).path("links").toString()).contains("INDEPENDENT_OPPORTUNITY");
    }
    @Test void invalidReferencesAndFalseGroupingFailClaimsValidation() throws Exception {
        var source = synthetic(new ArrayList<>(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2026, false,
                new int[]{1,2,3}, "0.1", "0.1", "0.1")));
        var d = FrozenContext.MAPPER.valueToTree(new LocalRuleSelector().select(source, FrozenContext.parameters(source)).document());
        ((com.fasterxml.jackson.databind.node.ArrayNode)d.path("sections").path("fator_chave"))
                .add(d.path("sections").path("fator_chave").get(0));
        assertThatThrownBy(() -> new ClaimValidator().validate(d, source)).isInstanceOf(RuntimeException.class);
        var paired = new ArrayList<>(rows("BBB", MetricCatalog.OFF_EPA_PASS, 2026, false, new int[]{1,2,3}, "0.1", "0.1", "0.1"));
        paired.addAll(rows("AAA", MetricCatalog.DEF_EPA_PASS, 2026, false, new int[]{1,2,3}, "0.2", "0.2", "0.2"));
        paired.addAll(rows("BBB", MetricCatalog.OFF_EPA_PLAY, 2026, false, new int[]{1,2,3}, "0.1", "0.1", "0.1"));
        paired.addAll(rows("AAA", MetricCatalog.DEF_EPA_PLAY, 2026, false, new int[]{1,2,3}, "0.2", "0.2", "0.2"));
        var context = synthetic(paired);
        var good = new LocalRuleSelector().select(context, FrozenContext.parameters(context));
        ObjectNode dangling = FrozenContext.MAPPER.valueToTree(good.document());
        ((com.fasterxml.jackson.databind.node.ArrayNode)dangling.path("claims").get(0).path("evidence_ids")).add("dangling");
        assertThatThrownBy(() -> new ClaimValidator().validate(dangling, context)).isInstanceOf(RuntimeException.class);
        ObjectNode badGroup = FrozenContext.MAPPER.valueToTree(good.document());
        assertThat(badGroup.path("groupings").size()).isPositive();
        ((ObjectNode)badGroup.path("groupings").get(0)).put("candidateId", "AAA:OFF_EPA_RUSH");
        assertThatThrownBy(() -> new ClaimValidator().validate(badGroup, context)).isInstanceOf(RuntimeException.class);
    }
}
