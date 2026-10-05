package com.nflsideline.coreapi.editorial.evaluation;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.editorial.*;
import com.nflsideline.coreapi.llm.*;
import com.nflsideline.coreapi.llm.dto.GeminiRequest;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.*;

/** Internal, frozen-input evaluation. Never starts Spring, reads a database or writes a cache. */
public final class EvaluationApplication {
    private static final ObjectMapper MAPPER = new ObjectMapper()
            .enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    private static final String MODEL = "gemini-3.1-pro-preview";

    private EvaluationApplication() { }

    // prepare <originals.json> <contexts-dir>
    // generate <cases.json> <development|holdout> <new-output-dir>
    // replay <cases.json> <development|holdout> <new-output-dir> <prior-output-dir>
    public static int run(String[] args) {
        try {
            if (args.length == 3 && args[0].equals("prepare")) {
                Path output = internalOutput(args[2]);
                Files.createDirectory(output);
                for (JsonNode original : MAPPER.readTree(Path.of(args[1]).toFile())) {
                    AnalysisContext context = fromFrozenLegacy(original.path("context_json"));
                    String gameId = safeId(original.path("game_id").asText());
                    write(output.resolve(gameId + ".json"), MAPPER.readTree(context.canonicalJson()));
                }
                return 0;
            }
            boolean replay = args.length == 5 && args[0].equals("replay");
            boolean resume = args.length == 4 && args[0].equals("resume");
            if (!(args.length == 4 && args[0].equals("generate")) && !replay && !resume)
                throw new IllegalArgumentException("Invalid evaluation command");
            if (!Set.of("development", "holdout").contains(args[2])) throw new IllegalArgumentException("Invalid split");
            Path manifest = Path.of(args[1]).toAbsolutePath();
            JsonNode cases = MAPPER.readTree(manifest.toFile());
            List<JsonNode> selected = new ArrayList<>();
            for (JsonNode item : cases.path("cases")) if (item.path("split").asText().equals(args[2])) selected.add(item);
            if (selected.isEmpty() || selected.size() > 6) throw new IllegalArgumentException("Expected 1..6 cases");
            Path output = internalOutput(args[3]);
            if (resume) {
                if (!Files.isRegularFile(output.resolve("run.json"))) throw new IllegalArgumentException("Missing prior run");
                selected.removeIf(item -> Files.exists(output.resolve(safeId(item.path("gameId").asText()))));
                if (selected.isEmpty()) throw new IllegalArgumentException("No unattempted cases");
            } else Files.createDirectory(output); // Never overwrite a prior run, including failed attempts.
            String apiKey = System.getenv().getOrDefault("GEMINI_API_KEY", "");
            if (!replay && apiKey.isBlank()) throw new IllegalArgumentException("Missing GEMINI_API_KEY");
            GeminiGateway gateway = replay ? null : new GeminiClient(apiKey,
                    "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent", Duration.ofSeconds(180));
            ObjectNode run = MAPPER.createObjectNode().put("startedAt", Instant.now().toString())
                    .put("mode", replay ? "REPLAY" : "LIVE").put("model", MODEL)
                    .put("promptVersion", PromptCatalog.VERSION).put("split", args[2])
                    .put("manifestSha256", sha256(Files.readString(manifest)))
                    .put("publicationApproved", false);
            run.set("manifest", cases);
            run.put("systemPrompt", PromptCatalog.SYSTEM);
            run.set("generationConfig", MAPPER.valueToTree(GeminiRequest.GenerationConfig.editorial()));
            write(output.resolve(resume ? "resume-" + Instant.now().toEpochMilli() + ".json" : "run.json"), run);
            int failures = 0;
            for (JsonNode item : selected) {
                String id = safeId(item.path("gameId").asText());
                Path caseDir = output.resolve(id);
                Files.createDirectory(caseDir);
                AnalysisContext context = fromV3(MAPPER.readTree(manifest.getParent().resolve(item.path("context").asText()).toFile()));
                if (!MAPPER.readTree(context.canonicalJson()).path("game").path("game_id").asText().equals(id))
                    throw new IllegalArgumentException("Context game mismatch");
                AnalysisDepth depth = AnalysisDepth.valueOf(item.path("depth").asText());
                String user = context.canonicalJson() + "\n\n" + PromptCatalog.instruction(depth);
                write(caseDir.resolve("context.json"), MAPPER.readTree(context.canonicalJson()));
                Files.writeString(caseDir.resolve("user-prompt.txt"), user, StandardOpenOption.CREATE_NEW);
                String raw;
                if (replay) {
                    if (!Files.isRegularFile(Path.of(args[4]).resolve(id).resolve("response-original.txt"))) {
                        write(caseDir.resolve("result.json"), MAPPER.createObjectNode().put("status", "NO_RESPONSE_TO_REPLAY"));
                        failures++;
                        continue;
                    }
                    raw = Files.readString(Path.of(args[4]).resolve(id).resolve("response-original.txt"));
                } else {
                    write(caseDir.resolve("attempt.json"), MAPPER.createObjectNode()
                            .put("startedAt", Instant.now().toString()).put("model", MODEL)
                            .put("contextSha256", sha256(context.canonicalJson()))
                            .put("userPromptSha256", sha256(user))
                            .put("systemPromptSha256", sha256(PromptCatalog.SYSTEM))
                            .put("retryPolicy", "NONE; every attempted call consumes the authorized budget"));
                    try { raw = gateway.generateAnalysis(PromptCatalog.SYSTEM, user); }
                    catch (RuntimeException failure) {
                        ObjectNode failed = MAPPER.createObjectNode().put("status", "GENERATION_FAILED")
                                .put("category", GenerationFailure.classify(failure).name());
                        if (failure instanceof GenerationFailure known) {
                            failed.set("diagnosticTypes", MAPPER.valueToTree(known.diagnosticTypes()));
                            if (known.httpStatus() != null) failed.put("httpStatus", known.httpStatus());
                        }
                        write(caseDir.resolve("result.json"), failed);
                        failures++;
                        System.out.println(id + " GENERATION_FAILED " + GenerationFailure.classify(failure));
                        break; // Stop the batch on transport failure; never spend remaining calls blindly.
                    }
                }
                if (!recordResponse(caseDir, raw, context)) failures++;
            }
            return failures == 0 ? 0 : 1;
        } catch (Exception failure) {
            System.err.println("Evaluation failed: " + failure.getClass().getSimpleName());
            return 1;
        }
    }

    public static boolean recordResponse(Path directory, String raw, AnalysisContext context) throws java.io.IOException {
        Files.writeString(directory.resolve("response-original.txt"), raw, StandardOpenOption.CREATE_NEW);
        ObjectNode result = MAPPER.createObjectNode().put("responseSha256", sha256(raw))
                .put("contextSha256", sha256(context.canonicalJson())).put("publicationApproved", false);
        boolean accepted;
        try {
            JsonNode root = MAPPER.readTree(raw);
            if (root != null && root.has("claims")) write(directory.resolve("claims.json"), root.path("claims"));
            JsonNode rendered = new ClaimRenderer(MAPPER).render(root, context);
            write(directory.resolve("rendered.json"), rendered);
            result.put("status", "VALIDATED");
            accepted = true;
        } catch (RuntimeException | com.fasterxml.jackson.core.JsonProcessingException failure) {
            result.put("status", "REJECTED").put("category", GenerationFailure.classify(failure).name());
            accepted = false;
        }
        write(directory.resolve("result.json"), result);
        System.out.println(directory.getFileName() + " " + result.path("status").asText() + " " + result.path("category").asText());
        return accepted;
    }

    /** Convert only the stored observations. No current DB lookup, imputation or historical replacement. */
    public static AnalysisContext fromFrozenLegacy(JsonNode original) throws java.io.IOException {
        List<Evidence> evidence = new ArrayList<>();
        int season = original.path("game").path("season").asInt();
        int week = original.path("game").path("week").asInt();
        String home = original.path("home_team").path("abbr").asText();
        String away = original.path("away_team").path("abbr").asText();
        for (String side : List.of("home_team", "away_team")) {
            JsonNode team = original.path(side);
            boolean historical = team.path("historical_reference").asBoolean();
            for (JsonNode row : team.path("recent_form_last_3_eligible_weeks")) {
                TeamWeekMetrics metrics = MAPPER.treeToValue(row, TeamWeekMetrics.class);
                var key = metrics.getId();
                if (!key.getTeamAbbr().equals(team.path("abbr").asText())
                        || (!historical && (key.getSeason() != season || key.getWeek() >= week))
                        || (historical && key.getSeason() >= season))
                    throw new IllegalArgumentException("Frozen temporal or team mismatch");
                for (MetricCatalog metric : MetricCatalog.values()) if (metric.value(metrics) != null)
                    evidence.add(Evidence.observed(key.getTeamAbbr(), metric, key.getSeason(), key.getWeek(),
                            historical, metric.value(metrics), metric.volume(metrics)));
            }
        }
        evidence.sort(Comparator.comparing(Evidence::id));
        ObjectNode out = MAPPER.createObjectNode().put("contract_version", 3);
        out.set("game", original.path("game"));
        out.put("home_team", home).put("away_team", away);
        ContextQuality quality = ContextQuality.valueOf(original.path("context_quality").asText());
        out.put("data_coverage", quality.name());
        out.set("evidence", MAPPER.valueToTree(evidence));
        out.set("recent_windows", MAPPER.valueToTree(EvidenceWindow.from(evidence)));
        out.put("window_policy", "FROZEN_ORIGINAL_OBSERVATIONS_ONLY; no refresh, imputation or opponent adjustment");
        out.set("data_limitations", original.path("data_limitations"));
        return new AnalysisContext(MAPPER.writeValueAsString(out), quality, List.copyOf(evidence), home, away);
    }

    private static AnalysisContext fromV3(JsonNode root) throws java.io.IOException {
        List<Evidence> evidence = new ArrayList<>();
        for (JsonNode item : root.path("evidence")) evidence.add(MAPPER.treeToValue(item, Evidence.class));
        // Rebuild windows from evidence; never trust editable derived values sent to the model.
        ((ObjectNode) root).set("recent_windows", MAPPER.valueToTree(EvidenceWindow.from(evidence)));
        return new AnalysisContext(MAPPER.writeValueAsString(root), ContextQuality.valueOf(root.path("data_coverage").asText()),
                List.copyOf(evidence), root.path("home_team").asText(), root.path("away_team").asText());
    }

    private static String safeId(String value) {
        if (!value.matches("[A-Za-z0-9_-]+")) throw new IllegalArgumentException("Invalid case id");
        return value;
    }
    private static Path internalOutput(String value) throws java.io.IOException {
        Path output = Path.of(value).toAbsolutePath().normalize();
        Path parent = output.getParent().toRealPath();
        for (Path part : parent) if (part.toString().equals("public")) throw new IllegalArgumentException("Public output forbidden");
        return parent.resolve(output.getFileName());
    }
    private static void write(Path path, JsonNode value) throws java.io.IOException {
        Files.writeString(path, MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(value) + "\n", StandardOpenOption.CREATE_NEW);
    }
    private static String sha256(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))); }
        catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }
}
