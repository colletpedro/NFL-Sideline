package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.*;

class ClaimWindowRendererTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private final ClaimRenderer renderer = new ClaimRenderer(mapper);

    @Test void unevenWeeksAllowAttackDefenseMatchupWithoutGeneralTeamSuperiority() {
        AnalysisContext context = context("0.1", "0.2");
        ObjectNode result = renderer.render(response(context, true), context);
        assertThat(result.path("vantagem_tatica").asText()).contains("semanas 1, 3", "semanas 2, 3",
                "média das médias semanais", "2 observações", "faixa", "oportunidade condicional para A");
        // A's own defense and B's offense are not prerequisites for a pass matchup.
        assertThat(context.evidence()).allMatch(e -> e.metric() == MetricCatalog.OFF_EPA_PASS && e.team().equals("A")
                || e.metric() == MetricCatalog.DEF_EPA_PASS && e.team().equals("B"));
        assertThat(result.path("alerta_vermelho").asText()).contains("semanas observadas diferentes");
    }

    @Test void negativeAttackOrOneNegativeWeekCannotBeHiddenByAnExtremePositiveMean() {
        for (String[] values : List.of(new String[]{"-0.2", "-0.1"}, new String[]{"-0.1", "1.06"},
                new String[]{"0", "0.5"})) {
            AnalysisContext context = context(values[0], values[1]);
            assertThatThrownBy(() -> renderer.render(response(context, true), context))
                    .hasMessage("INCOMPATIBLE_PREDICATE");
            var output = renderer.render(response(context, false), context);
            assertThat(output.path("veredito").asText()).contains("inconclusivo");
            assertThat(output.path("vantagem_tatica").asText()).contains("sem demonstrar capacidade de exploração");
        }
    }

    @Test void incompleteMetricCoverageIsVisibleAndCannotProduceDirectionalConvergence() {
        var items = new ArrayList<>(context("0.1", "0.2").evidence());
        items.add(ev("A", 2, MetricCatalog.OFF_EPA_PLAY, "0.1"));
        var context = ctx(items);
        assertThatThrownBy(() -> renderer.render(response(context, true), context)).hasMessage("INCOMPATIBLE_PREDICATE");
        assertThat(renderer.render(response(context, false), context).path("vantagem_tatica").asText())
                .contains("métrica ausente nas semanas [2]");
    }

    @Test void passAttackCannotBePairedWithRushDefenseOrASelectedSingleWeek() {
        var items = new ArrayList<>(context("0.1", "0.2").evidence());
        items.add(ev("B", 2, MetricCatalog.DEF_EPA_RUSH, "0.3"));
        items.add(ev("B", 3, MetricCatalog.DEF_EPA_RUSH, "0.3"));
        var context = ctx(items);
        var wrongChannel = response(context, true);
        refs(wrongChannel, 0).set(1, mapper.valueToTree(wid(context, "B", MetricCatalog.DEF_EPA_RUSH)));
        assertThatThrownBy(() -> renderer.render(wrongChannel, context)).hasMessage("INCOMPATIBLE_PREDICATE");
        var cherryPicked = response(context, true);
        refs(cherryPicked, 0).set(0, mapper.valueToTree(items.getFirst().id()));
        assertThatThrownBy(() -> renderer.render(cherryPicked, context)).hasMessage("INVALID_REFERENCE");
    }

    @Test void currentAndHistoricalWindowsCannotBeMixedOrUsedForCurrentConvergence() {
        var items = context("0.1", "0.2").evidence().stream().map(e -> Evidence.observed(e.team(), e.metric(),
                e.team().equals("A") ? 2026 : 2025, e.week(), e.team().equals("B"), e.value(), null)).toList();
        var mixed = ctx(items);
        assertThatThrownBy(() -> renderer.render(response(mixed, true), mixed)).hasMessage("INVALID_REFERENCE");
        var oldItems = context("0.1", "0.2").evidence().stream().map(e -> Evidence.observed(e.team(), e.metric(),
                2025, e.week(), true, e.value(), null)).toList();
        var old = ctx(oldItems);
        var historical = response(old, false);
        claim(historical, 0).put("period", "HISTORICAL");
        claim(historical, 1).put("predicate", "HISTORICAL_ONLY");
        claim(historical, 2).put("predicate", "HISTORICAL_ONLY");
        assertThat(renderer.render(historical, old).path("vantagem_tatica").asText()).contains("referência histórica");
    }

    @Test void completeWindowComparisonSupportsDifferentWeeksButRejectsFalseOrder() {
        var items = new ArrayList<>(context("0.1", "0.2").evidence());
        items.add(ev("B", 2, MetricCatalog.OFF_EPA_PASS, "-0.1"));
        items.add(ev("B", 3, MetricCatalog.OFF_EPA_PASS, "-0.2"));
        var context = ctx(items);
        var response = response(context, false);
        ObjectNode comparison = mapper.createObjectNode().put("claim_id", "comparison")
                .put("type", "WINDOW_COMPARISON").put("subject", "A").put("predicate", "GREATER_THAN")
                .put("period", "CURRENT").put("role", "SUPPORT");
        comparison.putArray("evidence_ids").add(wid(context, "A", MetricCatalog.OFF_EPA_PASS))
                .add(wid(context, "B", MetricCatalog.OFF_EPA_PASS));
        ((ArrayNode) response.path("claims")).add(comparison);
        ((ObjectNode) response.path("sections")).putArray("fator_chave").add("comparison");
        assertThat(renderer.render(response, context).path("fator_chave").asText())
                .contains("semanas 1, 3", "semanas 2, 3", "média de A é maior");
        comparison.put("predicate", "LESS_THAN");
        assertThatThrownBy(() -> renderer.render(response, context)).hasMessage("FALSE_COMPARISON");
    }

    @Test void noDataCannotProduceMatchupAndUnknownOrDuplicateWindowIdsAreRejected() {
        var context = context("0.1", "0.2");
        var response = response(context, true);
        refs(response, 0).set(1, mapper.valueToTree("rw:unknown"));
        assertThatThrownBy(() -> renderer.render(response, context)).hasMessage("INVALID_REFERENCE");
        refs(response, 0).set(1, refs(response, 0).get(0));
        assertThatThrownBy(() -> renderer.render(response, context)).hasMessage("INVALID_REFERENCE");
        assertThatThrownBy(() -> renderer.render(response(context, true), ctx(List.of()))).hasMessage("INVALID_REFERENCE");
    }

    @Test void differentAggregationMethodsCannotBeRankedAsEquivalentWindows() {
        var items = new ArrayList<>(context("0.1", "0.2").evidence());
        for (int week : List.of(1, 3)) items.add(Evidence.observed("A", MetricCatalog.OFF_EPA_PLAY,
                2026, week, false, new BigDecimal("0.4"), 50));
        for (int week : List.of(2, 3)) items.add(ev("B", week, MetricCatalog.OFF_EPA_PLAY, "0.1"));
        var context = ctx(items);
        var root = response(context, false);
        ObjectNode comparison = ((ArrayNode) root.path("claims")).addObject().put("claim_id", "comparison")
                .put("type", "WINDOW_COMPARISON").put("subject", "A").put("predicate", "GREATER_THAN")
                .put("period", "CURRENT").put("role", "SUPPORT");
        comparison.putArray("evidence_ids").add(wid(context, "A", MetricCatalog.OFF_EPA_PLAY))
                .add(wid(context, "B", MetricCatalog.OFF_EPA_PLAY));
        ((ObjectNode) root.path("sections")).putArray("fator_chave").add("comparison");
        assertThatThrownBy(() -> renderer.render(root, context)).hasMessage("INCOMPATIBLE_PREDICATE");
    }

    @Test void mixedSignalLimitationRequiresActualSignVariationAndCannotBeInvented() {
        var mixed = context("-0.1", "1.06");
        var root = response(mixed, false);
        claim(root, 1).put("predicate", "MIXED_SIGNALS");
        assertThat(renderer.render(root, mixed).path("alerta_vermelho").asText())
                .contains("EPA semanal positivo e negativo");
        var positive = context("0.1", "0.2");
        var invented = response(positive, false);
        claim(invented, 1).put("predicate", "MIXED_SIGNALS");
        assertThatThrownBy(() -> renderer.render(invented, positive)).hasMessage("INCOMPATIBLE_PREDICATE");
    }

    @Test void claimReuseAcrossSectionsIsAllowedButDuplicationWithinSectionIsNot() {
        var context = context("0.1", "0.2");
        var response = response(context, true);
        assertThat(renderer.render(response, context).size()).isEqualTo(4);
        ((ArrayNode) response.path("sections").path("vantagem_tatica")).add("matchup");
        assertThatThrownBy(() -> renderer.render(response, context)).hasMessage("INVALID_REFERENCE");
    }

    @Test void versionTwoCannotBeMistakenForNewGeneration() {
        var context = context("0.1", "0.2");
        var response = response(context, true).put("contract_version", 2);
        assertThatThrownBy(() -> renderer.render(response, context)).hasMessage("MISSING_FIELDS");
    }

    private ObjectNode response(AnalysisContext context, boolean directional) {
        ObjectNode root = mapper.createObjectNode().put("contract_version", 3)
                .put("thesis_team", directional ? "A" : "NONE")
                .put("verdict", directional ? "SLIGHT_HOME" : "INCONCLUSIVE");
        ArrayNode claims = root.putArray("claims");
        ObjectNode matchup = claims.addObject().put("claim_id", "matchup").put("type", "MATCHUP")
                .put("subject", "A").put("predicate", directional ? "POSITIVE_EPA_CONVERGENCE" : "ATTACK_DEFENSE_PROFILE")
                .put("period", "CURRENT").put("role", directional ? "SUPPORT" : "LIMITATION");
        matchup.putArray("evidence_ids").add(wid(context, "A", MetricCatalog.OFF_EPA_PASS))
                .add(wid(context, "B", MetricCatalog.DEF_EPA_PASS));
        for (String id : List.of("risk", "limit")) {
            claims.addObject().put("claim_id", id).put("type", "LIMITATION").put("subject", "MATCHUP")
                    .put("predicate", id.equals("risk") ? "UNEVEN_WINDOWS" : "SMALL_SAMPLE")
                    .put("period", "NONE").put("role", "LIMITATION").putArray("evidence_ids");
        }
        ObjectNode sections = root.putObject("sections");
        sections.putArray("fator_chave").add("matchup");
        sections.putArray("vantagem_tatica").add("matchup");
        sections.putArray("alerta_vermelho").add("risk");
        sections.putArray("veredito").add("limit");
        return root;
    }
    private AnalysisContext context(String first, String second) {
        return ctx(List.of(ev("A", 1, MetricCatalog.OFF_EPA_PASS, first), ev("A", 3, MetricCatalog.OFF_EPA_PASS, second),
                ev("B", 2, MetricCatalog.DEF_EPA_PASS, "0.2"), ev("B", 3, MetricCatalog.DEF_EPA_PASS, "0.3")));
    }
    private AnalysisContext ctx(List<Evidence> evidence) { return new AnalysisContext("{}", ContextQuality.COMPLETE, evidence, "A", "B"); }
    private Evidence ev(String team, int week, MetricCatalog metric, String value) {
        return Evidence.observed(team, metric, 2026, week, false, new BigDecimal(value), null);
    }
    private String wid(AnalysisContext context, String team, MetricCatalog metric) {
        return context.windows().stream().filter(w -> w.team().equals(team) && w.metric() == metric).findFirst().orElseThrow().id();
    }
    private ObjectNode claim(ObjectNode root, int i) { return (ObjectNode) root.path("claims").get(i); }
    private ArrayNode refs(ObjectNode root, int i) { return (ArrayNode) claim(root, i).path("evidence_ids"); }
}
