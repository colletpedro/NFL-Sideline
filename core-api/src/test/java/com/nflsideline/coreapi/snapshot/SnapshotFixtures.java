package com.nflsideline.coreapi.snapshot;

import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.MarketImplied;
import com.nflsideline.coreapi.domain.Team;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.domain.TeamWeekMetricsId;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;

final class SnapshotFixtures {

    private SnapshotFixtures() {
    }

    static Team team(String abbreviation) {
        return Team.builder().teamAbbr(abbreviation).teamName("Team " + abbreviation)
                .conference("AFC").division("Test").logoUrl(null).build();
    }

    static Game game(String id, int week, String away, String home) {
        Game game = Game.builder().gameId(id).season(2026).week(week).gameType("REG")
                .gameday(LocalDate.of(2026, 9, 9 + week)).awayTeam(team(away)).homeTeam(team(home))
                .awayScore(17).homeScore(20).result(3)
                .spreadLine(new BigDecimal("-2.5")).totalLine(new BigDecimal("44.5"))
                .awayMoneyline(120).homeMoneyline(-140).homeSpreadOdds(-110).awaySpreadOdds(-110)
                .overOdds(-105).underOdds(-115).roof("outdoors").surface("grass").divGame(false)
                .updatedAt(OffsetDateTime.parse("2026-09-10T10:00:00Z")).build();
        MarketImplied market = MarketImplied.builder().gameId(id).game(game)
                .homeImpliedRaw(new BigDecimal("0.58")).awayImpliedRaw(new BigDecimal("0.45"))
                .homeImpliedFair(new BigDecimal("0.56")).awayImpliedFair(new BigDecimal("0.44"))
                .vigPct(new BigDecimal("0.03"))
                .computedAt(OffsetDateTime.parse("2026-09-10T10:00:00Z")).build();
        game.setMarketImplied(market);
        return game;
    }

    static TeamWeekMetrics metric(String team, int week) {
        return TeamWeekMetrics.builder()
                .id(TeamWeekMetricsId.builder().season(2026).week(week).teamAbbr(team).build())
                .offEpaPlay(new BigDecimal("0.10")).offEpaPass(new BigDecimal("0.20"))
                .offEpaRush(new BigDecimal("0.01")).defEpaPass(new BigDecimal("-0.02"))
                .defEpaRush(new BigDecimal("0.03")).dropbackRate(new BigDecimal("0.60"))
                .playsOffense(60).build();
    }

    static AnalysisCache analysis(long id, String gameId, String createdAt, String response) {
        return AnalysisCache.builder().id(id).gameId(gameId).analysisType("matchup_full_v0")
                .promptHash("internal").contextJson("{\"private\":true}").responseText(response)
                .modelName("cached-model").createdAt(OffsetDateTime.parse(createdAt)).build();
    }

    static String validAnalysis(String suffix) {
        return "{\"fator_chave\":\"factor " + suffix + "\","
                + "\"vantagem_tatica\":\"edge " + suffix + "\","
                + "\"alerta_vermelho\":\"alert " + suffix + "\","
                + "\"veredito\":\"verdict " + suffix + "\"}";
    }
}
