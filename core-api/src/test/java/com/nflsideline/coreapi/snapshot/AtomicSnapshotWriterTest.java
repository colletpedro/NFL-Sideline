package com.nflsideline.coreapi.snapshot;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AtomicSnapshotWriterTest {

    @TempDir
    Path temporaryDirectory;

    @Test
    void deterministicMaterialDoesNotRewriteFilesForTimestampOnlyChange() throws Exception {
        AtomicSnapshotWriter writer = new AtomicSnapshotWriter(mapper());
        Path output = temporaryDirectory.resolve("data");
        var first = documents("2026-09-10T12:00:00Z");
        assertThat(writer.write(output, first.manifest(), first.snapshots()).changed()).isTrue();
        String original = Files.readString(output.resolve("manifest.json"));
        var second = documents("2026-09-10T13:00:00Z");

        assertThat(writer.write(output, second.manifest(), second.snapshots()).changed()).isFalse();
        assertThat(Files.readString(output.resolve("manifest.json"))).isEqualTo(original);
    }

    @Test
    void failedSwapRestoresPreviousCompleteOutput() throws Exception {
        Path output = temporaryDirectory.resolve("data");
        Files.createDirectories(output);
        Files.writeString(output.resolve("sentinel.txt"), "complete-old-output");
        AtomicInteger moves = new AtomicInteger();
        AtomicSnapshotWriter writer = new AtomicSnapshotWriter(mapper(), (source, target) -> {
            if (moves.incrementAndGet() == 2) throw new IOException("simulated swap failure");
            Files.move(source, target, StandardCopyOption.ATOMIC_MOVE);
        });
        var documents = documents("2026-09-10T12:00:00Z");

        assertThatThrownBy(() -> writer.write(output, documents.manifest(), documents.snapshots()))
                .isInstanceOf(IOException.class);
        assertThat(Files.readString(output.resolve("sentinel.txt"))).isEqualTo("complete-old-output");
        assertThat(Files.exists(output.resolve("manifest.json"))).isFalse();
    }

    private Documents documents(String timestamp) {
        OffsetDateTime generatedAt = OffsetDateTime.parse(timestamp);
        SnapshotContract.Manifest manifest = new SnapshotContract.Manifest(1, generatedAt, 2026, List.of(2026));
        SnapshotContract.SeasonSnapshot season = new SnapshotContract.SeasonSnapshot(
                1, 2026, generatedAt, List.of(), List.of(), new TreeMap<>(), new TreeMap<>());
        return new Documents(manifest, Map.of(2026, season));
    }

    private ObjectMapper mapper() {
        return new ObjectMapper().findAndRegisterModules();
    }

    private record Documents(SnapshotContract.Manifest manifest,
                             Map<Integer, SnapshotContract.SeasonSnapshot> snapshots) {
    }
}
