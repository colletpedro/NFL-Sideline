package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.Team;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.domain.TeamWeekMetricsId;
import com.nflsideline.coreapi.domain.MarketImplied;
import com.nflsideline.coreapi.repository.MarketImpliedRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AnalysisContextBuilderTest {
    @Test
    void qualityDependsOnTwoTeamMetricCoverageNotMarket() {
        TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
        MarketImpliedRepository markets = mock(MarketImpliedRepository.class);
        List<TeamWeekMetrics> home = List.of(metric(2026, 1, "HOME"), metric(2026, 2, "HOME"), metric(2026, 2, "HOME"));
        List<TeamWeekMetrics> away = List.of(metric(2026, 1, "AWAY"), metric(2026, 2, "AWAY"), metric(2026, 2, "AWAY"));
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "HOME")).thenReturn(home);
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "AWAY")).thenReturn(away);
        when(markets.findById("g")).thenReturn(Optional.empty());
        ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();
        assertThat(new AnalysisContextBuilder(metrics, markets, mapper).build(game(), LocalDate.parse("2026-09-15")).quality())
                .isEqualTo(ContextQuality.COMPLETE);

        TeamWeekMetricsRepository noMetrics = mock(TeamWeekMetricsRepository.class);
        MarketImpliedRepository noMarket = mock(MarketImpliedRepository.class);
        when(noMetrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(org.mockito.ArgumentMatchers.anyInt(),
                org.mockito.ArgumentMatchers.anyString())).thenReturn(List.of());
        when(noMarket.findById("g")).thenReturn(Optional.empty());
        assertThat(new AnalysisContextBuilder(noMetrics, noMarket, mapper).build(game(), LocalDate.parse("2026-09-15")).quality())
                .isEqualTo(ContextQuality.MINIMAL);

        TeamWeekMetricsRepository oneTeam = mock(TeamWeekMetricsRepository.class);
        when(oneTeam.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "HOME")).thenReturn(home);
        when(oneTeam.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "AWAY")).thenReturn(List.of());
        when(oneTeam.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2025, "AWAY")).thenReturn(List.of());
        assertThat(new AnalysisContextBuilder(oneTeam, noMarket, mapper)
                .build(game(), LocalDate.parse("2026-09-15")).quality()).isEqualTo(ContextQuality.PARTIAL);
    }

    @Test
    void exposesOnlyCoherentCompleteMarketAndWithholdsEveryPartialForm() throws Exception {
        TeamWeekMetricsRepository metrics = twoTeamMetrics();
        MarketImpliedRepository markets = mock(MarketImpliedRepository.class);
        MarketImplied complete = MarketImplied.builder().gameId("g")
                .homeImpliedRaw(new BigDecimal("0.58")).awayImpliedRaw(new BigDecimal("0.45"))
                .homeImpliedFair(new BigDecimal("0.56")).awayImpliedFair(new BigDecimal("0.44"))
                .vigPct(new BigDecimal("0.03")).build();
        when(markets.findById("g")).thenReturn(Optional.of(complete));
        Game fullGame = game();
        fullGame.setHomeMoneyline(-140);
        fullGame.setAwayMoneyline(120);
        var full = json(new AnalysisContextBuilder(metrics, markets, mapper())
                .build(fullGame, LocalDate.parse("2026-09-15")));
        assertThat(full.path("market_availability").asText()).isEqualTo("COMPLETE");
        assertThat(full.at("/market/home_implied_fair").decimalValue()).isEqualByComparingTo("0.56");
        assertThat(full.at("/odds/home_moneyline").asInt()).isEqualTo(-140);

        Game isolatedSpread = game();
        isolatedSpread.setSpreadLine(new BigDecimal("-2.5"));
        when(markets.findById("g")).thenReturn(Optional.empty());
        assertPartialAndWithheld(new AnalysisContextBuilder(metrics, markets, mapper())
                .build(isolatedSpread, LocalDate.parse("2026-09-15")));

        Game oneMoneyline = game();
        oneMoneyline.setHomeMoneyline(-140);
        assertPartialAndWithheld(new AnalysisContextBuilder(metrics, markets, mapper())
                .build(oneMoneyline, LocalDate.parse("2026-09-15")));

        Game incompleteImplied = game();
        incompleteImplied.setHomeMoneyline(-140);
        incompleteImplied.setAwayMoneyline(120);
        when(markets.findById("g")).thenReturn(Optional.of(MarketImplied.builder().gameId("g")
                .homeImpliedFair(new BigDecimal("0.56")).build()));
        assertPartialAndWithheld(new AnalysisContextBuilder(metrics, markets, mapper())
                .build(incompleteImplied, LocalDate.parse("2026-09-15")));
    }

    @Test
    void cutsCurrentMetricsBeforeGameAndLabelsHistoricalFallback() throws Exception {
        TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
        MarketImpliedRepository markets = mock(MarketImpliedRepository.class);
        when(markets.findById("g")).thenReturn(Optional.empty());
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "HOME"))
                .thenReturn(List.of(metric(2026, 1, "HOME"), metric(2026, 2, "HOME"), metric(2026, 3, "HOME")));
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "AWAY")).thenReturn(List.of());
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2025, "AWAY"))
                .thenReturn(List.of(metric(2025, 18, "AWAY")));
        AnalysisContext context = new AnalysisContextBuilder(metrics, markets,
                new ObjectMapper().findAndRegisterModules()).build(game(), LocalDate.parse("2026-09-15"));
        var json = new ObjectMapper().findAndRegisterModules().readTree(context.canonicalJson());
        assertThat(json.at("/home_team/recent_form_last_3_eligible_weeks")).hasSize(2);
        assertThat(json.at("/away_team/metrics_origin").asText()).isEqualTo("HISTORICAL_REFERENCE");
        assertThat(json.at("/away_team/historical_reference").asBoolean()).isTrue();
        assertThat(context.quality()).isEqualTo(ContextQuality.PARTIAL);
        assertThat(context.canonicalJson()).contains("MARKET_MISSING", "HISTORICAL_REFERENCE_NOT_CURRENT_FORM");
    }

    @Test
    void postseasonDoesNotPretendWeekNumbersProveChronology() {
        TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
        MarketImpliedRepository markets = mock(MarketImpliedRepository.class);
        when(markets.findById("g")).thenReturn(Optional.empty());
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2025, "HOME"))
                .thenReturn(List.of(metric(2025, 18, "HOME")));
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2025, "AWAY"))
                .thenReturn(List.of(metric(2025, 18, "AWAY")));
        Game postseason = game();
        postseason.setGameType("WC");
        postseason.setWeek(1);
        AnalysisContext context = new AnalysisContextBuilder(metrics, markets, mapper())
                .build(postseason, LocalDate.parse("2027-01-10"));
        assertThat(context.quality()).isEqualTo(ContextQuality.PARTIAL);
        assertThat(context.canonicalJson()).contains("POSTSEASON_METRIC_CUTOFF_UNVERIFIABLE")
                .doesNotContain("\"metrics_season\":2026");
    }

    private void assertPartialAndWithheld(AnalysisContext context) throws Exception {
        var value = json(context);
        assertThat(value.path("market_availability").asText()).isEqualTo("PARTIAL");
        assertThat(value.path("market").isEmpty()).isTrue();
        assertThat(value.path("odds").isEmpty()).isTrue();
        assertThat(context.canonicalJson()).contains("MARKET_PARTIAL_WITHHELD_FROM_PROMPT");
        assertThat(context.quality()).isEqualTo(ContextQuality.COMPLETE);
    }

    private com.fasterxml.jackson.databind.JsonNode json(AnalysisContext context) throws Exception {
        return mapper().readTree(context.canonicalJson());
    }

    private ObjectMapper mapper() {
        return new ObjectMapper().findAndRegisterModules();
    }

    private TeamWeekMetricsRepository twoTeamMetrics() {
        TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "HOME"))
                .thenReturn(List.of(metric(2026, 1, "HOME")));
        when(metrics.findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(2026, "AWAY"))
                .thenReturn(List.of(metric(2026, 1, "AWAY")));
        return metrics;
    }

    private Game game() {
        return Game.builder().gameId("g").season(2026).week(3).gameType("REG")
                .gameday(LocalDate.parse("2026-09-20"))
                .homeTeam(Team.builder().teamAbbr("HOME").build())
                .awayTeam(Team.builder().teamAbbr("AWAY").build()).build();
    }

    private TeamWeekMetrics metric(int season, int week, String team) {
        return TeamWeekMetrics.builder().id(TeamWeekMetricsId.builder().season(season).week(week).teamAbbr(team).build())
                .offEpaPlay(new BigDecimal("0.12")).build();
    }
}
