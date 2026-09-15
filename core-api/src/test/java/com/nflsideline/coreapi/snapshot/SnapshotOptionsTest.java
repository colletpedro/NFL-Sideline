package com.nflsideline.coreapi.snapshot;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class SnapshotOptionsTest {

    private static final Clock SEPTEMBER = Clock.fixed(Instant.parse("2026-09-10T12:00:00Z"), ZoneOffset.UTC);

    @Test
    void parsesRepeatedSeasonsDeduplicatesAndSorts() {
        SnapshotOptions options = SnapshotOptions.parse(new String[]{
                "--season", "2026", "--season=2025", "--season", "2026",
                "--output", "../public/data", "--allow-empty", "--as-of", "2026-09-15"
        }, SEPTEMBER);

        assertThat(options.seasons()).containsExactly(2025, 2026);
        assertThat(options.allowEmpty()).isTrue();
        assertThat(options.outputDirectory()).isAbsolute();
        assertThat(options.asOfDate()).isEqualTo(java.time.LocalDate.parse("2026-09-15"));
    }

    @Test
    void defaultsToCurrentNflSeasonOnlyWhenSeasonIsAbsent() {
        assertThat(SnapshotOptions.parse(new String[]{"--output", "data", "--as-of=2026-09-15"}, SEPTEMBER).seasons())
                .containsExactly(2026);
        Clock january = Clock.fixed(Instant.parse("2027-01-10T12:00:00Z"), ZoneOffset.UTC);
        assertThat(SnapshotOptions.parse(new String[]{"--output", "data", "--as-of=2027-01-10"}, january).seasons())
                .containsExactly(2026);
    }

    @Test
    void requiresOutputAndValidSeason() {
        assertThatThrownBy(() -> SnapshotOptions.parse(new String[]{"--season", "2026"}, SEPTEMBER))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SnapshotOptions.parse(new String[]{"--season", "x", "--output", "data"}, SEPTEMBER))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SnapshotOptions.parse(new String[]{"--output", "data"}, SEPTEMBER))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SnapshotOptions.parse(
                new String[]{"--output", "data", "--as-of", "private-payload"}, SEPTEMBER))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("--as-of must use YYYY-MM-DD");
    }
}
