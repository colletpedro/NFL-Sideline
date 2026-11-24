package com.nflsideline.coreapi.editorial.local;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.*;
import com.nflsideline.coreapi.editorial.*;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.nio.file.*;
import java.util.*;
import static org.assertj.core.api.Assertions.*;
import static com.nflsideline.coreapi.editorial.MetricCatalog.*;
import static com.nflsideline.coreapi.editorial.SignalDimensions.Pattern.*;
import static com.nflsideline.coreapi.editorial.SignalDimensions.Relation.*;

class SignalEditorialTest {
    final LocalRuleSelector selector = new LocalRuleSelector();
    final ClaimRenderer renderer = new ClaimRenderer(FrozenContext.MAPPER);

    @Test void weeklyVariationIsAttributedToTheCorrectSideAndInternalLimitIsADistinctClaim() throws Exception {
        for (boolean both : List.of(false, true)) {
            var ctx = context(pair(OFF_EPA_PASS, new String[]{"-.1", ".4", ".2"},
                    both ? new String[]{".2", "-.3", "0"} : new String[]{".2", ".3", ".1"}));
            var selection = select(ctx); var c = selection.candidates().getFirst();
            assertThat(c.signals().attack().pattern()).isEqualTo(MIXED_SIGNS);
            assertThat(c.signals().defense().pattern()).isEqualTo(both ? MIXED_SIGNS : ALL_POSITIVE);
            assertThat(c.signals().relation()).isEqualTo(WEEKLY_SIGN_VARIATION);
            assertThat(c.signals().defense().containsZero()).isEqualTo(both);
            var output = render(ctx);
            assertThat(output.path("vantagem_tatica").asText()).contains("faixa semanal", "semanas positivas e negativas");
            String alert = output.path("alerta_vermelho").asText();
            assertThat(alert).contains("ataque de AAA", "não descrevem um sinal presente em todas").doesNotContain("Contraponto direto");
            if (both) assertThat(alert).contains("defesa de BBB"); else assertThat(alert).doesNotContain("defesa de BBB");
            assertThat(selection.document().links()).allMatch(l -> !l.from().equals(l.to()));
            assertThat(selection.document().links()).anyMatch(l -> l.relation() == ClaimSelection.Relation.INTERNAL_LIMITATION);
            var internal = selection.document().claims().stream().filter(x -> x.type() == ClaimSelection.Kind.WINDOW_LIMITATION).findFirst().orElseThrow();
            assertThat(internal.evidenceIds()).containsExactlyElementsOf(c.evidenceIds());
        }
    }
    @Test void strictOppositionHasTwoDifferentInterpretationsAndNeitherPredictsExploitation() throws Exception {
        var favorable = context(pair(OFF_EPA_PASS, repeat(".2"), repeat("-.3")));
        assertThat(select(favorable).candidates().getFirst().signals().relation()).isEqualTo(FAVORABLE_ATTACK_AND_DEFENSE);
        assertThat(render(favorable).path("vantagem_tatica").asText()).contains("+0,200", "-0,300", "indicadores favoráveis a ambos", "sem estabelecer quem prevalecerá");
        var unshown = context(pair(OFF_EPA_PASS, repeat("-.2"), repeat(".3")));
        assertThat(select(unshown).candidates().getFirst().signals().relation()).isEqualTo(ATTACK_NOT_DEMONSTRATED);
        assertThat(render(unshown).path("vantagem_tatica").asText()).contains("não demonstrou produção positiva para sustentar exploração");
        var negatives = context(pair(OFF_EPA_PASS, repeat("-.2"), repeat("-.3")));
        assertThat(select(negatives).candidates().getFirst().signals().relation()).isEqualTo(BOTH_NEGATIVE);
        assertThat(render(negatives).path("vantagem_tatica").asText()).contains("ataque produziu EPA negativo", "defesa permitiu EPA negativo");
    }
    @Test void zerosAreExactAndTinySignsAreNeverPrintedAsSignedZero() throws Exception {
        var ctx = context(pair(OFF_EPA_PASS, new String[]{"0", ".2", ".1"}, repeat(".3")));
        assertThat(select(ctx).candidates().getFirst().signals().attack().pattern()).isEqualTo(NONNEGATIVE_WITH_ZERO);
        assertThat(opportunities(select(ctx))).isEmpty();
        assertThat(render(ctx).path("vantagem_tatica").asText()).contains("EPA zero");
        for (String value : List.of(".000000001", "-.000000001", "0")) {
            var tiny = context(pair(OFF_EPA_PASS, repeat(value), repeat(".3")));
            String text = render(tiny).path("vantagem_tatica").asText();
            assertThat(text).doesNotContain("+0,000 EPA", "-0,000 EPA");
            assertThat(text).contains(value.equals("0") ? "0,000 EPA" : value.startsWith("-") ? "-0,0005 < EPA < 0" : "0 < EPA < 0,0005");
            assertThat(opportunities(select(tiny)).size()).isEqualTo(value.startsWith(".") ? 1 : 0);
        }
        var varyingMagnitude = context(pair(OFF_EPA_PASS, new String[]{".1", ".4", ".2"}, repeat(".3")));
        assertThat(select(varyingMagnitude).candidates().getFirst().signals().attack().valuesVary()).isTrue();
        assertThat(select(varyingMagnitude).candidates().getFirst().signals().relation()).isEqualTo(POSITIVE_CONVERGENCE);
    }
    @Test void tinyRangeEndpointsKeepTheirSignAndEndpointAttributionWithoutChainedInequalities() throws Exception {
        String[][] cases = {
                {".00001", ".116", "0 < EPA < 0,0005", "+0,116 EPA"},
                {"-.116", "-.00001", "-0,116 EPA", "-0,0005 < EPA < 0"},
                {"-.00001", ".00001", "-0,0005 < EPA < 0", "0 < EPA < 0,0005"},
                {"0", ".00001", "0,000 EPA", "0 < EPA < 0,0005"},
                {"-.00001", "0", "-0,0005 < EPA < 0", "0,000 EPA"}
        };
        for (var values : cases) {
            var ctx = context(pair(OFF_EPA_PASS, new String[]{values[0], values[1], values[1]}, repeat(".3")));
            var selected = select(ctx);
            String text = render(ctx).path("vantagem_tatica").asText();
            assertThat(text).contains("AAA (ataque)", "mínimo (" + values[2] + "); máximo (" + values[3] + ")")
                    .doesNotContain("faixa semanal de 0 <", "faixa semanal de -0,0005 <", "+0,000 EPA", "-0,000 EPA");
            assertThat(select(ctx)).isEqualTo(selected);
        }
        var boundary = context(pair(OFF_EPA_PASS, new String[]{"-.0005", "0", ".0005"}, repeat(".3")));
        assertThat(render(boundary).path("vantagem_tatica").asText())
                .contains("faixa semanal de -0,001 EPA a +0,001 EPA").doesNotContain("mínimo (");
    }
    @Test void tiedFoundationsKeepAllFourMeansWeeksAndSharedUnweightedNotice() throws Exception {
        var data = new ArrayList<>(pair(OFF_EPA_PASS, repeat(".111"), repeat(".222")));
        data.addAll(reverse(pair(OFF_EPA_RUSH, repeat(".333"), repeat(".444"))));
        var ctx = context(data); var selected = select(ctx);
        assertThat(selected.document().sections().get("fator_chave")).containsExactlyInAnyOrder("AAA:OFF_EPA_PASS", "BBB:OFF_EPA_RUSH");
        String advantage = render(ctx).path("vantagem_tatica").asText();
        assertThat(advantage).contains("AAA", "BBB", "Passe", "Corrida", "+0,111", "+0,222", "+0,333", "+0,444", "semanas 1, 2, 3", "3 observações");
        assertThat(advantage.split("sem ponderação por jogadas", -1)).hasSize(2);
        String verdict = render(ctx).path("veredito").asText();
        assertThat(verdict).contains("passe do ataque de AAA contra a defesa de BBB, há uma oportunidade localizada", "corrida do ataque de BBB contra a defesa de AAA, há uma oportunidade localizada", "não estima o vencedor")
                .doesNotContain("equilibrado", "inconclusivo", "50/50", "estatisticamente indecidível");
    }
    @Test void redundantGeneralIsAuditedButNotRepeatedAndAContraryGeneralCannotDisappear() throws Exception {
        var data = new ArrayList<>(pair(OFF_EPA_PASS, repeat(".2"), repeat(".3")));
        data.addAll(pair(OFF_EPA_PLAY, repeat(".4"), repeat(".1")));
        var ctx = context(data); var selection = select(ctx);
        assertThat(selection.candidates()).hasSize(6);
        assertThat(selection.document().groupings()).anyMatch(g -> g.candidateId().equals("AAA:OFF_EPA_PLAY"));
        assertThat(render(ctx).path("veredito").asText()).doesNotContain("panorama");
        var contrary = new ArrayList<>(pair(OFF_EPA_PASS, repeat(".2"), repeat(".3")));
        contrary.addAll(pair(OFF_EPA_PLAY, repeat("-.4"), repeat(".1")));
        var other = context(contrary);
        assertThat(select(other).document().groupings()).isEmpty();
        assertThat(select(other).document().links()).anyMatch(l -> l.relation() == ClaimSelection.Relation.ADDITIONAL_RESTRICTION);
        assertThat(render(other).path("alerta_vermelho").asText()).contains("outro fundamento", "Panorama", "-0,400", "+0,100");
        assertThat(render(other).path("veredito").asText()).contains("panorama por jogada", "não mostrou EPA positivo");
        // Remove every reference to the distinct fact: integrity of remaining IDs is intact,
        // but the inventory and semantic omission checks must still reject its disappearance.
        ObjectNode omitted = document(other);
        removeClaim(omitted, "AAA:OFF_EPA_PLAY");
        assertThatThrownBy(() -> renderer.render(omitted, other)).hasMessage("INCOMPATIBLE_PREDICATE");
        ObjectNode fakeGroup = omitted.deepCopy();
        fakeGroup.putArray("groupings").addObject().put("candidateId", "AAA:OFF_EPA_PLAY")
                .put("reason", "GENERAL_SAME_SIGNAL_AND_COVERAGE").putArray("representedBy").add("AAA:OFF_EPA_PASS");
        assertThatThrownBy(() -> renderer.render(fakeGroup, other)).isInstanceOf(RuntimeException.class);
    }
    @Test void independentOpponentOpportunityStaysDistinctFromRestriction() throws Exception {
        var data = new ArrayList<>(pair(OFF_EPA_PASS, repeat(".2"), repeat(".3")));
        data.addAll(reverse(pair(OFF_EPA_PLAY, repeat(".4"), repeat(".1"))));
        var ctx = context(data);
        assertThat(select(ctx).document().links()).anyMatch(l -> l.relation() == ClaimSelection.Relation.INDEPENDENT_OPPORTUNITY);
        assertThat(render(ctx).path("alerta_vermelho").asText()).contains("oportunidade independente do adversário").doesNotContain("refutação");
        assertThat(render(ctx).path("veredito").asText()).contains("AAA", "BBB", "oportunidade localizada");
    }
    @Test void invalidSignalsSelfLinksWrongInternalRefsAndLegacyRelationsAreRejected() throws Exception {
        var ctx = context(pair(OFF_EPA_PASS, repeat(".2"), repeat("-.3")));
        var falseSignals = document(ctx);
        ((ObjectNode) falseSignals.path("claims").get(0).path("signals")).put("relation", "POSITIVE_CONVERGENCE");
        assertThatThrownBy(() -> renderer.render(falseSignals, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
        var self = document(ctx); var link = (ObjectNode) self.path("links").get(0); link.put("from", link.path("to").asText());
        assertThatThrownBy(() -> renderer.render(self, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
        var legacy = document(ctx); ((ObjectNode) legacy.path("links").get(0)).put("relation", "DIRECT_CONFLICT");
        assertThatThrownBy(() -> renderer.render(legacy, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
        var wrong = document(ctx);
        for (var claim : wrong.path("claims")) if (claim.path("type").asText().equals("WINDOW_LIMITATION"))
            ((ObjectNode) claim).put("predicate", "SIGN_VARIATION_LIMIT");
        assertThatThrownBy(() -> renderer.render(wrong, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
        var directional = document(ctx).put("thesis_team", "AAA").put("verdict", "SLIGHT_HOME");
        assertThatThrownBy(() -> renderer.render(directional, ctx)).hasMessage("INCOMPATIBLE_PREDICATE");
    }
    @Test void dimensionsSurviveIncompleteCoverageAndOldNumericWindowsAreNotChanged() throws Exception {
        var data = new ArrayList<>(pair(OFF_EPA_PASS, new String[]{"-.1", ".4", ".2"}, repeat(".2")));
        data.removeIf(e -> e.team().equals("BBB") && e.week() == 2);
        var ctx = context(data); var candidate = select(ctx).candidates().getFirst();
        assertThat(candidate.signals().attack().pattern()).isEqualTo(MIXED_SIGNS);
        assertThat(candidate.adequateCoverage()).isFalse();
        assertThat(candidate.limitations()).contains(MatchupAssessment.Limitation.DIFFERENT_WEEKS);
        assertThat(render(ctx).path("vantagem_tatica").asText()).contains("semanas 1, 2, 3", "semanas 1, 3", "sem ponderação");
        assertThat(render(ctx).path("alerta_vermelho").asText()).contains("semanas observadas diferentes");
        assertThat(candidate.attack()).isEqualTo(ctx.windows().stream().filter(w -> w.id().equals(candidate.attack().id())).findFirst().orElseThrow());
    }
    @Test void propertiesHoldForNewContractAcross180ContextsIncludingDataRemoval() throws Exception {
        Random random = new Random(3201);
        for (int i = 0; i < 180; i++) {
            var data = new ArrayList<Evidence>();
            for (String t : List.of("AAA", "BBB")) for (var metric : List.of(OFF_EPA_PASS, DEF_EPA_PASS, OFF_EPA_RUSH, DEF_EPA_RUSH, OFF_EPA_PLAY, DEF_EPA_PLAY))
                for (int week = 1; week <= 3; week++) if (random.nextInt(5) != 0)
                    data.add(ev(t, metric, week, List.of("-.2", "0", ".00001", ".3", "10").get(random.nextInt(5))));
            var ctx = context(data); var selected = select(ctx); var text = render(ctx);
            assertThat(selected.document().verdict()).isEqualTo("INCONCLUSIVE");
            assertThat(selected.document().thesisTeam()).isEqualTo("NONE");
            var shuffled = new ArrayList<>(data); Collections.shuffle(shuffled, random); shuffled.addAll(data);
            assertThat(select(context(shuffled))).isEqualTo(selected);
            assertThat(render(context(shuffled))).isEqualTo(text);
            ObjectNode root = (ObjectNode) FrozenContext.MAPPER.readTree(ctx.canonicalJson()); root.putObject("market").put("homeMoneyline", -9000);
            var market = new AnalysisContext(root.toString(), ctx.quality(), data, ctx.homeTeam(), ctx.awayTeam());
            assertThat(select(market)).isEqualTo(selected); assertThat(render(market)).isEqualTo(text);
            var homeSwap = new AnalysisContext(ctx.canonicalJson(), ctx.quality(), data, "BBB", "AAA");
            assertThat(select(homeSwap)).isEqualTo(selected); assertThat(render(homeSwap)).isEqualTo(text);
            var symmetric = select(context(reverse(data)));
            for (var c : selected.candidates()) {
                var mapped = symmetric.candidates().stream().filter(x -> x.id().equals(swap(c.id()))).findFirst().orElseThrow();
                assertThat(mapped.signals()).isEqualTo(c.signals()); assertThat(mapped.limitations()).isEqualTo(c.limitations());
            }
            var reduced = context(data.stream().filter(e -> random.nextBoolean()).toList()); render(reduced);
            assertThat(opportunities(select(reduced))).isSubsetOf(opportunities(selected));
            assertThat(selected.document().links()).noneMatch(l -> l.from().equals(l.to()));
        }
    }
    @Test void allSixV4DocumentsStillRenderByteForByteEquivalentJson() throws Exception {
        Path root = Path.of("..").toAbsolutePath().normalize();
        for (String dir : List.of("development-final", "holdout-v1")) {
            try (var paths = Files.list(root.resolve("editorial/local-rules-runs/" + dir))) {
                for (Path path : paths.filter(Files::isDirectory).toList()) {
                    var ctx = FrozenContext.read(FrozenContext.MAPPER.readTree(path.resolve("context.json").toFile()));
                    assertThat(renderer.render(FrozenContext.MAPPER.readTree(path.resolve("claims.json").toFile()), ctx))
                            .isEqualTo(FrozenContext.MAPPER.readTree(path.resolve("rendered.json").toFile()));
                }
            }
        }
    }
    @Test void verdictNamesBothSidesAndDoesNotInventATemporalTrajectory() throws Exception {
        for (boolean reverseSides : List.of(false, true)) {
            for (String[] a : List.of(repeat("-.2"), repeat(".2"), new String[]{"-.1", ".4", ".2"}, new String[]{"0", ".1", ".2"})) {
                for (String[] d : List.of(repeat("-.3"), repeat(".3"), new String[]{".1", "-.2", ".3"})) {
                    var data = pair(OFF_EPA_PASS, a, d);
                    var ctx = context(reverseSides ? reverse(data) : data);
                    var c = select(ctx).candidates().stream().filter(MatchupAssessment.Candidate::pairable).findFirst().orElseThrow();
                    String text = render(ctx).path("veredito").asText();
                    assertThat(text).contains("ataque de " + c.attackTeam() + " contra a defesa de " + c.defenseTeam())
                            .doesNotContain("mudança de sinal", "EPA permitido adversário", "instável", "inconsistente");
                    if (c.signals().relation() == BOTH_NEGATIVE)
                        assertThat(text).contains("ataque de " + c.attackTeam() + " apresentou EPA negativo",
                                "defesa de " + c.defenseTeam() + " permitiu EPA negativo");
                    if (c.signals().attack().pattern() == MIXED_SIGNS)
                        assertThat(text).contains("EPA do ataque de " + c.attackTeam() + ", há semanas com valores positivos e negativos");
                    if (c.signals().defense().pattern() == MIXED_SIGNS)
                        assertThat(text).contains("EPA permitido pela defesa de " + c.defenseTeam() + ", há semanas com valores positivos e negativos");
                    if (c.signals().attack().containsZero())
                        assertThat(text).contains("EPA do ataque de " + c.attackTeam() + ", há semanas com valores positivos e semanas com zero");
                }
            }
        }
    }
    private void removeClaim(ObjectNode doc, String id) {
        var claims = (ArrayNode) doc.path("claims");
        for (int i = claims.size() - 1; i >= 0; i--) if (claims.get(i).path("claim_id").asText().equals(id)) claims.remove(i);
        for (var section : doc.path("sections")) {
            var refs = (ArrayNode) section;
            for (int i = refs.size() - 1; i >= 0; i--) if (refs.get(i).asText().equals(id)) refs.remove(i);
        }
        var links = (ArrayNode) doc.path("links");
        for (int i = links.size() - 1; i >= 0; i--) if (links.get(i).path("from").asText().equals(id)
                || links.get(i).path("to").asText().equals(id)) links.remove(i);
    }
    private ClaimSelection select(AnalysisContext c) { return selector.select(c, FrozenContext.parameters(c)); }
    private ObjectNode document(AnalysisContext c) { return FrozenContext.MAPPER.valueToTree(select(c).document()); }
    private JsonNode render(AnalysisContext c) { return renderer.render(document(c), c); }
    private Set<String> opportunities(ClaimSelection s) { return s.candidates().stream().filter(c -> c.signals().relation() == POSITIVE_CONVERGENCE).map(MatchupAssessment.Candidate::id).collect(java.util.stream.Collectors.toSet()); }
    private AnalysisContext context(List<Evidence> data) {
        ObjectNode root = FrozenContext.MAPPER.createObjectNode().put("contract_version", 3).put("home_team", "AAA").put("away_team", "BBB");
        root.putObject("game").put("game_id", "synthetic").put("season", 2026).put("week", 4).put("phase", "REG");
        root.set("evidence", FrozenContext.MAPPER.valueToTree(data));
        return new AnalysisContext(root.toString(), ContextQuality.COMPLETE, data, "AAA", "BBB");
    }
    private List<Evidence> pair(MetricCatalog metric, String[] a, String[] d) {
        var data = new ArrayList<Evidence>();
        for (int i=0;i<a.length;i++) data.add(ev("AAA",metric,i+1,a[i]));
        for (int i=0;i<d.length;i++) data.add(ev("BBB",metric.defensiveCounterpart(),i+1,d[i])); return data;
    }
    private String[] repeat(String v) { return new String[]{v,v,v}; }
    private Evidence ev(String team, MetricCatalog m, int week, String v) { return Evidence.observed(team,m,2026,week,false,new BigDecimal(v),null); }
    private String swap(String s) { return s.replace("AAA","ZZZ").replace("BBB","AAA").replace("ZZZ","BBB"); }
    private List<Evidence> reverse(List<Evidence> data) { return data.stream().map(e -> Evidence.observed(swap(e.team()),e.metric(),e.season(),e.week(),false,e.value(),e.volume())).toList(); }
}
