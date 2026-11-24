package com.nflsideline.coreapi.editorial.evaluation;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.editorial.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.*;

class EvaluationApplicationTest {
    @TempDir Path directory;
    private final ObjectMapper mapper = new ObjectMapper();

    @Test void frozenOriginalsPreserveHistoricalCutoffAndDoNotImportMarket() throws Exception {
        var originals = mapper.readTree(Path.of("../editorial/evaluations/2026-09-26/regression/originals.json").toFile());
        assertThat(originals.size()).isEqualTo(16);
        for (var original : originals) {
            var input = original.path("context_json");
            var context = EvaluationApplication.fromFrozenLegacy(input);
            assertThat(context.evidence()).isNotEmpty().allSatisfy(evidence -> {
                assertThat(evidence.season()).isEqualTo(2026);
                assertThat(evidence.week()).isBetween(1, 2);
            });
            var canonical = mapper.readTree(context.canonicalJson());
            assertThat(canonical.has("market")).isFalse();
            assertThat(canonical.has("odds")).isFalse();
            assertThat(canonical.path("game").path("as_of_date_utc").asText()).isEqualTo("2026-09-22");
            // Every stored non-null observation survives the adaptation, including the weekly extreme.
            int count = 0;
            for (String side : List.of("home_team", "away_team")) {
                for (var row : input.path(side).path("recent_form_last_3_eligible_weeks")) {
                    var metrics = mapper.treeToValue(row, com.nflsideline.coreapi.domain.TeamWeekMetrics.class);
                    for (var metric : MetricCatalog.values()) if (metric.value(metrics) != null) {
                        count++;
                        var found = context.evidence().stream().filter(e -> e.team().equals(metrics.getId().getTeamAbbr())
                                && e.week() == metrics.getId().getWeek() && e.metric() == metric).findFirst().orElseThrow();
                        assertThat(found.value()).isEqualByComparingTo(metric.value(metrics));
                        assertThat(found.volume()).isEqualTo(metric.volume(metrics));
                    }
                }
            }
            assertThat(context.evidence()).hasSize(count);
        }
    }

    @Test void rejectsSameWeekEvidenceInsteadOfRefreshingOrHidingIt() throws Exception {
        var originals = mapper.readTree(Path.of("../editorial/evaluations/2026-09-26/regression/originals.json").toFile());
        var context = originals.get(0).path("context_json");
        ((com.fasterxml.jackson.databind.node.ObjectNode) context.path("home_team")
                .path("recent_form_last_3_eligible_weeks").get(0).path("id")).put("week", 3);
        assertThatThrownBy(() -> EvaluationApplication.fromFrozenLegacy(context)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void rejectedClaimsAndOriginalResponseRemainAuditableAndCannotBeOverwritten() throws Exception {
        String raw = "{\"contract_version\":3,\"claims\":[],\"sections\":{}}";
        var context = new AnalysisContext("{}", ContextQuality.MINIMAL, List.of(), "BUF", "BAL");
        assertThat(EvaluationApplication.recordResponse(directory, raw, context)).isFalse();
        assertThat(Files.readString(directory.resolve("response-original.txt"))).isEqualTo(raw);
        assertThat(Files.readString(directory.resolve("claims.json")).trim()).isEqualTo("[ ]");
        assertThat(Files.readString(directory.resolve("result.json"))).contains("REJECTED", "MISSING_FIELDS");
        assertThat(directory.resolve("rendered.json")).doesNotExist();
        assertThatThrownBy(() -> EvaluationApplication.recordResponse(directory, "replacement", context))
                .isInstanceOf(java.nio.file.FileAlreadyExistsException.class);
    }

    @Test void invalidJsonIsPreservedWithoutInventingClaims() throws Exception {
        assertThat(EvaluationApplication.recordResponse(directory, "not json", new AnalysisContext("{}", ContextQuality.MINIMAL))).isFalse();
        assertThat(Files.readString(directory.resolve("result.json"))).contains("INVALID_JSON");
        assertThat(directory.resolve("claims.json")).doesNotExist();
    }

    @Test void publicArtifactOutputIsRejected() throws Exception {
        Path publicDir = Files.createDirectory(directory.resolve("public"));
        assertThat(EvaluationApplication.run(new String[]{"prepare", "missing.json", publicDir.resolve("evaluation").toString()})).isEqualTo(1);
        assertThat(publicDir.resolve("evaluation")).doesNotExist();
    }
}
