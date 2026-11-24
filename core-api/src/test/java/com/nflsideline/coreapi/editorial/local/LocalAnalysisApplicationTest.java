package com.nflsideline.coreapi.editorial.local;

import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import static org.assertj.core.api.Assertions.*;

class LocalAnalysisApplicationTest {
    @TempDir Path temp;
    @Test void offlineArtifactsAreSanitizedVersionedAndNeverOverwritten() throws Exception {
        var input = input();
        input.put("api_key", "secret-value-must-not-be-copied");
        Path file = temp.resolve("input.json"), output = temp.resolve("attempt");
        Files.writeString(file, input.toString());
        assertThat(LocalAnalysisApplication.run(new String[]{file.toString(), output.toString()})).isZero();
        var result = FrozenContext.MAPPER.readTree(output.resolve("result.json").toFile());
        assertThat(result.path("status").asText()).isEqualTo("VALIDATED");
        assertThat(result.path("selector").path("name").asText()).isEqualTo("local-descriptive-rules");
        assertThat(result.path("contractVersion").asInt()).isEqualTo(5);
        assertThat(result.path("contextSha256").asText()).hasSize(64);
        assertThat(result.path("resultIdentity").asText()).hasSize(64);
        String before = Files.readString(output.resolve("result.json"));
        assertThat(LocalAnalysisApplication.run(new String[]{file.toString(), output.toString()})).isEqualTo(1);
        assertThat(Files.readString(output.resolve("result.json"))).isEqualTo(before);
        try (var files = Files.list(output)) {
            for (var artifact : files.toList()) assertThat(Files.readString(artifact)).doesNotContain("secret-value", "api_key");
        }
        var rendered = FrozenContext.MAPPER.readTree(output.resolve("rendered.json").toFile());
        assertThat(rendered.size()).isEqualTo(4);
        assertThat(rendered.path("veredito").asText()).contains("não estima o vencedor");
    }
    @Test void invalidContextPersistsSanitizedFailureAndPublicPathsAreRejectedIncludingSymlinks() throws Exception {
        Path file = temp.resolve("bad.json"), output = temp.resolve("failed");
        Files.writeString(file, "{\"secret\":\"must-not-appear\"}");
        assertThat(LocalAnalysisApplication.run(new String[]{file.toString(), output.toString()})).isEqualTo(1);
        assertThat(Files.readString(output.resolve("result.json"))).contains("INVALID_LOCAL_INPUT").doesNotContain("must-not-appear");
        Path publicDir = Files.createDirectory(temp.resolve("public"));
        Path alias = Files.createSymbolicLink(temp.resolve("alias"), publicDir);
        assertThat(LocalAnalysisApplication.run(new String[]{file.toString(), alias.resolve("attempt").toString()})).isEqualTo(1);
        assertThat(publicDir.resolve("attempt")).doesNotExist();
        Path parent = Files.createDirectory(temp.resolve("fresh"));
        assertThat(LocalAnalysisApplication.run(new String[]{file.toString(), parent.resolve("public").toString()})).isEqualTo(1);
        assertThat(parent.resolve("public")).doesNotExist();
    }
    @Test void derivedWindowsAndCoverageAreRebuiltFromObservedEvidence() throws Exception {
        var input = input(); input.putArray("recent_windows").addObject().put("value", 1000);
        input.put("data_coverage", "COMPLETE");
        var context = FrozenContext.read(input);
        assertThat(context.windows()).isEmpty();
        assertThat(context.quality().name()).isEqualTo("MINIMAL");
        assertThat(context.canonicalJson()).doesNotContain("1000");
    }
    private ObjectNode input() {
        var root = FrozenContext.MAPPER.createObjectNode().put("contract_version", 3).put("home_team", "AAA").put("away_team", "BBB");
        root.putObject("game").put("game_id", "empty").put("season", 2026).put("week", 3).put("phase", "REG");
        root.putArray("evidence"); return root;
    }
}
