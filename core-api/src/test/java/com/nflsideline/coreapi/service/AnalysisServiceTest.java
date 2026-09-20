package com.nflsideline.coreapi.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.editorial.AnalysisContext;
import com.nflsideline.coreapi.editorial.AnalysisContextBuilder;
import com.nflsideline.coreapi.editorial.AnalysisDepth;
import com.nflsideline.coreapi.llm.GeminiGateway;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.service.dto.AnalysisRequest;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AnalysisServiceTest {
    private static final LocalDate AS_OF = LocalDate.parse("2026-09-15");
    private static final String VALID = "{\"fator_chave\":\"duelo central\",\"vantagem_tatica\":\"equilíbrio\","
            + "\"alerta_vermelho\":\"incerteza\",\"veredito\":\"jogo aberto\",\"metricas_citadas\":{}}";

    @Test
    void identicalExecutionCallsGeminiOnceAndRevisionCreatesImmutableVersion() {
        Fixture fixture = fixture(VALID);
        var first = fixture.service.generateMatchupAnalysis(request("r1"));
        var cached = fixture.service.generateMatchupAnalysis(request("r1"));
        fixture.service.generateMatchupAnalysis(request("r2"));
        assertThat(first.fromCache()).isFalse();
        assertThat(cached.fromCache()).isTrue();
        assertThat(fixture.calls).hasValue(2);
        assertThat(fixture.saved).hasSize(2);
    }

    @Test
    void hashChangesForEveryApprovedIdentityDimension() {
        Fixture fixture = fixture(VALID);
        String baseline = fixture.service.promptHash(AnalysisDepth.FULL, "{\"x\":1}", AS_OF, "r1");
        assertThat(fixture.service.promptHash(AnalysisDepth.BASIC, "{\"x\":1}", AS_OF, "r1")).isNotEqualTo(baseline);
        assertThat(fixture.service.promptHash(AnalysisDepth.FULL, "{\"x\":2}", AS_OF, "r1")).isNotEqualTo(baseline);
        assertThat(fixture.service.promptHash(AnalysisDepth.FULL, "{\"x\":1}", AS_OF.plusDays(1), "r1")).isNotEqualTo(baseline);
        assertThat(fixture.service.promptHash(AnalysisDepth.FULL, "{\"x\":1}", AS_OF, "r2")).isNotEqualTo(baseline);
        AnalysisService otherModel = new AnalysisService(fixture.games, fixture.caches, fixture.contexts,
                fixture.gateway, new ObjectMapper(), "other-model");
        assertThat(otherModel.promptHash(AnalysisDepth.FULL, "{\"x\":1}", AS_OF, "r1")).isNotEqualTo(baseline);
    }

    @Test
    void unknownTypeAndInvalidResponseNeverCreateUsableCache() {
        Fixture fixture = fixture("{\"fator_chave\":\"20 pontos\",\"vantagem_tatica\":\"x\","
                + "\"alerta_vermelho\":\"y\",\"veredito\":\"z\"}");
        assertThatThrownBy(() -> fixture.service.generateMatchupAnalysis(
                new AnalysisRequest("g", "matchup", AS_OF, "r1"))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> fixture.service.generateMatchupAnalysis(request("r1")))
                .isInstanceOf(IllegalStateException.class);
        verify(fixture.caches, never()).saveAndFlush(any());
    }

    @Test
    void timeoutOrClientFailureNeverCreatesUsableCache() {
        Fixture fixture = fixture((system, user) -> { throw new IllegalStateException("timed out"); });
        assertThatThrownBy(() -> fixture.service.generateMatchupAnalysis(request("r1")))
                .isInstanceOf(IllegalStateException.class);
        verify(fixture.caches, never()).saveAndFlush(any());
    }

    @Test
    void validStructuredResponseStoresOnlyFourPublicFields() throws Exception {
        Fixture f = fixture(VALID.replace("duelo central", "20 pontos na temporada anterior")
                .replace("\"metricas_citadas\":{}", "\"metricas_citadas\":{\"pontos\":20}"));
        var result = f.service.generateMatchupAnalysis(request("r1"));
        var json = new ObjectMapper().readTree(f.saved.values().iterator().next().getResponseText());
        assertThat(json.size()).isEqualTo(4);
        assertThat(json.has("metricas_citadas")).isFalse();
    }

    @Test
    void historicalYearsAreNotMetricsButUncitedMetricsAreRejected() {
        fixture(VALID.replace("duelo central", "Histórico de 1999, 2025 e 2100")).service.generateMatchupAnalysis(request("r1"));
        for (String output : java.util.List.of(
                VALID.replace("duelo central", "20 pontos"),
                VALID.replace("duelo central", "21 pontos").replace("\"metricas_citadas\":{}", "\"metricas_citadas\":{\"pontos\":21}"),
                VALID.replace("\"metricas_citadas\":{}", "\"metricas_citadas\":{\"pontos\":{\"valor\":20}}"))) {
            Fixture f = fixture(output);
            assertThatThrownBy(() -> f.service.generateMatchupAnalysis(request("r1"))).hasMessage("INVALID_NUMERIC_CITATIONS");
            assertThat(f.saved).isEmpty();
        }
    }

    @Test
    void allFourFieldsMustBeNonblankStringsAndCitationsObjectRequired() throws Exception {
        for (String key : java.util.List.of("fator_chave", "vantagem_tatica", "alerta_vermelho", "veredito")) {
            for (String value : java.util.List.of("missing", "blank", "number")) {
                var json = (com.fasterxml.jackson.databind.node.ObjectNode) new ObjectMapper().readTree(VALID);
                if (value.equals("missing")) json.remove(key);
                else if (value.equals("blank")) json.put(key, "  ");
                else json.put(key, 20);
                Fixture f = fixture(json.toString());
                assertThatThrownBy(() -> f.service.generateMatchupAnalysis(request("r1"))).hasMessage("MISSING_FIELDS");
                assertThat(f.saved).isEmpty();
            }
        }
        Fixture invalid = fixture("{secret");
        assertThatThrownBy(() -> invalid.service.generateMatchupAnalysis(request("r1"))).hasMessage("INVALID_JSON");
        Fixture empty = fixture(" ");
        assertThatThrownBy(() -> empty.service.generateMatchupAnalysis(request("r1"))).hasMessage("EMPTY_RESPONSE");
        Fixture missing = fixture(VALID.replace(",\"metricas_citadas\":{}", ""));
        assertThatThrownBy(() -> missing.service.generateMatchupAnalysis(request("r1"))).hasMessage("MISSING_FIELDS");
    }

    private AnalysisRequest request(String revision) {
        return new AnalysisRequest("g", "matchup_full_v0", AS_OF, revision);
    }

    private Fixture fixture(String output) {
        AtomicInteger calls = new AtomicInteger();
        return fixture((system, user) -> { calls.incrementAndGet(); return output; }, calls);
    }

    private Fixture fixture(GeminiGateway gateway) {
        return fixture(gateway, new AtomicInteger());
    }

    private Fixture fixture(GeminiGateway gateway, AtomicInteger calls) {
        GameRepository games = mock(GameRepository.class);
        AnalysisCacheRepository caches = mock(AnalysisCacheRepository.class);
        AnalysisContextBuilder contexts = mock(AnalysisContextBuilder.class);
        Game game = Game.builder().gameId("g").season(2026).week(2).gameType("REG")
                .gameday(AS_OF).build();
        when(games.findById("g")).thenReturn(Optional.of(game));
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(java.util.List.of(game));
        when(contexts.build(any(), any())).thenReturn(new AnalysisContext("{\"metric\":20}",
                com.nflsideline.coreapi.editorial.ContextQuality.PARTIAL));
        Map<String, AnalysisCache> saved = new HashMap<>();
        when(caches.findByGameIdAndAnalysisTypeAndPromptHash(any(), any(), any()))
                .thenAnswer(invocation -> Optional.ofNullable(saved.get(invocation.getArgument(2))));
        when(caches.saveAndFlush(any())).thenAnswer(invocation -> {
            AnalysisCache value = invocation.getArgument(0);
            saved.put(value.getPromptHash(), value);
            return value;
        });
        AnalysisService service = new AnalysisService(games, caches, contexts, gateway,
                new ObjectMapper().findAndRegisterModules(), "model-a");
        return new Fixture(service, games, caches, contexts, gateway, calls, saved);
    }

    private record Fixture(AnalysisService service, GameRepository games, AnalysisCacheRepository caches,
                           AnalysisContextBuilder contexts, GeminiGateway gateway, AtomicInteger calls,
                           Map<String, AnalysisCache> saved) { }
}
