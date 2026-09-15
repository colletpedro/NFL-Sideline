package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class EditorialManifestTest {
    private static final String RESPONSE =
            "{\"fator_chave\":\"a\",\"vantagem_tatica\":\"b\",\"alerta_vermelho\":\"c\",\"veredito\":\"d\"}";
    @TempDir Path directory;

    @Test
    void rootManifestIsFailClosedButEmptySelectionsIsValid() throws Exception {
        var missing = new EditorialManifestLoader(mapper(), directory.resolve("missing.json")).load();
        assertThat(missing.validRoot()).isFalse();
        Files.writeString(directory.resolve("invalid.json"), "{\"version\":1}");
        assertThat(new EditorialManifestLoader(mapper(), directory.resolve("invalid.json")).load().validRoot()).isFalse();
        Files.writeString(directory.resolve("empty.json"), "{\"version\":1,\"selections\":[]}");
        assertThat(new EditorialManifestLoader(mapper(), directory.resolve("empty.json")).load().validRoot()).isTrue();
    }

    @Test
    void loaderKeepsValidApprovalWhenAnotherEntryIsInvalid() throws Exception {
        String hash = "a".repeat(64);
        Path file = directory.resolve("manifest.json");
        Files.writeString(file, "{\"version\":1,\"selections\":["
                + entry("g", 1, "FULL", hash, "b".repeat(64), "APPROVED", "2026-09-15T10:00:00Z") + ","
                + entry("g", 2, "FULL", hash, "bad", "APPROVED", "2026-09-15T11:00:00Z") + "]}");
        var loaded = new EditorialManifestLoader(mapper(), file).load();
        assertThat(loaded.validRoot()).isTrue();
        assertThat(loaded.selections()).hasSize(1);
        assertThat(loaded.problems()).containsExactly("invalid_selection");
    }

    @Test
    void rechecksExactDepthAtGenerationAndPublicationDates() {
        List<Game> schedule = schedule();
        AnalysisCache cache = cache(7, "g", "matchup_full_v0", "2026-09-15", null);
        var valid = approval(7, AnalysisDepth.FULL, "2026-09-15", "2026-09-15T10:00:00Z");
        assertThat(selector().select(schedule, date("2026-09-16"), List.of(valid), List.of(cache)).analyses())
                .containsExactly(cache);

        var generatedWhileBasic = approval(7, AnalysisDepth.FULL, "2026-09-08", "2026-09-15T10:00:00Z");
        cache.setContextJson("{\"game\":{\"as_of_date_utc\":\"2026-09-08\"}}");
        assertThat(selector().select(schedule, date("2026-09-16"),
                List.of(generatedWhileBasic), List.of(cache)).analyses()).isEmpty();

        var generatedOutside = approval(7, AnalysisDepth.FULL, "2026-08-01", "2026-09-15T10:00:00Z");
        cache.setContextJson("{\"game\":{\"as_of_date_utc\":\"2026-08-01\"}}");
        assertThat(selector().select(schedule, date("2026-09-16"),
                List.of(generatedOutside), List.of(cache)).analyses()).isEmpty();
    }

    @Test
    void rejectsRetroactiveReviewAfterGamedayButAcceptsReviewOnGameday() {
        List<Game> schedule = schedule();
        Game completed = schedule.stream().filter(game -> game.getGameId().equals("g")).findFirst().orElseThrow();
        completed.setHomeScore(24);
        completed.setAwayScore(17);
        completed.setResult(7);
        AnalysisCache cache = cache(7, "g", "matchup_full_v0", "2026-09-15", null);
        var late = approval(7, AnalysisDepth.FULL, "2026-09-15", "2026-09-21T00:00:00Z");
        assertThat(selector().select(schedule, date("2026-09-21"), List.of(late), List.of(cache)).analyses())
                .isEmpty();
        var onGameday = approval(7, AnalysisDepth.FULL, "2026-09-15", "2026-09-20T23:59:00Z");
        assertThat(selector().select(schedule, date("2026-09-21"),
                List.of(onGameday), List.of(cache)).analyses()).containsExactly(cache);
    }

    @Test
    void legacyRequiresExplicitPastExactPreviouslyPublishedVersionAndUnlistedStaysInvisible() {
        Game past = game("legacy", 1, "2026-09-14");
        Game current = game("current", 2, "2026-09-20");
        AnalysisCache legacy = cache(9, "legacy", "matchup", "ignored", "2026-09-14T12:00:00Z");
        var approval = new EditorialManifest.Selection("legacy", 9, AnalysisDepth.LEGACY_PUBLISHED,
                "a".repeat(64), sha(RESPONSE), "APPROVED", "editor",
                OffsetDateTime.parse("2026-09-22T10:00:00Z"), date("2026-09-01"));
        var previous = new ApprovedAnalysisSelector.PublishedAnalysis(
                OffsetDateTime.parse("2026-09-14T12:00:00Z"), "a", "b", "c", "d");
        assertThat(selector().select(List.of(past, current), date("2026-09-21"), List.of(approval),
                List.of(legacy), Map.of("legacy", previous)).analyses()).containsExactly(legacy);
        var changedPrevious = new ApprovedAnalysisSelector.PublishedAnalysis(
                OffsetDateTime.parse("2026-09-14T12:00:00Z"), "a", "b", "c", "changed");
        assertThat(selector().select(List.of(past, current), date("2026-09-21"), List.of(approval),
                List.of(legacy), Map.of("legacy", changedPrevious)).analyses()).isEmpty();

        for (Game notPast : List.of(current, game("future", 3, "2026-09-27"))) {
            legacy.setGameId(notPast.getGameId());
            var notPastApproval = new EditorialManifest.Selection(notPast.getGameId(), 9,
                    AnalysisDepth.LEGACY_PUBLISHED, "a".repeat(64), sha(RESPONSE), "APPROVED", "editor",
                    OffsetDateTime.parse("2026-09-22T10:00:00Z"), date("2026-09-01"));
            assertThat(selector().select(List.of(past, notPast), date("2026-09-15"),
                    List.of(notPastApproval), List.of(legacy), Map.of(notPast.getGameId(), previous)).analyses())
                    .isEmpty();
        }
        legacy.setGameId("legacy");
        assertThat(selector().select(List.of(past), date("2026-09-21"), List.of(), List.of(legacy),
                Map.of("legacy", previous)).analyses()).isEmpty();
    }

    @Test
    void invalidNewerApprovalCannotHideOlderValidApproval() {
        List<Game> schedule = schedule();
        AnalysisCache validCache = cache(7, "g", "matchup_full_v0", "2026-09-15", null);
        var older = approval(7, AnalysisDepth.FULL, "2026-09-15", "2026-09-15T10:00:00Z");
        var newerMissing = approval(8, AnalysisDepth.FULL, "2026-09-15", "2026-09-15T11:00:00Z");
        assertThat(selector().select(schedule, date("2026-09-16"), List.of(newerMissing, older),
                List.of(validCache)).analyses()).containsExactly(validCache);
    }

    private List<Game> schedule() {
        return List.of(game("w1", 1, "2026-09-14"), game("g", 2, "2026-09-20"), game("w3", 3, "2026-09-27"));
    }

    private Game game(String id, int week, String gameday) {
        return Game.builder().gameId(id).season(2026).gameType("REG").week(week)
                .gameday(date(gameday)).build();
    }

    private AnalysisCache cache(long id, String gameId, String type, String asOf, String createdAt) {
        return AnalysisCache.builder().id(id).gameId(gameId).analysisType(type).promptHash("a".repeat(64))
                .responseText(RESPONSE).contextJson("{\"game\":{\"as_of_date_utc\":\"" + asOf + "\"}}")
                .createdAt(createdAt == null ? null : OffsetDateTime.parse(createdAt)).build();
    }

    private EditorialManifest.Selection approval(long id, AnalysisDepth depth, String asOf, String reviewedAt) {
        return new EditorialManifest.Selection("g", id, depth, "a".repeat(64), sha(RESPONSE),
                "APPROVED", "editor", OffsetDateTime.parse(reviewedAt), date(asOf));
    }

    private String entry(String game, long id, String depth, String prompt, String response,
                         String status, String reviewedAt) {
        return "{\"gameId\":\"" + game + "\",\"analysisCacheId\":" + id + ",\"depth\":\"" + depth
                + "\",\"promptHash\":\"" + prompt + "\",\"responseHash\":\"" + response
                + "\",\"status\":\"" + status + "\",\"reviewedBy\":\"editor\",\"reviewedAt\":\""
                + reviewedAt + "\",\"asOfDate\":\"2026-09-15\"}";
    }

    private LocalDate date(String value) { return LocalDate.parse(value); }
    private ObjectMapper mapper() { return new ObjectMapper().findAndRegisterModules(); }
    private ApprovedAnalysisSelector selector() { return new ApprovedAnalysisSelector(); }
    private String sha(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(value.getBytes(StandardCharsets.UTF_8))); }
        catch (Exception failure) { throw new AssertionError(failure); }
    }
}
