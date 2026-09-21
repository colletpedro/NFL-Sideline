package com.nflsideline.coreapi.editorial.batch;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class EditorialBatchOptionsTest {
    @Test
    void defaultsToDryRunAndRequiresExplicitTemporalIdentity() {
        var options = EditorialBatchOptions.parse(new String[]{"--season", "2026", "--as-of", "2026-09-15",
                "--revision-key", "first-pass", "--max-analyses", "32"});
        assertThat(options.season()).isEqualTo(2026);
        assertThat(options.asOfDate()).isEqualTo(LocalDate.parse("2026-09-15"));
        assertThat(options.dryRun()).isTrue();
        assertThat(options.maxAnalyses()).isEqualTo(32);
        assertThat(options.gameIds()).isEmpty();
        assertThat(EditorialBatchOptions.parse(new String[]{"--season=2026", "--as-of=2026-09-15",
                "--revision-key=r", "--execute"}).dryRun()).isFalse();
        assertThatThrownBy(() -> EditorialBatchOptions.parse(new String[]{"--season=2026", "--revision-key=r"}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void repeatedGameIdsAreDeduplicatedInFirstSeenOrder() {
        var options = EditorialBatchOptions.parse(new String[]{"--season=2026", "--as-of=2026-09-15",
                "--revision-key=r", "--game-id", "g2", "--game-id=g1", "--game-id", "g2"});
        assertThat(options.gameIds()).containsExactly("g2", "g1");
    }
}
