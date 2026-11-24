package com.nflsideline.coreapi.editorial.local;

import com.nflsideline.coreapi.editorial.AnalysisContext;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;

/** Flat, startup-only snapshot. Requests never read client-supplied paths or changed input files. */
public final class LocalContextCatalog {
    public record Entry(AnalysisContext context, String sourceSha256, String declaredAsOfDate) {
        public Entry(AnalysisContext context, String sourceSha256) { this(context, sourceSha256, null); }
    }
    private final Map<String, Entry> entries;
    private final List<Summary> summaries;
    public LocalContextCatalog(Path directory) throws IOException {
        Path root = directory.toRealPath();
        var items = new TreeMap<String, Entry>();
        var metadata = new TreeMap<String, Summary>();
        try (var files = Files.list(root)) {
            for (Path file : files.sorted().toList()) {
                if (Files.isSymbolicLink(file) || !Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS)
                        || !file.getFileName().toString().endsWith(".json") || !file.toRealPath().startsWith(root))
                    throw new IllegalArgumentException("INVALID_CATALOG_ENTRY");
                byte[] bytes = Files.readAllBytes(file);
                var source = FrozenContext.MAPPER.readTree(bytes);
                var context = FrozenContext.read(source);
                String id = FrozenContext.MAPPER.readTree(context.canonicalJson()).path("game").path("game_id").asText();
                requireId(id);
                String asOf = optionalDate(source.path("game").path("as_of_date_utc").asText());
                if (items.putIfAbsent(id, new Entry(context, LocalGenerationService.sha256(bytes),
                        asOf.isEmpty() ? null : asOf)) != null)
                    throw new IllegalArgumentException("AMBIGUOUS_GAME_ID");
                var game = source.path("game");
                metadata.put(id, new Summary(id, context.homeTeam(), context.awayTeam(), game.path("season").asInt(),
                        game.path("week").asInt(), game.path("phase").asText(), optionalDate(game.path("gameday").asText()),
                        optionalDate(game.path("as_of_date_utc").asText()), items.get(id).sourceSha256()));
            }
        }
        if (items.isEmpty()) throw new IllegalArgumentException("EMPTY_CATALOG");
        entries = Collections.unmodifiableMap(items);
        summaries = List.copyOf(metadata.values());
    }
    public Entry get(String id) {
        requireId(id);
        var entry = entries.get(id);
        if (entry == null) throw new NoSuchElementException("CONTEXT_NOT_FOUND");
        return entry;
    }
    public record Summary(String gameId, String homeTeam, String awayTeam, int season, int week,
                          String phase, String gameday, String asOfDate, String sourceSha256) { }
    public List<Summary> list() { return summaries; }
    private static String optionalDate(String date) {
        try { return java.time.LocalDate.parse(date).toString(); }
        catch (java.time.format.DateTimeParseException e) { return ""; }
    }
    public static void requireId(String id) {
        if (id == null || !id.matches("[A-Za-z0-9_-]{1,128}")) throw new IllegalArgumentException("INVALID_GAME_ID");
    }
}
