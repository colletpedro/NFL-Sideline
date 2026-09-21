package com.nflsideline.coreapi.editorial.batch;

import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.editorial.AnalysisContext;
import com.nflsideline.coreapi.editorial.AnalysisContextBuilder;
import com.nflsideline.coreapi.editorial.ContextQuality;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.service.AnalysisService;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class EditorialBatchServiceTest {
    @Test
    void plansEverythingBeforeCallsAndHonorsGlobalCeilingInDryRun() {
        GameRepository games = mock(GameRepository.class);
        AnalysisCacheRepository caches = mock(AnalysisCacheRepository.class);
        AnalysisContextBuilder contexts = mock(AnalysisContextBuilder.class);
        AnalysisService analyses = mock(AnalysisService.class);
        List<Game> schedule = new ArrayList<>();
        for (int i = 0; i < 16; i++) schedule.add(game("w2-" + i, 2, "2026-09-15"));
        for (int i = 0; i < 16; i++) schedule.add(game("w3-" + i, 3, "2026-09-22"));
        schedule.add(game("w9", 9, "2026-11-03"));
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(schedule);
        when(contexts.build(any(), any())).thenReturn(new AnalysisContext("{}", ContextQuality.MINIMAL));
        when(analyses.promptHash(any(), any(), any(), any())).thenReturn("a".repeat(64));
        when(caches.findByGameIdAndAnalysisTypeAndPromptHash(any(), any(), any())).thenReturn(Optional.empty());
        var summary = new EditorialBatchService(games, caches, contexts, analyses).run(
                new EditorialBatchOptions(2026, LocalDate.parse("2026-09-15"), true, 20, "r1", List.of()));
        assertThat(summary.eligible().values()).containsExactlyInAnyOrder(16, 16);
        assertThat(summary.callsPlanned()).isEqualTo(20);
        assertThat(summary.callsRealized()).isZero();
        assertThat(summary.omittedByLimit()).isEqualTo(12);
        assertThat(summary.omissionReasons()).containsEntry("OUTSIDE_EDITORIAL_WINDOW", 1L);
        verify(analyses, never()).generatePrepared(any(), any(), any(), any(), any());
    }

    @Test
    void reportsSanitizedCategoryCountsAndContinuesWithoutRetry() {
        var games = mock(GameRepository.class);
        var caches = mock(AnalysisCacheRepository.class);
        var contexts = mock(AnalysisContextBuilder.class);
        var analyses = mock(AnalysisService.class);
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(List.of(game("g1", 2, "2026-09-15"), game("g2", 2, "2026-09-15")));
        when(contexts.build(any(), any())).thenReturn(new AnalysisContext("{}", ContextQuality.MINIMAL));
        when(analyses.promptHash(any(), any(), any(), any())).thenReturn("a".repeat(64));
        when(caches.findByGameIdAndAnalysisTypeAndPromptHash(any(), any(), any())).thenReturn(Optional.empty());
        when(analyses.generatePrepared(any(), any(), any(), any(), any()))
                .thenThrow(new com.nflsideline.coreapi.llm.GenerationFailure(com.nflsideline.coreapi.llm.GenerationFailure.Category.HTTP_429));
        var summary = new EditorialBatchService(games, caches, contexts, analyses).run(
                new EditorialBatchOptions(2026, LocalDate.parse("2026-09-15"), false, 2, "r1", List.of()));
        assertThat(summary.failureCategories()).containsEntry(com.nflsideline.coreapi.llm.GenerationFailure.Category.HTTP_429, 2);
        assertThat(summary.failures()).containsExactly("HTTP_429:g1", "HTTP_429:g2");
        verify(analyses, org.mockito.Mockito.times(2)).generatePrepared(any(), any(), any(), any(), any());
    }

    @Test
    void filtersPlanningToExplicitGameIds() {
        var games = mock(GameRepository.class);
        var caches = mock(AnalysisCacheRepository.class);
        var contexts = mock(AnalysisContextBuilder.class);
        var analyses = mock(AnalysisService.class);
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(List.of(
                game("g1", 2, "2026-09-15"), game("g2", 2, "2026-09-15"), game("g3", 3, "2026-09-22")));
        when(contexts.build(any(), any())).thenReturn(new AnalysisContext("{}", ContextQuality.MINIMAL));
        when(analyses.promptHash(any(), any(), any(), any())).thenReturn("a".repeat(64));
        when(caches.findByGameIdAndAnalysisTypeAndPromptHash(any(), any(), any())).thenReturn(Optional.empty());

        var summary = new EditorialBatchService(games, caches, contexts, analyses).run(
                new EditorialBatchOptions(2026, LocalDate.parse("2026-09-15"), false, 10, "r1", List.of("g3", "g1")));

        assertThat(summary.callsPlanned()).isEqualTo(2);
        assertThat(summary.callsRealized()).isEqualTo(2);
        assertThat(summary.eligible().values()).containsExactlyInAnyOrder(1, 1);
        verify(analyses, org.mockito.Mockito.times(2)).generatePrepared(any(), any(), any(), any(), any());
    }

    @Test
    void invalidOrIneligibleGameIdAbortsBeforeAnyGeneration() {
        for (String requested : List.of("missing", "outside")) {
            var games = mock(GameRepository.class);
            var caches = mock(AnalysisCacheRepository.class);
            var contexts = mock(AnalysisContextBuilder.class);
            var analyses = mock(AnalysisService.class);
            when(games.findAllBySeasonWithDetails(2026)).thenReturn(List.of(
                    game("eligible", 2, "2026-09-15"), game("next", 3, "2026-09-22"),
                    game("outside", 9, "2026-11-03")));

            org.assertj.core.api.Assertions.assertThatThrownBy(() ->
                    new EditorialBatchService(games, caches, contexts, analyses).run(
                            new EditorialBatchOptions(2026, LocalDate.parse("2026-09-15"), false,
                                    10, "r1", List.of(requested))))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("Requested game is not eligible");
            verify(contexts, never()).build(any(), any());
            verify(analyses, never()).generatePrepared(any(), any(), any(), any(), any());
        }
    }

    private Game game(String id, int week, String date) {
        return Game.builder().gameId(id).season(2026).gameType("REG").week(week)
                .gameday(LocalDate.parse(date)).build();
    }
}
