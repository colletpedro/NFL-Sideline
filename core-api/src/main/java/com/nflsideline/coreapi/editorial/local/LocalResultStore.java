package com.nflsideline.coreapi.editorial.local;

import com.fasterxml.jackson.databind.JsonNode;
import com.nflsideline.coreapi.editorial.ClaimSelector;
import java.io.IOException;
import java.nio.channels.*;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;

/** One owner per store; immutable UUID attempts; atomic completion marker is the only read boundary. */
public final class LocalResultStore implements AutoCloseable {
    public record Response(String mode, boolean publicationApproved, String gameId, String attemptId,
                           String resultIdentity, LocalGenerationService.Texts analysis) { }
    public record InsightsResponse(String mode, boolean publicationApproved, String gameId, String attemptId,
                                   String resultIdentity, String visualIdentity, JsonNode document) { }
    public static final class VisualDocumentNotAvailable extends IOException {
        public VisualDocumentNotAvailable() { super("VISUAL_DOCUMENT_NOT_AVAILABLE"); }
    }
    private final Path root;
    private final FileChannel channel;
    private final FileLock lock;
    private final LocalGenerationService service = new LocalGenerationService();
    public LocalResultStore(Path directory) throws IOException {
        root = directory.toRealPath();
        for (Path part : root) if (part.toString().equals("public")) throw new IllegalArgumentException("PUBLIC_OUTPUT_FORBIDDEN");
        Path owner = root.resolve(".owner");
        if (Files.isSymbolicLink(owner)) throw new IOException("INVALID_STORE");
        channel = FileChannel.open(owner, StandardOpenOption.CREATE, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
        try {
            lock = channel.tryLock();
            if (lock == null) throw new IOException("STORE_IN_USE");
        } catch (IOException | RuntimeException e) { channel.close(); throw e; }
    }
    public Response generate(String gameId, LocalContextCatalog.Entry entry, ClaimSelector selector) throws IOException {
        LocalContextCatalog.requireId(gameId);
        String attempt = UUID.randomUUID().toString();
        Path dir = root.resolve(attempt);
        Files.createDirectory(dir);
        var audit = FrozenContext.MAPPER.createObjectNode().put("artifactVersion", 4)
                .put("startedAt", Instant.now().toString()).put("gameId", gameId).put("attemptId", attempt)
                .put("sourceFileSha256", entry.sourceSha256()).put("serviceVersion", LocalGenerationService.VERSION);
        try {
            write(dir.resolve("context.json"), FrozenContext.MAPPER.readTree(entry.context().canonicalJson()));
            var result = service.generate(entry.context(), FrozenContext.parameters(entry.context()), selector, entry.declaredAsOfDate());
            write(dir.resolve("selection.json"), result.selection());
            write(dir.resolve("claims.json"), result.selection().document());
            write(dir.resolve("rendered.json"), result.texts());
            if (result.insights() == null) audit.put("artifactVersion", 3);
            else {
                write(dir.resolve("insights.json"), result.insights());
                audit.put("visualIdentity", LocalGenerationService.sha256(Files.readAllBytes(dir.resolve("insights.json"))));
            }
            audit.set("identity", FrozenContext.MAPPER.valueToTree(result.identity()));
            audit.put("resultIdentity", result.identity().hash()).put("status", "VALIDATED")
                    .put("publicationApproved", false).put("mode", "LOCAL_RULES_DEVELOPMENT");
            write(dir.resolve("result.json"), audit);
            var response = new Response("LOCAL_RULES_DEVELOPMENT", false, gameId, attempt, result.identity().hash(), result.texts());
            var marker = FrozenContext.MAPPER.createObjectNode();
            marker.set("response", FrozenContext.MAPPER.valueToTree(response));
            var hashes = marker.putObject("hashes");
            for (String name : result.insights() == null ? ARTIFACTS_V3 : ARTIFACTS_V4)
                hashes.put(name, LocalGenerationService.sha256(Files.readAllBytes(dir.resolve(name))));
            write(dir.resolve("complete.tmp"), marker);
            Files.move(dir.resolve("complete.tmp"), dir.resolve("complete.json"), StandardCopyOption.ATOMIC_MOVE);
            return response;
        } catch (Exception failure) {
            audit.put("status", "FAILED").put("failureType", failure.getClass().getName());
            if (failure instanceof LocalGenerationService.Rejected rejected) {
                audit.put("causeType", rejected.getCause().getClass().getName());
                audit.set("rejectedSelection", FrozenContext.MAPPER.valueToTree(rejected.selection()));
            }
            // Keep diagnostics internal; never publish a complete marker on failure.
            try { write(dir.resolve("failure.json"), audit); } catch (IOException suppressed) { failure.addSuppressed(suppressed); }
            throw new IOException("LOCAL_GENERATION_FAILED", failure);
        }
    }
    private static final List<String> ARTIFACTS_V3 = List.of("context.json", "selection.json", "claims.json", "rendered.json", "result.json");
    private static final List<String> ARTIFACTS_V4 = List.of("context.json", "selection.json", "claims.json", "rendered.json", "result.json", "insights.json");
    public record Attempt(String attemptId, String startedAt, String resultIdentity, String sourceSha256) { }
    public record History(List<Attempt> attempts, int unavailableInStore) { }
    /** Lists only complete, hash-checked attempts. Unavailable entries are counted across the store. */
    public History list(String gameId) throws IOException {
        LocalContextCatalog.requireId(gameId);
        var attempts = new ArrayList<Attempt>();
        int unavailable = 0;
        try (var paths = Files.list(root)) {
            for (Path dir : paths.filter(p -> !p.getFileName().toString().equals(".owner")).toList()) {
                try {
                    if (Files.isSymbolicLink(dir) || !Files.isDirectory(dir, LinkOption.NOFOLLOW_LINKS))
                        throw new IOException("INVALID_STORE");
                    var marker = read(dir.resolve("complete.json"));
                    String storedGame = marker.path("response").path("gameId").asText();
                    var response = get(storedGame, dir.getFileName().toString());
                    if (!gameId.equals(response.gameId())) continue;
                    var audit = read(dir.resolve("result.json"));
                    attempts.add(new Attempt(response.attemptId(), audit.path("startedAt").asText(),
                            response.resultIdentity(), audit.path("sourceFileSha256").asText()));
                } catch (IOException | IllegalArgumentException | NoSuchElementException e) { unavailable++; }
            }
        }
        attempts.sort(Comparator.comparing(Attempt::startedAt).reversed().thenComparing(Attempt::attemptId));
        return new History(List.copyOf(attempts), unavailable);
    }
    public Response get(String gameId, String attempt) throws IOException {
        LocalContextCatalog.requireId(gameId);
        if (!attempt.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"))
            throw new IllegalArgumentException("INVALID_ATTEMPT_ID");
        Path dir = root.resolve(attempt);
        if (!Files.exists(dir, LinkOption.NOFOLLOW_LINKS)) throw new NoSuchElementException("RESULT_NOT_FOUND");
        if (Files.isSymbolicLink(dir) || !dir.toRealPath().startsWith(root)) throw new IOException("INVALID_STORE");
        JsonNode marker;
        try {
            marker = read(dir.resolve("complete.json"));
            var result = read(dir.resolve("result.json"));
            int version = result.path("artifactVersion").asInt(-1);
            List<String> artifacts = version == 3 ? ARTIFACTS_V3 : version == 4 ? ARTIFACTS_V4 : null;
            if (artifacts == null || marker.path("hashes").size() != artifacts.size()) throw new IOException("INCOMPLETE_RESULT");
            for (String name : artifacts) {
                Path file = dir.resolve(name);
                if (Files.isSymbolicLink(file) || !Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS)
                        || !LocalGenerationService.sha256(Files.readAllBytes(file)).equals(marker.path("hashes").path(name).asText()))
                    throw new IOException("INCOMPLETE_RESULT");
            }
            var rendered = read(dir.resolve("rendered.json"));
            var identity = FrozenContext.MAPPER.treeToValue(result.path("identity"), LocalGenerationService.Identity.class);
            var context = FrozenContext.read(read(dir.resolve("context.json")));
            if (!"VALIDATED".equals(result.path("status").asText())
                    || !rendered.equals(marker.path("response").path("analysis"))
                    || !result.path("resultIdentity").equals(marker.path("response").path("resultIdentity"))
                    || !identity.hash().equals(result.path("resultIdentity").asText())
                    || !identity.contextSha256().equals(LocalGenerationService.sha256(
                            context.canonicalJson().getBytes(java.nio.charset.StandardCharsets.UTF_8)))
                    || version == 4 && (!result.path("visualIdentity").asText().equals(marker.path("hashes").path("insights.json").asText())
                    || !"VALIDATED_LOCAL_RESULT".equals(read(dir.resolve("insights.json")).path("source").path("kind").asText())
                    || !result.path("resultIdentity").equals(read(dir.resolve("insights.json")).path("source").path("resultIdentity"))
                    || !result.path("identity").path("contextSha256").equals(read(dir.resolve("insights.json")).path("source").path("contextSha256"))))
                throw new IOException("INCOMPLETE_RESULT");
        } catch (IOException | RuntimeException e) { throw new IOException("INCOMPLETE_RESULT", e); }
        Response response = FrozenContext.MAPPER.treeToValue(marker.path("response"), Response.class);
        if (!attempt.equals(response.attemptId()) || !gameId.equals(response.gameId())) throw new NoSuchElementException("RESULT_NOT_FOUND");
        return response;
    }
    public InsightsResponse getInsights(String gameId, String attempt) throws IOException {
        Response response = get(gameId, attempt);
        Path dir = root.resolve(attempt);
        JsonNode result = read(dir.resolve("result.json"));
        if (result.path("artifactVersion").asInt(-1) == 3) throw new VisualDocumentNotAvailable();
        JsonNode document = read(dir.resolve("insights.json"));
        String hash = LocalGenerationService.sha256(Files.readAllBytes(dir.resolve("insights.json")));
        if (!hash.equals(result.path("visualIdentity").asText())
                || !response.resultIdentity().equals(document.path("source").path("resultIdentity").asText())
                || !response.gameId().equals(document.path("game").path("gameId").asText()))
            throw new IOException("INCOMPLETE_RESULT");
        return new InsightsResponse(response.mode(), response.publicationApproved(), gameId, attempt,
                response.resultIdentity(), hash, document);
    }
    private static JsonNode read(Path path) throws IOException {
        if (Files.isSymbolicLink(path)) throw new IOException("INVALID_STORE");
        return FrozenContext.MAPPER.readTree(Files.readAllBytes(path));
    }
    static void write(Path path, Object value) throws IOException {
        Files.writeString(path, FrozenContext.MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(value) + "\n", StandardOpenOption.CREATE_NEW);
    }
    @Override public void close() throws IOException { lock.release(); channel.close(); }
}
