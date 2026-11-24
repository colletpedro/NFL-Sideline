package com.nflsideline.coreapi.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.editorial.AnalysisContext;
import com.nflsideline.coreapi.editorial.AnalysisContextBuilder;
import com.nflsideline.coreapi.editorial.AnalysisDepth;
import com.nflsideline.coreapi.editorial.ContextQuality;
import com.nflsideline.coreapi.llm.GeminiGateway;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.service.dto.AnalysisRequest;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class AnalysisServiceTest {
    private static final LocalDate DATE = LocalDate.parse("2026-09-15");
    private static final String VALID = """
            {"contract_version":3,"thesis_team":"NONE","verdict":"INCONCLUSIVE","claims":[
            {"claim_id":"k","type":"LIMITATION","subject":"MATCHUP","predicate":"NO_DATA","period":"NONE","evidence_ids":[],"role":"LIMITATION"},
            {"claim_id":"a","type":"LIMITATION","subject":"MATCHUP","predicate":"NO_MATCHUP_SUPPORT","period":"NONE","evidence_ids":[],"role":"LIMITATION"},
            {"claim_id":"r","type":"LIMITATION","subject":"MATCHUP","predicate":"NO_DATA","period":"NONE","evidence_ids":[],"role":"LIMITATION"},
            {"claim_id":"v","type":"LIMITATION","subject":"MATCHUP","predicate":"NO_DATA","period":"NONE","evidence_ids":[],"role":"LIMITATION"}],
            "sections":{"fator_chave":["k"],"vantagem_tatica":["a"],"alerta_vermelho":["r"],"veredito":["v"]}}
            """;

    @Test void cacheIdentityIsVersionedAndRevisionCreatesNewRow() {
        Fixture f = fixture(VALID);
        var first = f.service.generateMatchupAnalysis(request("r1"));
        var repeat = f.service.generateMatchupAnalysis(request("r1"));
        f.service.generateMatchupAnalysis(request("r2"));
        assertThat(first.fromCache()).isFalse();
        assertThat(repeat.fromCache()).isTrue();
        assertThat(f.calls).hasValue(2);
        assertThat(f.saved).hasSize(2);
        String baseline = f.service.promptHash(AnalysisDepth.FULL, "{}", DATE, "r1");
        assertThat(f.service.promptHash(AnalysisDepth.BASIC, "{}", DATE, "r1")).isNotEqualTo(baseline);
        assertThat(f.service.promptHash(AnalysisDepth.FULL, "{}", DATE, "r2")).isNotEqualTo(baseline);
    }

    @Test void onlyFourRenderedFieldsArePersistedAndLegacyReadsRemainAvailable() throws Exception {
        Fixture f = fixture(VALID);
        f.service.generateMatchupAnalysis(request("r1"));
        var saved = f.saved.values().iterator().next();
        var json = new ObjectMapper().readTree(saved.getResponseText());
        assertThat(json.size()).isEqualTo(4);
        assertThat(json.path("veredito").asText()).contains("inconclusivo");
        AnalysisCache legacy = AnalysisCache.builder().gameId("g").responseText("{\"fator_chave\":\"antigo\"}").build();
        when(f.caches.findFirstByGameIdAndAnalysisTypeInOrderByCreatedAtDescIdDesc(eq("g"), any()))
                .thenReturn(Optional.of(legacy));
        assertThat(f.service.findLatestCachedMatchup("g").orElseThrow().markdownText()).contains("antigo");
    }

    @Test void invalidReferenceCannotCreateCache() {
        Fixture f = fixture(VALID.replace("\"fator_chave\":[\"k\"]", "\"fator_chave\":[\"missing\"]"));
        assertThatThrownBy(() -> f.service.generateMatchupAnalysis(request("r1"))).hasMessage("INVALID_REFERENCE");
        assertThat(f.saved).isEmpty();
        verify(f.caches, never()).saveAndFlush(any());
    }

    @Test void malformedOrFailedGenerationCannotCreateCache() {
        Fixture malformed = fixture("{oops");
        assertThatThrownBy(() -> malformed.service.generateMatchupAnalysis(request("r1"))).hasMessage("INVALID_JSON");
        assertThat(malformed.saved).isEmpty();
        Fixture failed = fixture((system, prompt) -> { throw new IllegalStateException("timeout"); });
        assertThatThrownBy(() -> failed.service.generateMatchupAnalysis(request("r1"))).isInstanceOf(IllegalStateException.class);
        assertThat(failed.saved).isEmpty();
    }

    @Test void geminiDoesNotAdoptLocalContractImplicitly() {
        Fixture f = fixture(VALID.replace("\"contract_version\":3", "\"contract_version\":5"));
        assertThatThrownBy(() -> f.service.generateMatchupAnalysis(request("local-contract")))
                .hasMessage("INCOMPATIBLE_PREDICATE");
        assertThat(f.saved).isEmpty();
    }

    private AnalysisRequest request(String revision) { return new AnalysisRequest("g", "matchup_full_v0", DATE, revision); }
    private Fixture fixture(String response) {
        AtomicInteger calls = new AtomicInteger();
        return fixture((system, prompt) -> { calls.incrementAndGet(); return response; }, calls);
    }
    private Fixture fixture(GeminiGateway gateway) { return fixture(gateway, new AtomicInteger()); }
    private Fixture fixture(GeminiGateway gateway, AtomicInteger calls) {
        GameRepository games = mock(GameRepository.class);
        AnalysisCacheRepository caches = mock(AnalysisCacheRepository.class);
        AnalysisContextBuilder contexts = mock(AnalysisContextBuilder.class);
        Game game = Game.builder().gameId("g").season(2026).week(2).gameType("REG").gameday(DATE).build();
        when(games.findById("g")).thenReturn(Optional.of(game));
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(List.of(game));
        when(contexts.build(any(), any())).thenReturn(new AnalysisContext("{\"contract_version\":3}",
                ContextQuality.MINIMAL, List.of(), "HOME", "AWAY"));
        Map<String, AnalysisCache> saved = new HashMap<>();
        when(caches.findByGameIdAndAnalysisTypeAndPromptHash(any(), any(), any()))
                .thenAnswer(call -> Optional.ofNullable(saved.get(call.getArgument(2))));
        when(caches.saveAndFlush(any())).thenAnswer(call -> {
            AnalysisCache cache = call.getArgument(0); saved.put(cache.getPromptHash(), cache); return cache;
        });
        AnalysisService service = new AnalysisService(games, caches, contexts, gateway,
                new ObjectMapper().findAndRegisterModules(), "model-a");
        return new Fixture(service, caches, calls, saved);
    }
    private record Fixture(AnalysisService service, AnalysisCacheRepository caches, AtomicInteger calls,
                           Map<String, AnalysisCache> saved) { }
}
