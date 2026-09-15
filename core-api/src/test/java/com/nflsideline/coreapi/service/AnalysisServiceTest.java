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
