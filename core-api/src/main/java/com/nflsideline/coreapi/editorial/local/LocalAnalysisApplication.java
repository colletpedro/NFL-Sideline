package com.nflsideline.coreapi.editorial.local;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.editorial.*;
import com.nflsideline.coreapi.llm.GenerationFailure;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;

/** Standalone offline command: no Spring, datasource, environment credentials, cache or generation client. */
public final class LocalAnalysisApplication {
    private LocalAnalysisApplication() { }
    public static int run(String[] args) {
        Path output = null;
        ObjectNode result = FrozenContext.MAPPER.createObjectNode();
        try {
            if (args.length != 2) throw new IllegalArgumentException("Expected context file and new output directory");
            Path requested = Path.of(args[1]).toAbsolutePath().normalize();
            Path resolved = requested.getParent().toRealPath().resolve(requested.getFileName());
            for (Path part : resolved) if (part.toString().equals("public")) throw new IllegalArgumentException("Public output forbidden");
            Files.createDirectory(resolved); // Atomic reservation; never overwrite even failed attempts.
            output = resolved;
            ClaimSelector selector = new LocalRuleSelector();
            result.put("artifactVersion", 3).put("startedAt", Instant.now().toString())
                    .put("mode", "LOCAL_RULES_OFFLINE").put("contractVersion", 5)
                    .put("rendererVersion", ClaimRenderer.VERSION).put("publicationApproved", false);
            result.set("selector", FrozenContext.MAPPER.valueToTree(selector.identity()));
            byte[] input = Files.readAllBytes(Path.of(args[0]));
            result.put("sourceFileSha256", sha256(input));
            var context = FrozenContext.read(FrozenContext.MAPPER.readTree(input));
            String contextHash = sha256(context.canonicalJson().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            String gameId = FrozenContext.MAPPER.readTree(context.canonicalJson()).path("game").path("game_id").asText();
            result.put("contextSha256", contextHash).put("gameId", gameId);
            write(output.resolve("context.json"), FrozenContext.MAPPER.readTree(context.canonicalJson()));
            var generated = new LocalGenerationService().generate(context, FrozenContext.parameters(context), selector);
            write(output.resolve("selection.json"), FrozenContext.MAPPER.valueToTree(generated.selection()));
            write(output.resolve("claims.json"), FrozenContext.MAPPER.valueToTree(generated.selection().document()));
            write(output.resolve("rendered.json"), FrozenContext.MAPPER.valueToTree(generated.texts()));
            result.put("resultIdentity", generated.identity().hash());
            result.set("identity", FrozenContext.MAPPER.valueToTree(generated.identity()));
            result.put("serviceVersion", LocalGenerationService.VERSION);
            result.put("status", "VALIDATED").putArray("validationFailures");
            write(output.resolve("result.json"), result);
            System.out.println(gameId + " LOCAL_RULES VALIDATED");
            return 0;
        } catch (Exception failure) {
            if (failure instanceof LocalGenerationService.Rejected rejected && output != null) {
                try {
                    write(output.resolve("selection.json"), FrozenContext.MAPPER.valueToTree(rejected.selection()));
                    write(output.resolve("claims.json"), FrozenContext.MAPPER.valueToTree(rejected.selection().document()));
                } catch (java.io.IOException ignored) { /* failure remains rejected */ }
                failure = (Exception) rejected.getCause();
            }
            result.put("status", "REJECTED");
            result.putArray("validationFailures").add(failure instanceof GenerationFailure
                    ? GenerationFailure.classify(failure).name() : failure instanceof IllegalArgumentException ? "INVALID_LOCAL_INPUT" : "LOCAL_IO_OR_RUNTIME_FAILURE");
            if (output != null) try { write(output.resolve("result.json"), result); } catch (java.io.IOException ignored) { /* original failure remains failure */ }
            System.err.println("LOCAL_RULES REJECTED " + result.path("validationFailures"));
            return 1;
        }
    }
    private static void write(Path path, JsonNode value) throws java.io.IOException {
        Files.writeString(path, FrozenContext.MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(value) + "\n", StandardOpenOption.CREATE_NEW);
    }
    private static String sha256(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }
}
