package com.nflsideline.coreapi.snapshot;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Profile;

import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Comparator;
import java.util.Map;
import java.util.UUID;

@Component
@Profile("snapshot")
public class AtomicSnapshotWriter {

    private final ObjectMapper objectMapper;
    private final FileMover fileMover;

    @Autowired
    public AtomicSnapshotWriter(ObjectMapper objectMapper) {
        this(objectMapper, AtomicSnapshotWriter::movePath);
    }

    AtomicSnapshotWriter(ObjectMapper objectMapper, FileMover fileMover) {
        this.objectMapper = objectMapper.copy()
                .enable(SerializationFeature.INDENT_OUTPUT)
                .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);
        this.fileMover = fileMover;
    }

    public WriteResult write(Path outputDirectory, SnapshotContract.Manifest manifest,
                             Map<Integer, SnapshotContract.SeasonSnapshot> snapshots) throws IOException {
        Path output = outputDirectory.toAbsolutePath().normalize();
        Path parent = output.getParent();
        if (parent == null) {
            throw new IOException("Snapshot output requires a parent directory");
        }
        Files.createDirectories(parent);
        Path temporary = parent.resolve("." + output.getFileName() + ".tmp-" + UUID.randomUUID());
        Path backup = parent.resolve("." + output.getFileName() + ".backup-" + UUID.randomUUID());
        boolean movedExisting = false;
        try {
            Files.createDirectories(temporary.resolve("seasons"));
            writeJson(temporary.resolve("manifest.json"), manifest);
            for (Map.Entry<Integer, SnapshotContract.SeasonSnapshot> entry : snapshots.entrySet()) {
                writeJson(temporary.resolve("seasons").resolve(entry.getKey() + ".json"), entry.getValue());
            }

            if (Files.isDirectory(output) && materiallyEqual(output, temporary)) {
                deleteTree(temporary);
                return new WriteResult(false, output);
            }

            if (Files.exists(output)) {
                fileMover.move(output, backup);
                movedExisting = true;
            }
            try {
                fileMover.move(temporary, output);
            } catch (IOException failure) {
                if (movedExisting && !Files.exists(output)) {
                    fileMover.move(backup, output);
                    movedExisting = false;
                }
                throw failure;
            }
            if (movedExisting) {
                deleteTree(backup);
            }
            return new WriteResult(true, output);
        } finally {
            deleteTreeIfExists(temporary);
            if (movedExisting && Files.exists(backup) && !Files.exists(output)) {
                fileMover.move(backup, output);
            }
            deleteTreeIfExists(backup);
        }
    }

    private void writeJson(Path path, Object value) throws IOException {
        objectMapper.writeValue(path.toFile(), value);
        Files.writeString(path, Files.readString(path) + System.lineSeparator());
    }

    private boolean materiallyEqual(Path current, Path candidate) throws IOException {
        if (!Files.isRegularFile(current.resolve("manifest.json"))
                || !Files.isDirectory(current.resolve("seasons"))) {
            return false;
        }
        JsonNode currentManifest = withoutGeneratedAt(objectMapper.readTree(current.resolve("manifest.json").toFile()));
        JsonNode candidateManifest = withoutGeneratedAt(objectMapper.readTree(candidate.resolve("manifest.json").toFile()));
        if (!currentManifest.equals(candidateManifest)) {
            return false;
        }
        try (var files = Files.walk(candidate.resolve("seasons"))) {
            for (Path candidateFile : files.filter(Files::isRegularFile).toList()) {
                Path relative = candidate.relativize(candidateFile);
                Path currentFile = current.resolve(relative);
                if (!Files.isRegularFile(currentFile)) {
                    return false;
                }
                JsonNode left = withoutGeneratedAt(objectMapper.readTree(currentFile.toFile()));
                JsonNode right = withoutGeneratedAt(objectMapper.readTree(candidateFile.toFile()));
                if (!left.equals(right)) {
                    return false;
                }
            }
        }
        try (var files = Files.walk(current.resolve("seasons"))) {
            return files.filter(Files::isRegularFile).count() == snapshotsCount(candidate.resolve("seasons"));
        }
    }

    private long snapshotsCount(Path directory) throws IOException {
        try (var files = Files.walk(directory)) {
            return files.filter(Files::isRegularFile).count();
        }
    }

    private JsonNode withoutGeneratedAt(JsonNode source) {
        JsonNode copy = source.deepCopy();
        if (copy.isObject()) {
            ((com.fasterxml.jackson.databind.node.ObjectNode) copy).remove("generatedAt");
        }
        return copy;
    }

    private static void movePath(Path source, Path target) throws IOException {
        try {
            Files.move(source, target, StandardCopyOption.ATOMIC_MOVE);
        } catch (AtomicMoveNotSupportedException ignored) {
            Files.move(source, target);
        }
    }

    private static void deleteTreeIfExists(Path path) throws IOException {
        if (Files.exists(path)) {
            deleteTree(path);
        }
    }

    private static void deleteTree(Path path) throws IOException {
        try (var files = Files.walk(path)) {
            for (Path entry : files.sorted(Comparator.reverseOrder()).toList()) {
                Files.deleteIfExists(entry);
            }
        }
    }

    interface FileMover {
        void move(Path source, Path target) throws IOException;
    }

    public record WriteResult(boolean changed, Path outputDirectory) {
    }
}
