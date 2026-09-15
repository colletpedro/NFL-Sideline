package com.nflsideline.coreapi.editorial;

import com.nflsideline.coreapi.domain.Game;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class EditorialPlannerTest {
    private final EditorialRoundResolver resolver = new EditorialRoundResolver();
    private final EditorialPlanner planner = new EditorialPlanner(resolver);

    @Test
    void resolvesOpeningBoundariesGapsEndAndUtcClock() {
        List<Game> games = List.of(game("w1", "REG", 1, "2026-09-10"),
                game("w1-late", "REG", 1, "2026-09-14"), game("w2", "REG", 2, "2026-09-20"));
        assertThat(resolver.resolve(games, LocalDate.parse("2026-09-02")).offseason()).isTrue();
        assertThat(resolver.resolve(games, LocalDate.parse("2026-09-03")).current().orElseThrow().key().week()).isOne();
        assertThat(resolver.resolve(games, LocalDate.parse("2026-09-10")).current().orElseThrow().key().week()).isOne();
        assertThat(resolver.resolve(games, LocalDate.parse("2026-09-14")).current().orElseThrow().key().week()).isOne();
        assertThat(resolver.resolve(games, LocalDate.parse("2026-09-15")).current().orElseThrow().key().week()).isEqualTo(2);
        assertThat(resolver.resolve(games, LocalDate.parse("2026-09-21")).offseason()).isTrue();
        Clock utc = Clock.fixed(Instant.parse("2026-09-15T23:59:59Z"), ZoneOffset.UTC);
        assertThat(resolver.resolve(games, utc).current().orElseThrow().key().week()).isEqualTo(2);
    }

    @Test
    void latestStartingRoundWinsOverlapAndPostseasonUsesChronology() {
        List<Game> games = List.of(game("reg", "REG", 18, "2027-01-08"),
                game("delayed", "REG", 18, "2027-01-12"), game("wc", "WC", 1, "2027-01-11"),
                game("div", "DIV", 1, "2027-01-18"));
        assertThat(resolver.resolve(games, LocalDate.parse("2027-01-11")).current().orElseThrow().key().phase())
                .isEqualTo("WC");
        assertThat(resolver.rounds(games)).extracting(round -> round.key().phase())
                .containsExactly("REG", "WC", "DIV");
    }

    @Test
    void fixtureSeptemberFifteenthPlansSixteenFullSixteenBasicAndHidesWeekNine() {
        List<Game> games = new ArrayList<>();
        for (int i = 0; i < 16; i++) games.add(game("w2-" + i, "REG", 2, "2026-09-15"));
        for (int i = 0; i < 16; i++) games.add(game("w3-" + i, "REG", 3, "2026-09-22"));
        games.add(game("w9-anticipated", "REG", 9, "2026-11-03"));
        List<EditorialCandidate> plan = planner.plan(games, LocalDate.parse("2026-09-15"));
        assertThat(plan).filteredOn(item -> item.depth() == AnalysisDepth.FULL).hasSize(16);
        assertThat(plan).filteredOn(item -> item.depth() == AnalysisDepth.BASIC).hasSize(16);
        assertThat(plan).filteredOn(item -> item.game().getWeek() == 9)
                .allMatch(item -> item.eligibility() == Eligibility.INELIGIBLE);
    }

    @Test
    void omitsFinishedPastUndatedAndOffseasonGames() {
        Game scored = game("scored", "REG", 1, "2026-09-10");
        scored.setHomeScore(10); scored.setAwayScore(7); scored.setResult(3);
        Game past = game("past", "REG", 1, "2026-09-10");
        Game undated = game("undated", "REG", 2, null);
        List<EditorialCandidate> plan = planner.plan(List.of(scored, past, undated, game("future", "REG", 2, "2026-09-20")),
                LocalDate.parse("2026-09-15"));
        assertThat(plan).filteredOn(item -> item.reason() == EditorialReason.GAME_FINISHED).hasSize(1);
        assertThat(plan).filteredOn(item -> item.reason() == EditorialReason.PAST_WITHOUT_SCORE).hasSize(1);
        assertThat(plan).filteredOn(item -> item.reason() == EditorialReason.MISSING_GAMEDAY).hasSize(1);
    }

    private Game game(String id, String phase, int week, String date) {
        return Game.builder().gameId(id).season(2026).gameType(phase).week(week)
                .gameday(date == null ? null : LocalDate.parse(date)).build();
    }
}
