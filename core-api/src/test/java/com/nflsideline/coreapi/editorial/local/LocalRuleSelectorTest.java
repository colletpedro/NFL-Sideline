package com.nflsideline.coreapi.editorial.local;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.editorial.*;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.util.*;
import static org.assertj.core.api.Assertions.*;
import static com.nflsideline.coreapi.editorial.MetricCatalog.*;
import static com.nflsideline.coreapi.editorial.local.MatchupAssessment.Classification.*;

class LocalRuleSelectorTest {
    private final LegacyLocalRuleSelector selector = new LegacyLocalRuleSelector();
    private final ClaimRenderer renderer = new ClaimRenderer(FrozenContext.MAPPER);
    private final EditorialParameters parameters = new EditorialParameters(2026, 4, "REG");

    @Test void emptyOneTeamHistoricalAndShortSlicesRemainDescriptive() throws Exception {
        for (var values : List.of(List.<Evidence>of(), series("AAA", OFF_EPA_PASS, ".1", ".2", ".3"),
                historical(pair(OFF_EPA_PASS, ".1", ".2", ".3")))) {
            var context = context(values);
            var selection = select(context);
            assertThat(selection.document().thesisTeam()).isEqualTo("NONE");
            assertThat(selection.document().verdict()).isEqualTo("INCONCLUSIVE");
            assertThat(opportunities(selection)).isEmpty();
            assertThat(render(context).path("veredito").asText()).contains("inconclusivo");
        }
        assertThat(render(context(List.of())).path("fator_chave").asText()).contains("Não há métricas");
        assertThat(render(context(series("AAA", OFF_EPA_PASS, ".1"))).path("alerta_vermelho").asText()).contains("um dos times");
        assertThat(render(context(historical(pair(OFF_EPA_PASS, ".1", ".2", ".3")))).toString()).contains("histórica");
        for (int weeks : List.of(1, 2)) {
            var ctx = context(pair(OFF_EPA_PASS, Collections.nCopies(weeks, ".1").toArray(String[]::new)), weeks + 1);
            assertThat(opportunities(select(ctx))).containsExactly("AAA:OFF_EPA_PASS");
            assertThat(render(ctx).path("veredito").asText()).contains("amostra curta");
        }
    }

    @Test void unequalMissingStaleOrIncompatibleWindowsNeverBecomeOpportunities() throws Exception {
        var base = pair(OFF_EPA_PASS, ".1", ".2", ".3");
        var uneven = new ArrayList<>(base); uneven.removeIf(e -> e.team().equals("BBB") && e.week() == 2);
        var partial = new ArrayList<>(uneven); partial.add(ev("BBB", OFF_EPA_RUSH, 2, ".1", null));
        var mixedOrigin = base.stream().map(e -> e.team().equals("BBB") ? old(e) : e).toList();
        for (var values : List.of(uneven, partial, mixedOrigin, pair(OFF_EPA_PASS, ".1", ".2"))) {
            var ctx = context(values);
            assertThat(opportunities(select(ctx))).isEmpty();
            render(ctx);
        }
        var c = select(context(partial)).candidates().stream().filter(x -> x.id().equals("AAA:OFF_EPA_PASS")).findFirst().orElseThrow();
        assertThat(c.limitations()).contains(MatchupAssessment.Limitation.MISSING_METRIC_WEEKS,
                MatchupAssessment.Limitation.DIFFERENT_WEEKS, MatchupAssessment.Limitation.IDENTIFIABLE_CALENDAR_GAPS);
        assertThat(render(context(uneven)).toString()).contains("lacunas", "semanas observadas diferentes");
    }

    @Test void unknownDenominatorsStayUnweightedAndDifferentAggregationsAreIncompatibleForOpportunity() throws Exception {
        var pass = context(pair(OFF_EPA_PASS, ".1", ".2", ".3"));
        assertThat(render(pass).path("vantagem_tatica").asText()).contains("sem ponderação por jogadas");
        var play = pair(OFF_EPA_PLAY, ".1", ".2", ".3").stream().map(e -> Evidence.observed(e.team(), e.metric(),
                e.season(), e.week(), false, e.value(), e.team().equals("AAA") ? 50 : null)).toList();
        assertThat(opportunities(select(context(play)))).isEmpty();
        assertThat(render(context(play)).path("vantagem_tatica").asText()).contains("métodos de agregação diferem");
    }

    @Test void zeroAndExtremeMeansCannotEraseWeeklyConflicts() throws Exception {
        for (String[] values : List.of(new String[]{"-.01", "10", ".1"}, new String[]{"0", ".1", ".2"},
                new String[]{"-.00001", ".00001", ".00001"})) {
            var ctx = context(pair(OFF_EPA_PASS, values));
            assertThat(opportunities(select(ctx))).isEmpty();
            var candidate = select(ctx).candidates().getFirst();
            assertThat(candidate.classification()).isEqualTo(values[0].equals("0") ? PROFILE : CONFLICTING);
            if (!values[0].equals("0")) assertThat(render(ctx).path("alerta_vermelho").asText()).contains("Contraponto direto", "sinais positivos e negativos");
        }
        var tiny = context(pair(OFF_EPA_PASS, ".00001", ".00002", ".00001"));
        assertThat(opportunities(select(tiny))).hasSize(1); // sign reference is exactly zero, no strength threshold.
        assertThat(render(tiny).path("veredito").asText()).contains("nenhum time é escolhido");
    }

    @Test void retainTiedSpecificAlternativesRegardlessOfMagnitudeAndBothTeamsInConclusion() throws Exception {
        var values = new ArrayList<>(pair(OFF_EPA_PASS, ".01", ".01", ".01"));
        values.addAll(reverse(pair(OFF_EPA_RUSH, "4", "4", "4")));
        values.addAll(pair(OFF_EPA_PLAY, "10", "10", "10"));
        var ctx = context(values);
        var selection = select(ctx);
        assertThat(selection.document().sections().get("fator_chave")).containsExactlyInAnyOrder("AAA:OFF_EPA_PASS", "BBB:OFF_EPA_RUSH");
        assertThat(selection.document().sections().get("veredito")).contains("AAA:OFF_EPA_PASS", "BBB:OFF_EPA_RUSH", "AAA:OFF_EPA_PLAY");
        assertThat(render(ctx).path("fator_chave").asText()).contains("múltiplos recortes");
        assertThat(render(ctx).path("veredito").asText()).contains("Passe de AAA", "Corrida de BBB", "não contam como votos");
    }

    @Test void independentOpponentOpportunityIsNotCalledDirectRefutation() throws Exception {
        var values = new ArrayList<>(pair(OFF_EPA_PASS, ".2", ".2", ".2"));
        values.addAll(reverse(pair(OFF_EPA_PLAY, ".1", ".1", ".1")));
        var ctx = context(values);
        assertThat(select(ctx).document().sections().get("fator_chave")).containsExactly("AAA:OFF_EPA_PASS");
        assertThat(render(ctx).path("alerta_vermelho").asText()).contains("Oportunidade independente", "não refutação direta");
        assertThat(render(ctx).path("veredito").asText()).contains("AAA", "BBB");
        ObjectNode bad = document(ctx);
        ((ObjectNode) bad.path("links").get(0)).put("relation", "DIRECT_CONFLICT");
        assertThatThrownBy(() -> renderer.render(bad, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
    }

    @Test void generalProfileIsUsedWhenSpecificCoverageIsIncomplete() throws Exception {
        var values = new ArrayList<>(pair(OFF_EPA_PASS, ".1", ".1"));
        values.addAll(pair(OFF_EPA_PLAY, "-.1", "-.1", "-.1"));
        var ctx = context(values);
        assertThat(select(ctx).document().sections().get("fator_chave")).containsExactly("AAA:OFF_EPA_PLAY");
        render(ctx);
    }

    @Test void permutationDuplicatesHomeAwayAndMarketAreSemanticallyIrrelevant() throws Exception {
        var values = new ArrayList<>(pair(OFF_EPA_PASS, ".1", ".2", ".3"));
        values.addAll(reverse(pair(OFF_EPA_RUSH, ".4", ".2", ".1")));
        var original = context(values);
        var shuffled = new ArrayList<>(values); Collections.shuffle(shuffled, new Random(32));
        var reordered = context(shuffled);
        assertThat(select(reordered)).isEqualTo(select(original));
        assertThat(render(reordered)).isEqualTo(render(original));
        shuffled.addAll(values);
        var duplicates = context(shuffled);
        assertThat(select(duplicates)).isEqualTo(select(original));
        assertThat(render(duplicates)).isEqualTo(render(original));
        var swappedHome = new AnalysisContext(original.canonicalJson(), original.quality(), values, "BBB", "AAA");
        assertThat(select(swappedHome)).isEqualTo(select(original));
        assertThat(render(swappedHome)).isEqualTo(render(original));
        ObjectNode root = (ObjectNode) FrozenContext.MAPPER.readTree(original.canonicalJson());
        root.putObject("market").put("favorite", "BBB").put("moneyline", -9000).put("secret", "DO_NOT_COPY");
        var market = new AnalysisContext(root.toString(), original.quality(), values, "AAA", "BBB");
        assertThat(select(market)).isEqualTo(select(original));
        assertThat(render(market)).isEqualTo(render(original));
        assertThat(FrozenContext.read(root).canonicalJson()).doesNotContain("market", "DO_NOT_COPY");
        var renamed = context(reverse(values));
        assertThat(opportunities(select(renamed))).containsExactlyInAnyOrder("BBB:OFF_EPA_PASS", "AAA:OFF_EPA_RUSH");
        assertThat(new HashSet<>(select(renamed).document().sections().get("fator_chave")))
                .isEqualTo(new HashSet<>(select(original).document().sections().get("fator_chave").stream().map(this::swap).toList()));
    }

    @Test void randomizedDeletionCannotCreateSupportAndAllGeneratedClaimsValidate() throws Exception {
        Random random = new Random(71);
        for (int attempt = 0; attempt < 180; attempt++) {
            var values = new ArrayList<Evidence>();
            for (String team : List.of("AAA", "BBB")) for (var metric : List.of(OFF_EPA_PASS, OFF_EPA_RUSH, OFF_EPA_PLAY,
                    DEF_EPA_PASS, DEF_EPA_RUSH, DEF_EPA_PLAY)) for (int week = 1; week <= 3; week++)
                if (random.nextInt(5) != 0) values.add(ev(team, metric, week,
                        List.of("-.1", "0", ".00001", ".2", "8").get(random.nextInt(5)), null));
            var ctx = context(values); var selection = select(ctx); render(ctx);
            assertThat(selection.document().thesisTeam()).isEqualTo("NONE");
            assertThat(selection.document().verdict()).isEqualTo("INCONCLUSIVE");
            var reduced = values.stream().filter(e -> random.nextBoolean()).toList();
            var after = context(reduced); render(after);
            assertThat(opportunities(select(after))).isSubsetOf(opportunities(selection));
            // Renaming maps every classification, not just whichever primary was displayed.
            var renamed = select(context(reverse(values)));
            for (var candidate : selection.candidates()) {
                var other = renamed.candidates().stream().filter(c -> c.id().equals(swap(candidate.id()))).findFirst().orElseThrow();
                assertThat(other.classification()).isEqualTo(candidate.classification());
                assertThat(other.limitations()).isEqualTo(candidate.limitations());
            }
        }
    }

    @Test void neutralContractCannotChooseWinnerOmitOpportunityOrBypassLegacyRoles() throws Exception {
        var ctx = context(pair(OFF_EPA_PASS, ".1", ".2", ".3"));
        ObjectNode directional = document(ctx); directional.put("verdict", "SLIGHT_HOME").put("thesis_team", "AAA");
        assertThatThrownBy(() -> renderer.render(directional, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
        ObjectNode omission = document(ctx);
        ((ObjectNode) omission.path("sections")).putArray("veredito").add("limitation");
        assertThatThrownBy(() -> renderer.render(omission, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
        ObjectNode legacy = document(ctx); legacy.put("contract_version", 3);
        assertThatThrownBy(() -> renderer.render(legacy, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
        var incomplete = new ArrayList<>(ctx.evidence()); incomplete.remove(0);
        assertThatThrownBy(() -> renderer.render(document(ctx), context(incomplete))).isInstanceOf(RuntimeException.class);
        ObjectNode badRef = document(ctx);
        ((ArrayNode) badRef.path("claims").get(0).path("evidence_ids")).set(0, FrozenContext.MAPPER.valueToTree("rw:fake"));
        assertThatThrownBy(() -> renderer.render(badRef, ctx)).hasMessage("INVALID_REFERENCE");
    }

    @Test void contextGuardRejectsExpansionFutureEvidenceAndConflictingDuplicates() throws Exception {
        assertThatThrownBy(() -> select(context(pair(OFF_EPA_PASS, ".1", ".2", ".3", ".4"))))
                .hasMessage("Invalid frozen evidence");
        var values = new ArrayList<>(pair(OFF_EPA_PASS, ".1", ".2", ".3"));
        values.add(ev("AAA", OFF_EPA_PASS, 1, "-.1", null));
        assertThatThrownBy(() -> select(context(values))).isInstanceOf(IllegalArgumentException.class);
    }

    private ClaimSelection select(AnalysisContext context) { return selector.select(context, FrozenContext.parameters(context)); }
    private Set<String> opportunities(ClaimSelection selection) {
        return selection.candidates().stream().filter(c -> c.classification() == OPPORTUNITY).map(MatchupAssessment.Candidate::id)
                .collect(java.util.stream.Collectors.toSet());
    }
    private ObjectNode document(AnalysisContext ctx) { return FrozenContext.MAPPER.valueToTree(select(ctx).document()); }
    private JsonNode render(AnalysisContext ctx) { return renderer.render(document(ctx), ctx); }
    private AnalysisContext context(List<Evidence> evidence) throws Exception { return context(evidence, parameters.gameWeek()); }
    private AnalysisContext context(List<Evidence> evidence, int week) throws Exception {
        ObjectNode root = FrozenContext.MAPPER.createObjectNode().put("contract_version", 3).put("home_team", "AAA")
                .put("away_team", "BBB").put("data_coverage", "COMPLETE");
        root.putObject("game").put("season", 2026).put("week", week).put("phase", "REG").put("game_id", "fixture");
        root.set("evidence", FrozenContext.MAPPER.valueToTree(evidence));
        return new AnalysisContext(root.toString(), ContextQuality.COMPLETE, evidence, "AAA", "BBB");
    }
    private List<Evidence> series(String team, MetricCatalog metric, String... values) {
        var result = new ArrayList<Evidence>();
        for (int i = 0; i < values.length; i++) result.add(ev(team, metric, i + 1, values[i], null));
        return result;
    }
    private List<Evidence> pair(MetricCatalog metric, String... values) {
        var result = new ArrayList<>(series("AAA", metric, values));
        result.addAll(series("BBB", metric.defensiveCounterpart(), values)); return result;
    }
    private Evidence ev(String team, MetricCatalog metric, int week, String value, Integer volume) {
        return Evidence.observed(team, metric, 2026, week, false, new BigDecimal(value), volume);
    }
    private String swap(String text) { return text.replace("AAA", "ZZZ").replace("BBB", "AAA").replace("ZZZ", "BBB"); }
    private List<Evidence> reverse(List<Evidence> values) {
        return values.stream().map(e -> Evidence.observed(swap(e.team()), e.metric(), e.season(), e.week(),
                e.origin() == Evidence.Origin.HISTORICAL_REFERENCE, e.value(), e.volume())).toList();
    }
    private Evidence old(Evidence e) { return Evidence.observed(e.team(), e.metric(), 2025, e.week(), true, e.value(), e.volume()); }
    private List<Evidence> historical(List<Evidence> values) { return values.stream().map(this::old).toList(); }
}
