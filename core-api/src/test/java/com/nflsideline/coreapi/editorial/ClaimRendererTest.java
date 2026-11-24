package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.*;

class ClaimRendererTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private final ClaimRenderer renderer = new ClaimRenderer(mapper);

    @Test void validBilateralCaseRendersOnlyControlledPortugueseTextAndUnits() throws Exception {
        var output = renderer.render(valid(), context());
        assertThat(output.size()).isEqualTo(4);
        assertThat(output.path("fator_chave").asText()).contains("+0,123 EPA", "semana 1");
        assertThat(output.path("vantagem_tatica").asText()).contains("+0,123 EPA", "+0,050 EPA", "oportunidade condicional");
        assertThat(output.path("alerta_vermelho").asText()).contains("B", "+0,200 EPA");
        assertThat(output.path("veredito").asText()).contains("leve inclinação descritiva", "duas semanas");
        assertThat(output.toString()).doesNotContain("contract_version", "evidence_ids", "moneyline");
    }

    @Test void rateAndHistoricalObservationKeepTheirOwnUnitAndPeriod() throws Exception {
        ObjectNode rate = valid();
        evidenceIds(rate, 0).set(0, mapper.valueToTree(id("A", MetricCatalog.DROPBACK_RATE)));
        assertThat(renderer.render(rate, context()).path("fator_chave").asText())
                .contains("frequência de dropback", "50,1%").doesNotContain("EPA");
        Evidence old = Evidence.observed("A", MetricCatalog.OFF_EPA_PLAY, 2025, 18, true,
                new BigDecimal("0.300"), null);
        ObjectNode historical = valid();
        evidenceIds(historical, 0).set(0, mapper.valueToTree(old.id()));
        claim(historical, 0).put("period", "HISTORICAL");
        List<Evidence> evidence = new java.util.ArrayList<>(context().evidence());
        evidence.add(old);
        assertThat(renderer.render(historical,
                new AnalysisContext("{}", ContextQuality.PARTIAL, evidence, "A", "B"))
                .path("fator_chave").asText()).contains("temporada anterior");
    }

    @Test void inconclusiveMayKeepObservedAdvantageButCannotDenyExistingSupport() throws Exception {
        ObjectNode inconclusive = valid();
        inconclusive.put("verdict", "INCONCLUSIVE");
        assertThat(renderer.render(inconclusive, context()).path("veredito").asText()).contains("inconclusivo");
        ObjectNode denial = valid();
        ObjectNode advantage = claim(denial, 1);
        advantage.put("type", "LIMITATION");
        advantage.put("subject", "MATCHUP");
        advantage.put("predicate", "NO_MATCHUP_SUPPORT");
        advantage.put("period", "NONE");
        advantage.put("role", "LIMITATION");
        advantage.set("evidence_ids", mapper.createArrayNode());
        denial.put("verdict", "INCONCLUSIVE");
        rejected(denial, context(), "INCOMPATIBLE_PREDICATE");
    }

    @Test void wrongTeamMetricPeriodOrMissingIdIsRejected() throws Exception {
        ObjectNode wrongTeam = valid();
        claim(wrongTeam, 0).put("subject", "B");
        rejected(wrongTeam, context(), "INCOMPATIBLE_PREDICATE");
        ObjectNode metric = valid();
        evidenceIds(metric, 1).set(1, mapper.valueToTree(wid("B", MetricCatalog.DEF_EPA_PASS)));
        rejected(metric, context(), "INVALID_REFERENCE");
        ObjectNode historical = valid();
        claim(historical, 0).put("period", "HISTORICAL");
        rejected(historical, context(), "INVALID_REFERENCE");
        ObjectNode missing = valid();
        evidenceIds(missing, 0).set(0, mapper.valueToTree("tw:missing"));
        rejected(missing, context(), "INVALID_REFERENCE");
    }

    @Test void falseComparisonDuplicateIdAndRemovedSoleSupportAreRejected() throws Exception {
        ObjectNode falseComparison = valid();
        claim(falseComparison, 2).put("predicate", "LESS_THAN");
        rejected(falseComparison, context(), "FALSE_COMPARISON");
        ObjectNode duplicateClaim = valid();
        claim(duplicateClaim, 1).put("claim_id", "k");
        rejected(duplicateClaim, context(), "INVALID_REFERENCE");
        ObjectNode duplicateEvidence = valid();
        evidenceIds(duplicateEvidence, 1).set(1, mapper.valueToTree(wid("A", MetricCatalog.OFF_EPA_PLAY)));
        rejected(duplicateEvidence, context(), "INVALID_REFERENCE");
        ObjectNode removed = valid();
        evidenceIds(removed, 0).remove(0);
        rejected(removed, context(), "INCOMPATIBLE_PREDICATE");
    }

    @Test void dropbackIsFrequencyAndDefenseWeaknessAloneCannotBeAdvantage() throws Exception {
        ObjectNode dropback = valid();
        evidenceIds(dropback, 1).set(0, mapper.valueToTree(wid("A", MetricCatalog.DROPBACK_RATE)));
        evidenceIds(dropback, 1).set(1, mapper.valueToTree(wid("B", MetricCatalog.DROPBACK_RATE)));
        rejected(dropback, context(), "INCOMPATIBLE_PREDICATE");
        ObjectNode onlyDefense = valid();
        evidenceIds(onlyDefense, 1).set(0, mapper.valueToTree(wid("A", MetricCatalog.DEF_EPA_PLAY)));
        evidenceIds(onlyDefense, 1).set(1, mapper.valueToTree(wid("B", MetricCatalog.DEF_EPA_PLAY)));
        claim(onlyDefense, 1).put("predicate", "LESS_THAN");
        rejected(onlyDefense, context(), "INCOMPATIBLE_PREDICATE");
    }

    @Test void favorableRedFlagAndHistoricalAsCurrentAreRejected() throws Exception {
        ObjectNode favorable = valid();
        claim(favorable, 2).put("subject", "A");
        rejected(favorable, context(), "INCOMPATIBLE_PREDICATE");
        Evidence historical = Evidence.observed("A", MetricCatalog.OFF_EPA_PLAY, 2025, 18, true,
                new BigDecimal("0.1234"), null);
        AnalysisContext mixed = new AnalysisContext("{}", ContextQuality.PARTIAL,
                List.of(historical), "A", "B");
        ObjectNode recent = valid();
        evidenceIds(recent, 0).set(0, mapper.valueToTree(historical.id()));
        rejected(recent, mixed, "INVALID_REFERENCE");
    }

    @Test void renamingTeamsPreservesComparisonAndImprovingOneValueKeepsLocalOrdering() throws Exception {
        ObjectNode base = valid();
        var original = renderer.render(base, context());
        ObjectNode renamed = base.deepCopy();
        renamed.put("thesis_team", "X");
        for (JsonNode claim : renamed.path("claims")) {
            if (claim.path("subject").asText().equals("A")) ((ObjectNode) claim).put("subject", "X");
            if (claim.path("subject").asText().equals("B")) ((ObjectNode) claim).put("subject", "Y");
            ArrayNode refs = (ArrayNode) claim.path("evidence_ids");
            for (int i = 0; i < refs.size(); i++) refs.set(i, mapper.valueToTree(refs.get(i).asText()
                    .replace(":A:", ":X:").replace(":B:", ":Y:")));
        }
        List<Evidence> renamedEvidence = context().evidence().stream().map(e -> Evidence.observed(
                e.team().equals("A") ? "X" : "Y", e.metric(), e.season(), e.week(), false, e.value(), e.volume())).toList();
        var changed = renderer.render(renamed, new AnalysisContext("{}", ContextQuality.COMPLETE, renamedEvidence, "X", "Y"));
        assertThat(changed.path("vantagem_tatica").asText().replace("X", "A").replace("Y", "B"))
                .isEqualTo(original.path("vantagem_tatica").asText());
        List<Evidence> improved = context().evidence().stream().map(e -> e.team().equals("A")
                && e.metric() == MetricCatalog.OFF_EPA_PLAY
                ? Evidence.observed("A", e.metric(), e.season(), e.week(), false, new BigDecimal("0.500"), e.volume()) : e).toList();
        assertThat(renderer.render(base, new AnalysisContext("{}", ContextQuality.COMPLETE, improved, "A", "B"))
                .path("vantagem_tatica").asText()).contains("+0,500 EPA");
    }

    private ObjectNode valid() throws Exception {
        String json = """
                {"contract_version":3,"thesis_team":"A","verdict":"SLIGHT_HOME","claims":[
                {"claim_id":"k","type":"OBSERVATION","subject":"A","predicate":"RECORDED","period":"CURRENT","evidence_ids":["%s"],"role":"SUPPORT"},
                {"claim_id":"o","type":"MATCHUP","subject":"A","predicate":"POSITIVE_EPA_CONVERGENCE","period":"CURRENT","evidence_ids":["%s","%s"],"role":"SUPPORT"},
                {"claim_id":"r","type":"COMPARISON","subject":"B","predicate":"GREATER_THAN","period":"CURRENT","evidence_ids":["%s","%s"],"role":"COUNTER","thesis_id":"k"},
                {"claim_id":"v","type":"LIMITATION","subject":"MATCHUP","predicate":"SMALL_SAMPLE","period":"NONE","evidence_ids":[],"role":"LIMITATION"}],
                "sections":{"fator_chave":["k"],"vantagem_tatica":["o"],"alerta_vermelho":["r"],"veredito":["v"]}}
                """.formatted(id("A", MetricCatalog.OFF_EPA_PLAY),
                wid("A", MetricCatalog.OFF_EPA_PLAY), wid("B", MetricCatalog.DEF_EPA_PLAY),
                id("B", MetricCatalog.OFF_EPA_PASS), id("A", MetricCatalog.OFF_EPA_PASS));
        return (ObjectNode) mapper.readTree(json);
    }
    private AnalysisContext context() {
        return new AnalysisContext("{}", ContextQuality.COMPLETE, List.of(
                ev("A", MetricCatalog.OFF_EPA_PLAY, "0.1234"), ev("B", MetricCatalog.OFF_EPA_PLAY, "0.010"),
                ev("A", MetricCatalog.DEF_EPA_PLAY, "-0.100"), ev("B", MetricCatalog.DEF_EPA_PLAY, "0.050"),
                ev("A", MetricCatalog.OFF_EPA_PASS, "0.010"), ev("B", MetricCatalog.OFF_EPA_PASS, "0.200"),
                ev("A", MetricCatalog.DROPBACK_RATE, "0.501"), ev("B", MetricCatalog.DROPBACK_RATE, "0.409")), "A", "B");
    }
    private Evidence ev(String team, MetricCatalog metric, String value) {
        return Evidence.observed(team, metric, 2026, 1, false, new BigDecimal(value), null);
    }
    private String id(String team, MetricCatalog metric) { return "tw:2026:1:" + team + ":" + metric.name(); }
    private String wid(String team, MetricCatalog metric) { return "rw:2026:" + team + ":" + metric.name() + ":CURRENT_SEASON_PRIOR_WEEKS:1"; }
    private ObjectNode claim(ObjectNode tree, int n) { return (ObjectNode) tree.path("claims").get(n); }
    private ArrayNode evidenceIds(ObjectNode tree, int n) { return (ArrayNode) claim(tree, n).path("evidence_ids"); }
    private void rejected(ObjectNode tree, AnalysisContext context, String code) {
        assertThatThrownBy(() -> renderer.render(tree, context)).hasMessage(code);
    }
}
