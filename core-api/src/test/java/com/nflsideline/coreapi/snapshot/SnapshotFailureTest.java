package com.nflsideline.coreapi.snapshot;

import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.sql.SQLException;
import static org.assertj.core.api.Assertions.assertThat;
import java.time.Clock;

class SnapshotFailureTest {
    @Test
    void reportsActionableCodesWithoutLeakingExceptionPayloads() {
        String secret = "jdbc:postgresql://private-host password=private-value context_json=payload";
        assertThat(SnapshotBatchApplication.failureSummary("options", new IllegalArgumentException(secret)))
                .contains("INVALID_OPTIONS").doesNotContain(secret);
        assertThat(SnapshotBatchApplication.failureSummary("startup", new RuntimeException(secret, new SQLException(secret))))
                .contains("DATABASE_READ_FAILED").doesNotContain(secret);
        assertThat(SnapshotBatchApplication.failureSummary("export", new IOException(secret)))
                .contains("OUTPUT_WRITE_FAILED").doesNotContain(secret);
        assertThat(SnapshotBatchApplication.failureSummary("export", new SnapshotExporter.EmptySeasonException()))
                .contains("EMPTY_SEASON", "--allow-empty");
        assertThat(SnapshotBatchApplication.failureSummary("export",
                new SnapshotExporter.InvalidEditorialManifestException()))
                .contains("EDITORIAL_MANIFEST_INVALID").doesNotContain(secret);
        Exception invalidDate = org.junit.jupiter.api.Assertions.assertThrows(IllegalArgumentException.class,
                () -> SnapshotOptions.parse(new String[]{"--output", "data", "--as-of", secret}, Clock.systemUTC()));
        assertThat(SnapshotBatchApplication.failureSummary("options", invalidDate))
                .contains("INVALID_OPTIONS").doesNotContain(secret);
    }
}
