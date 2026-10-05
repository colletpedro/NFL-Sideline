package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.Team;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.domain.TeamWeekMetricsId;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

class AnalysisContextBuilderTest {
    private final ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();

    @Test void orderDuplicatesCutoffAndNullAreStable() {
        TeamWeekMetricsRepository repo = mock(TeamWeekMetricsRepository.class);
        TeamWeekMetrics one = metric(2026, 1, "HOME", "0.1234");
        TeamWeekMetrics two = metric(2026, 2, "HOME", "0.2345");
        TeamWeekMetrics future = metric(2026, 3, "HOME", "0.999");
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "HOME"))
                .thenReturn(List.of(two, future, one, two), List.of(one, two));
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "AWAY"))
                .thenReturn(List.of(), List.of());
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2025, "AWAY"))
                .thenReturn(List.of(), List.of());
        AnalysisContextBuilder builder = new AnalysisContextBuilder(repo, mapper);
        AnalysisContext first = builder.build(game(), LocalDate.parse("2026-09-15"));
        AnalysisContext second = builder.build(game(), LocalDate.parse("2026-09-15"));
        assertThat(first.canonicalJson()).isEqualTo(second.canonicalJson());
        assertThat(first.evidence()).hasSize(2);
        assertThat(first.evidence()).allMatch(e -> e.week() < 3 && e.volume() == 50);
        assertThat(first.quality()).isEqualTo(ContextQuality.PARTIAL);
        assertThat(first.canonicalJson()).doesNotContain("market", "odds", "0.999");
    }

    @Test void marketChangesCannotChangeContextOrHashInput() {
        TeamWeekMetricsRepository repo = mock(TeamWeekMetricsRepository.class);
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "HOME"))
                .thenReturn(List.of(metric(2026, 1, "HOME", "0.12")));
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "AWAY"))
                .thenReturn(List.of(metric(2026, 1, "AWAY", "0.11")));
        var builder = new AnalysisContextBuilder(repo, mapper);
        var game = game();
        String before = builder.build(game, LocalDate.parse("2026-09-15")).canonicalJson();
        game.setHomeMoneyline(-500);
        game.setSpreadLine(new BigDecimal("-9"));
        String after = builder.build(game, LocalDate.parse("2026-09-15")).canonicalJson();
        assertThat(after).isEqualTo(before);
        var service = new com.nflsideline.coreapi.service.AnalysisService(
                mock(com.nflsideline.coreapi.repository.GameRepository.class),
                mock(com.nflsideline.coreapi.repository.AnalysisCacheRepository.class), builder,
                mock(com.nflsideline.coreapi.llm.GeminiGateway.class), mapper, "model-a");
        assertThat(service.promptHash(AnalysisDepth.FULL, after, LocalDate.parse("2026-09-15"), "r1"))
                .isEqualTo(service.promptHash(AnalysisDepth.FULL, before, LocalDate.parse("2026-09-15"), "r1"));
    }

    @Test void historicalIsLabeledAndPostseasonDoesNotUseCurrentWeekAsChronology() {
        TeamWeekMetricsRepository repo = mock(TeamWeekMetricsRepository.class);
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2025, "HOME"))
                .thenReturn(List.of(metric(2025, 18, "HOME", "0.12")));
        Game game = game();
        game.setGameType("WC");
        var context = new AnalysisContextBuilder(repo, mapper).build(game, LocalDate.parse("2027-01-10"));
        assertThat(context.evidence()).allMatch(e -> e.origin() == Evidence.Origin.HISTORICAL_REFERENCE);
        assertThat(context.canonicalJson()).contains("POSTSEASON_METRIC_CUTOFF_UNVERIFIABLE");
    }

    @Test void recentWindowsUseLastThreeAvailableRowsPerTeamWithoutAligningOrFillingGaps() throws Exception {
        TeamWeekMetricsRepository repo = mock(TeamWeekMetricsRepository.class);
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "HOME"))
                .thenReturn(List.of(metric(2026, 1, "HOME", "0.9"), metric(2026, 2, "HOME", "0.1"),
                        metric(2026, 4, "HOME", "0.2"), metric(2026, 5, "HOME", "0.3"), metric(2026, 6, "HOME", "9")));
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "AWAY"))
                .thenReturn(List.of(metric(2026, 3, "AWAY", "-0.1"), metric(2026, 5, "AWAY", "0.1")));
        Game game = game();
        game.setWeek(6);
        var result = new AnalysisContextBuilder(repo, mapper).build(game, LocalDate.parse("2026-10-10"));
        assertThat(result.windows().stream().filter(w -> w.team().equals("HOME")).findFirst().orElseThrow().weeks())
                .containsExactly(2, 4, 5);
        assertThat(result.windows().stream().filter(w -> w.team().equals("AWAY")).findFirst().orElseThrow().weeks())
                .containsExactly(3, 5);
        assertThat(result.windows()).hasSize(2);
        var json = mapper.readTree(result.canonicalJson());
        assertThat(json.path("contract_version").asInt()).isEqualTo(3);
        assertThat(json.path("recent_windows").size()).isEqualTo(2);
        assertThat(result.evidence()).noneMatch(e -> e.week() == 1 || e.week() >= 6);
    }

    @Test void nullMetricDoesNotBecomeZeroOrCompleteCoverage() {
        TeamWeekMetricsRepository repo = mock(TeamWeekMetricsRepository.class);
        TeamWeekMetrics empty = TeamWeekMetrics.builder().id(TeamWeekMetricsId.builder()
                .season(2026).week(1).teamAbbr("HOME").build()).build();
        when(repo.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "HOME")).thenReturn(List.of(empty));
        var result = new AnalysisContextBuilder(repo, mapper).build(game(), LocalDate.parse("2026-09-15"));
        assertThat(result.evidence()).isEmpty();
        assertThat(result.quality()).isEqualTo(ContextQuality.MINIMAL);
        assertThat(result.canonicalJson()).doesNotContain("\"value\":0");
    }

    private Game game() {
        return Game.builder().gameId("g").season(2026).week(3).gameType("REG")
                .gameday(LocalDate.parse("2026-09-20"))
                .homeTeam(Team.builder().teamAbbr("HOME").build())
                .awayTeam(Team.builder().teamAbbr("AWAY").build()).build();
    }
    private TeamWeekMetrics metric(int season, int week, String team, String value) {
        return TeamWeekMetrics.builder().id(TeamWeekMetricsId.builder()
                .season(season).week(week).teamAbbr(team).build()).offEpaPlay(new BigDecimal(value))
                .playsOffense(50).build();
    }
}
