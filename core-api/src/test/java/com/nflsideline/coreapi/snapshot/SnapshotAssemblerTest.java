package com.nflsideline.coreapi.snapshot;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.time.OffsetDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class SnapshotAssemblerTest {

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final SnapshotAssembler assembler = new SnapshotAssembler(objectMapper);

    @Test
    void ordersGamesTeamsMetricsAndGroupsMetricsByTeam() {
        var result = assembler.assemble(2026, time(),
                List.of(SnapshotFixtures.game("game-b", 2, "CCC", "DDD"),
                        SnapshotFixtures.game("game-a", 1, "BBB", "AAA")),
                List.of(SnapshotFixtures.metric("BBB", 2), SnapshotFixtures.metric("AAA", 2),
                        SnapshotFixtures.metric("AAA", 1)), List.of());

        assertThat(result.snapshot().games()).extracting(SnapshotContract.GameDto::gameId)
                .containsExactly("game-a", "game-b");
        assertThat(result.snapshot().teams()).extracting(SnapshotContract.TeamDto::teamAbbr)
                .containsExactly("AAA", "BBB", "CCC", "DDD");
        assertThat(result.snapshot().metricsByTeam().keySet()).containsExactly("AAA", "BBB");
        assertThat(result.snapshot().metricsByTeam().get("AAA"))
                .extracting(SnapshotContract.MetricDto::week).containsExactly(1, 2);
        assertThat(result.missingAnalyses()).isEqualTo(2);
    }

    @Test
    void latestCacheWinsWithIdAsDeterministicTieBreaker() {
        String gameId = "game-a";
        var result = assembler.assemble(2026, time(),
                List.of(SnapshotFixtures.game(gameId, 1, "BBB", "AAA")), List.of(), List.of(
                        SnapshotFixtures.analysis(1, gameId, "2026-09-10T11:00:00Z", SnapshotFixtures.validAnalysis("old")),
                        SnapshotFixtures.analysis(2, gameId, "2026-09-10T12:00:00Z", SnapshotFixtures.validAnalysis("lower-id")),
                        SnapshotFixtures.analysis(3, gameId, "2026-09-10T12:00:00Z", SnapshotFixtures.validAnalysis("winner"))));

        assertThat(result.snapshot().analysesByGame().get(gameId).veredito()).isEqualTo("verdict winner");
        assertThat(result.validAnalyses()).isOne();
    }

    @Test
    void absentCacheDoesNotBlockAndInvalidLatestCacheIsRejectedWithoutFallback() throws Exception {
        String invalidGame = "game-invalid";
        String absentGame = "game-absent";
        var result = assembler.assemble(2026, time(), List.of(
                        SnapshotFixtures.game(invalidGame, 1, "BBB", "AAA"),
                        SnapshotFixtures.game(absentGame, 1, "DDD", "CCC")), List.of(), List.of(
                        SnapshotFixtures.analysis(1, invalidGame, "2026-09-10T11:00:00Z", SnapshotFixtures.validAnalysis("older")),
                        SnapshotFixtures.analysis(2, invalidGame, "2026-09-10T12:00:00Z", "{\"fator_chave\":\"\"}")));

        assertThat(result.snapshot().analysesByGame()).isEmpty();
        assertThat(result.rejectedAnalyses()).isOne();
        assertThat(result.missingAnalyses()).isOne();
        String json = objectMapper.writeValueAsString(result.snapshot());
        assertThat(json).doesNotContain("contextJson", "context_json", "promptHash", "prompt_hash", "modelName");
    }

    private OffsetDateTime time() {
        return OffsetDateTime.parse("2026-09-10T12:00:00Z");
    }

    @Test
    void publishesCalendarGameWithoutAnyOddsOrMarket() {
        var game = SnapshotFixtures.game("no-market", 8, "AAA", "BBB");
        game.setHomeMoneyline(null);
        game.setAwayMoneyline(null);
        game.setSpreadLine(null);
        game.setTotalLine(null);
        game.setMarketImplied(null);
        var snapshot = assembler.assemble(2026, time(), List.of(game), List.of(), List.of()).snapshot();
        assertThat(snapshot.games()).hasSize(1);
        var exported = snapshot.games().getFirst();
        assertThat(exported.gameId()).isEqualTo("no-market");
        assertThat(exported.week()).isEqualTo(8);
        assertThat(exported.market()).isNull();
        assertThat(exported.homeMoneyline()).isNull();
        assertThat(exported.awayMoneyline()).isNull();
        assertThat(exported.spreadLine()).isNull();
    }
}
