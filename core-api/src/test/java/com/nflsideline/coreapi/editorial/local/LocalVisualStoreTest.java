package com.nflsideline.coreapi.editorial.local;

import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.assertj.core.api.Assertions.*;

class LocalVisualStoreTest {
    @TempDir Path temp;
    private static final Path CONTEXT = Path.of("..").toAbsolutePath().normalize()
            .resolve("editorial/evaluations/2026-09-26/contexts/2026_03_BAL_DAL.json");
    private LocalContextCatalog.Entry entry() throws Exception {
        Path input = Files.createDirectory(temp.resolve("contexts"));
        Files.copy(CONTEXT, input.resolve("case.json"));
        return new LocalContextCatalog(input).get("2026_03_BAL_DAL");
    }
    @Test void v4VisualIdentityAndDocumentStayIdenticalAcrossAttemptsAndRestarts() throws Exception {
        var entry = entry(); Path dir = Files.createDirectory(temp.resolve("results"));
        LocalResultStore.Response first, second;
        try (var store = new LocalResultStore(dir)) {
            first = store.generate("2026_03_BAL_DAL", entry, new LocalRuleSelector());
            second = store.generate("2026_03_BAL_DAL", entry, new LocalRuleSelector());
            assertThat(first.attemptId()).isNotEqualTo(second.attemptId());
            assertThat(first.resultIdentity()).isEqualTo(second.resultIdentity());
            var a = store.getInsights(first.gameId(), first.attemptId());
            var b = store.getInsights(second.gameId(), second.attemptId());
            assertThat(a.document()).isEqualTo(b.document());
            assertThat(a.visualIdentity()).isEqualTo(b.visualIdentity());
            assertThat(a.visualIdentity()).isEqualTo(LocalGenerationService.sha256(Files.readAllBytes(dir.resolve(first.attemptId()).resolve("insights.json"))));
            assertThat(a.document().path("source").path("kind").asText()).isEqualTo("VALIDATED_LOCAL_RESULT");
            assertThat(a.document().path("game").path("gameId").asText()).isEqualTo(first.gameId());
            assertThat(a.mode()).isEqualTo(a.document().path("mode").asText());
            assertThat(a.publicationApproved()).isEqualTo(a.document().path("publicationApproved").asBoolean());
            assertThat(a.gameId()).isEqualTo(a.document().path("game").path("gameId").asText());
            assertThat(a.resultIdentity()).isEqualTo(a.document().path("source").path("resultIdentity").asText());
            assertThat(a.document().toString()).doesNotContain(first.attemptId());
            assertThat(store.get(first.gameId(), first.attemptId())).isEqualTo(first);
        }
        try (var restarted = new LocalResultStore(dir)) {
            assertThat(restarted.getInsights(first.gameId(), first.attemptId()).document())
                    .isEqualTo(restarted.getInsights(second.gameId(), second.attemptId()).document());
            assertThat(restarted.get(first.gameId(), first.attemptId())).isEqualTo(first);
        }
    }
    @Test void explicitV3ReaderLeavesLegacyBytesUntouchedAndVisualReturnsDocumentedError() throws Exception {
        var entry = entry(); Path dir = Files.createDirectory(temp.resolve("results"));
        LocalResultStore.Response response;
        try (var store = new LocalResultStore(dir)) {
            response = store.generate("2026_03_BAL_DAL", entry, new LocalRuleSelector());
        }
        Path attempt = dir.resolve(response.attemptId());
        Files.delete(attempt.resolve("insights.json"));
        ObjectNode result = (ObjectNode)FrozenContext.MAPPER.readTree(attempt.resolve("result.json").toFile());
        result.put("artifactVersion", 3).remove("visualIdentity");
        Files.writeString(attempt.resolve("result.json"), FrozenContext.MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(result) + "\n");
        ObjectNode marker = (ObjectNode)FrozenContext.MAPPER.readTree(attempt.resolve("complete.json").toFile());
        ObjectNode hashes = (ObjectNode)marker.path("hashes");
        hashes.remove("insights.json");
        hashes.put("result.json", LocalGenerationService.sha256(Files.readAllBytes(attempt.resolve("result.json"))));
        Files.writeString(attempt.resolve("complete.json"), FrozenContext.MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(marker) + "\n");
        var before = new HashMap<String, byte[]>();
        for (String name : List.of("context.json", "selection.json", "claims.json", "rendered.json", "result.json", "complete.json"))
            before.put(name, Files.readAllBytes(attempt.resolve(name)));
        try (var store = new LocalResultStore(dir)) {
            assertThat(store.get(response.gameId(), response.attemptId())).isEqualTo(response);
            assertThatThrownBy(() -> store.getInsights(response.gameId(), response.attemptId()))
                    .isInstanceOf(LocalResultStore.VisualDocumentNotAvailable.class);
        }
        before.forEach((name, bytes) -> {
            try { assertThat(Files.readAllBytes(attempt.resolve(name))).isEqualTo(bytes); }
            catch (java.io.IOException e) { throw new AssertionError(e); }
        });
    }
    @Test void tamperedVisualHashOrIdentityMakesWholeAttemptUnavailable() throws Exception {
        var entry = entry(); Path dir = Files.createDirectory(temp.resolve("results"));
        try (var store = new LocalResultStore(dir)) {
            var response = store.generate("2026_03_BAL_DAL", entry, new LocalRuleSelector());
            Path visual = dir.resolve(response.attemptId()).resolve("insights.json");
            Files.writeString(visual, "{}\n");
            assertThatThrownBy(() -> store.getInsights(response.gameId(), response.attemptId()))
                    .isInstanceOf(java.io.IOException.class).hasMessage("INCOMPLETE_RESULT");
            assertThatThrownBy(() -> store.get(response.gameId(), response.attemptId()))
                    .isInstanceOf(java.io.IOException.class).hasMessage("INCOMPLETE_RESULT");
        }
    }
    @Test void unsupportedPostseasonPhaseKeepsValidatedTextInExplicitV3Attempt() throws Exception {
        var raw = FrozenContext.MAPPER.createObjectNode().put("contract_version", 3)
                .put("home_team", "DAL").put("away_team", "BAL");
        raw.putObject("game").put("game_id", "2026_20_BAL_DAL").put("season", 2026).put("week", 20).put("phase", "WC");
        raw.putArray("evidence");
        var context = FrozenContext.read(raw);
        Path dir = Files.createDirectory(temp.resolve("results"));
        try (var store = new LocalResultStore(dir)) {
            var response = store.generate("2026_20_BAL_DAL", new LocalContextCatalog.Entry(context, "0".repeat(64)), new LocalRuleSelector());
            assertThat(store.get(response.gameId(), response.attemptId())).isEqualTo(response);
            assertThat(FrozenContext.MAPPER.readTree(dir.resolve(response.attemptId()).resolve("result.json").toFile())
                    .path("artifactVersion").asInt()).isEqualTo(3);
            assertThat(dir.resolve(response.attemptId()).resolve("insights.json")).doesNotExist();
            assertThatThrownBy(() -> store.getInsights(response.gameId(), response.attemptId()))
                    .isInstanceOf(LocalResultStore.VisualDocumentNotAvailable.class);
        }
    }
}
