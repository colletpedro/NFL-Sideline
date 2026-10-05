package com.nflsideline.coreapi.editorial.local;

import com.nflsideline.coreapi.editorial.AnalysisContext;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;

/** Flat, startup-only snapshot. Requests never read client-supplied paths or changed input files. */
public final class LocalContextCatalog {
    public record Entry(AnalysisContext context, String sourceSha256) { }
    private final Map<String, Entry> entries;
    public LocalContextCatalog(Path directory) throws IOException {
        Path root = directory.toRealPath();
        var items = new TreeMap<String, Entry>();
        try (var files = Files.list(root)) {
            for (Path file : files.sorted().toList()) {
                if (Files.isSymbolicLink(file) || !Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS)
                        || !file.getFileName().toString().endsWith(".json") || !file.toRealPath().startsWith(root))
                    throw new IllegalArgumentException("INVALID_CATALOG_ENTRY");
                byte[] bytes = Files.readAllBytes(file);
                var context = FrozenContext.read(FrozenContext.MAPPER.readTree(bytes));
                String id = FrozenContext.MAPPER.readTree(context.canonicalJson()).path("game").path("game_id").asText();
                requireId(id);
                if (items.putIfAbsent(id, new Entry(context, LocalGenerationService.sha256(bytes))) != null)
                    throw new IllegalArgumentException("AMBIGUOUS_GAME_ID");
            }
        }
        if (items.isEmpty()) throw new IllegalArgumentException("EMPTY_CATALOG");
        entries = Collections.unmodifiableMap(items);
    }
    public Entry get(String id) {
        requireId(id);
        var entry = entries.get(id);
        if (entry == null) throw new NoSuchElementException("CONTEXT_NOT_FOUND");
        return entry;
    }
    public static void requireId(String id) {
        if (id == null || !id.matches("[A-Za-z0-9_-]{1,128}")) throw new IllegalArgumentException("INVALID_GAME_ID");
    }
}
