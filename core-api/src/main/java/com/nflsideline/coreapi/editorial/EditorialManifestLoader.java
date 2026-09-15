package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

@Component
@Profile("snapshot")
public class EditorialManifestLoader {
    private static final Pattern SHA256 = Pattern.compile("[0-9a-f]{64}");
    private static final Set<String> FIELDS = Set.of("gameId", "analysisCacheId", "depth", "promptHash",
            "responseHash", "status", "reviewedBy", "reviewedAt", "asOfDate");
    private final ObjectMapper mapper;
    private final Path path;

    @Autowired
    public EditorialManifestLoader(ObjectMapper mapper,
                                   @Value("${app.editorial.manifest:editorial/analysis-selections.json}") String path) {
        this(mapper, Path.of(path));
    }

    public EditorialManifestLoader(ObjectMapper mapper, Path path) {
        this.mapper = mapper;
        this.path = path;
    }

    public LoadResult load() {
        if (!Files.isRegularFile(path)) return LoadResult.rootFailure("manifest_missing");
        try {
            JsonNode root = mapper.readTree(path.toFile());
            if (!root.isObject() || root.path("version").asInt(-1) != 1 || !root.path("selections").isArray()
                    || root.size() != 2) {
                return LoadResult.rootFailure("manifest_invalid");
            }
            List<EditorialManifest.Selection> valid = new ArrayList<>();
            List<String> problems = new ArrayList<>();
            Set<Long> ids = new HashSet<>();
            for (JsonNode node : root.path("selections")) {
                try {
                    EditorialManifest.Selection selection = parse(node);
                    if (!ids.add(selection.analysisCacheId())) throw new IllegalArgumentException();
                    valid.add(selection);
                } catch (RuntimeException failure) {
                    problems.add("invalid_selection");
                }
            }
            return new LoadResult(true, List.copyOf(valid), List.copyOf(problems));
        } catch (IOException | RuntimeException failure) {
            return LoadResult.rootFailure("manifest_unreadable");
        }
    }

    private EditorialManifest.Selection parse(JsonNode node) {
        if (!node.isObject()) throw new IllegalArgumentException();
        Set<String> actual = new HashSet<>();
        node.fieldNames().forEachRemaining(actual::add);
        if (!actual.equals(FIELDS) || !"APPROVED".equals(text(node, "status"))) throw new IllegalArgumentException();
        long cacheId = node.path("analysisCacheId").asLong(0);
        String promptHash = text(node, "promptHash");
        String responseHash = text(node, "responseHash");
        String reviewedBy = text(node, "reviewedBy");
        if (cacheId <= 0 || !SHA256.matcher(promptHash).matches() || !SHA256.matcher(responseHash).matches()
                || reviewedBy.isBlank()) throw new IllegalArgumentException();
        return new EditorialManifest.Selection(text(node, "gameId"), cacheId,
                AnalysisDepth.valueOf(text(node, "depth")), promptHash, responseHash, "APPROVED", reviewedBy,
                OffsetDateTime.parse(text(node, "reviewedAt")), LocalDate.parse(text(node, "asOfDate")));
    }

    private String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        if (value == null || !value.isTextual() || value.textValue().isBlank()) throw new IllegalArgumentException();
        return value.textValue();
    }

    public record LoadResult(boolean validRoot, List<EditorialManifest.Selection> selections, List<String> problems) {
        public static LoadResult rootFailure(String problem) {
            return new LoadResult(false, List.of(), List.of(problem));
        }
    }
}
