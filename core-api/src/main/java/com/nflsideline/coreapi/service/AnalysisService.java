package com.nflsideline.coreapi.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.editorial.AnalysisContext;
import com.nflsideline.coreapi.editorial.AnalysisContextBuilder;
import com.nflsideline.coreapi.editorial.AnalysisDepth;
import com.nflsideline.coreapi.editorial.PromptCatalog;
import com.nflsideline.coreapi.editorial.EditorialCandidate;
import com.nflsideline.coreapi.editorial.EditorialPlanner;
import com.nflsideline.coreapi.editorial.EditorialRoundResolver;
import com.nflsideline.coreapi.editorial.Eligibility;
import com.nflsideline.coreapi.llm.GeminiGateway;
import com.nflsideline.coreapi.llm.GenerationFailure;
import static com.nflsideline.coreapi.llm.GenerationFailure.Category.*;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.service.dto.AnalysisRequest;
import com.nflsideline.coreapi.service.dto.AnalysisResponse;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
@Profile("!snapshot")
public class AnalysisService {
    private static final double NUMERIC_TOLERANCE = 0.01;
    private static final List<String> PREDICTION_KEYS =
            List.of("fator_chave", "vantagem_tatica", "alerta_vermelho", "veredito");
    private static final Pattern NUMBER_IN_TEXT = Pattern.compile("(?<![\\p{L}\\d])[-+]?\\d+(?:[.,]\\d+)?%?");

    private final GameRepository gameRepository;
    private final AnalysisCacheRepository cacheRepository;
    private final AnalysisContextBuilder contextBuilder;
    private final GeminiGateway gemini;
    private final ObjectMapper objectMapper;
    private final String modelName;
    private final EditorialPlanner planner = new EditorialPlanner(new EditorialRoundResolver());

    public AnalysisService(GameRepository gameRepository,
                           AnalysisCacheRepository cacheRepository,
                           AnalysisContextBuilder contextBuilder,
                           GeminiGateway gemini,
                           ObjectMapper objectMapper,
                           @Value("${gemini.model:gemini-3.1-pro-preview}") String modelName) {
        this.gameRepository = gameRepository;
        this.cacheRepository = cacheRepository;
        this.contextBuilder = contextBuilder;
        this.gemini = gemini;
        this.objectMapper = objectMapper;
        this.modelName = modelName;
    }

    public AnalysisResponse generateMatchupAnalysis(AnalysisRequest request) {
        AnalysisDepth depth = AnalysisDepth.fromAnalysisType(request.analysisType().trim());
        if (depth == AnalysisDepth.LEGACY_PUBLISHED) {
            throw new IllegalArgumentException("Legacy analyses cannot be generated");
        }
        Game game = gameRepository.findById(request.gameId())
                .orElseThrow(() -> new EntityNotFoundException("Jogo não encontrado: " + request.gameId()));
        EditorialCandidate candidate = planner.plan(
                        gameRepository.findAllBySeasonWithDetails(game.getSeason()), request.asOfDate()).stream()
                .filter(item -> item.game().getGameId().equals(game.getGameId())).findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Game is not eligible for analysis"));
        if (candidate.eligibility() != Eligibility.ELIGIBLE || candidate.depth() != depth) {
            throw new IllegalArgumentException("Game is not eligible for requested analysis type");
        }
        AnalysisContext context = contextBuilder.build(game, request.asOfDate());
        return generatePrepared(game, depth, request.asOfDate(), request.revisionKey(), context);
    }

    public AnalysisResponse generatePrepared(Game game, AnalysisDepth depth, LocalDate asOfDate,
                                             String revisionKey, AnalysisContext context) {
        String hash = promptHash(depth, context.canonicalJson(), asOfDate, revisionKey);
        Optional<AnalysisCache> existing = cacheRepository.findByGameIdAndAnalysisTypeAndPromptHash(
                game.getGameId(), depth.analysisType(), hash);
        if (existing.isPresent()) return response(existing.get(), true);

        String userPrompt = context.canonicalJson() + "\n\n" + PromptCatalog.instruction(depth);
        JsonNode root = parse(gemini.generateAnalysis(PromptCatalog.SYSTEM, userPrompt));
        JsonNode prediction = validateAndExtract(root, context.canonicalJson());
        String responseText = write(prediction);
        AnalysisCache inserted = AnalysisCache.builder().gameId(game.getGameId())
                .analysisType(depth.analysisType()).promptHash(hash).contextJson(context.canonicalJson())
                .responseText(responseText).modelName(modelName).build();
        try {
            inserted = cacheRepository.saveAndFlush(inserted);
        } catch (DataIntegrityViolationException race) {
            return cacheRepository.findByGameIdAndAnalysisTypeAndPromptHash(game.getGameId(), depth.analysisType(), hash)
                    .map(cache -> response(cache, true))
                    .orElseThrow(() -> new IllegalStateException("Concurrent cache insertion failed"));
        }
        return response(inserted, false);
    }

    public Optional<AnalysisResponse> findLatestCachedMatchup(String gameId) {
        return cacheRepository.findFirstByGameIdAndAnalysisTypeInOrderByCreatedAtDescIdDesc(gameId,
                List.of(AnalysisDepth.FULL.analysisType(), AnalysisDepth.BASIC.analysisType()))
                .map(cache -> response(cache, true));
    }

    public String promptHash(AnalysisDepth depth, String canonicalContext, LocalDate asOfDate, String revisionKey) {
        String identity = "type=" + depth.analysisType() + "\nversion=" + PromptCatalog.VERSION
                + "\nmodel=" + modelName + "\nasOfDate=" + asOfDate + "\nrevisionKey=" + revisionKey
                + "\nsystem=" + PromptCatalog.SYSTEM + "\ninstruction=" + PromptCatalog.instruction(depth)
                + "\ncontext=" + canonicalContext;
        return sha256(identity);
    }

    private JsonNode validateAndExtract(JsonNode root, String contextJson) {
        JsonNode target = root;
        if (target == null || !target.isObject()) throw new GenerationFailure(MISSING_FIELDS);
        ObjectNode out = objectMapper.createObjectNode();
        for (String key : PREDICTION_KEYS) {
            JsonNode value = target.get(key);
            if (value == null || !value.isTextual() || value.textValue().trim().isEmpty()) {
                throw new GenerationFailure(MISSING_FIELDS);
            }
            out.set(key, value);
        }
        validateNumbers(target, out, parse(contextJson));
        return out;
    }

    private void validateNumbers(JsonNode target, JsonNode prediction, JsonNode context) {
        List<Double> textNumbers = new ArrayList<>();
        PREDICTION_KEYS.forEach(key -> collectTextNumbers(prediction.path(key).asText(), textNumbers));
        JsonNode cited = target.path("metricas_citadas");
        if (!cited.isObject()) throw new GenerationFailure(MISSING_FIELDS);
        List<Double> contextNumbers = new ArrayList<>();
        collectNumbers(context, contextNumbers);
        List<Double> citedNumbers = new ArrayList<>();
        if (cited.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = cited.fields();
            while (fields.hasNext()) {
                JsonNode value = fields.next().getValue();
                if (!value.isNumber()) throw new GenerationFailure(INVALID_NUMERIC_CITATIONS);
                double number = value.doubleValue();
                if (!contains(contextNumbers, number)) throw new GenerationFailure(INVALID_NUMERIC_CITATIONS);
                citedNumbers.add(number);
            }
        }
        if (textNumbers.stream().anyMatch(number -> !contains(citedNumbers, number))) {
            throw new GenerationFailure(INVALID_NUMERIC_CITATIONS);
        }
    }

    private void collectTextNumbers(String text, List<Double> out) {
        Matcher matcher = NUMBER_IN_TEXT.matcher(text);
        while (matcher.find()) {
            String token = matcher.group();
            String raw = token.replace("%", "").replace(',', '.');
            double number = Double.parseDouble(raw);
            if (raw.matches("\\d{4}") && number >= 1999 && number <= 2100 && !token.endsWith("%")) continue;
            out.add(token.endsWith("%") ? number / 100.0 : number);
        }
    }

    private boolean contains(List<Double> values, double wanted) {
        return values.stream().anyMatch(value -> Math.abs(value - wanted) <= NUMERIC_TOLERANCE);
    }

    private void collectNumbers(JsonNode node, List<Double> out) {
        if (node.isNumber()) out.add(node.doubleValue());
        else if (node.isContainerNode()) node.forEach(child -> collectNumbers(child, out));
    }

    private JsonNode parse(String value) {
        if (value == null || value.isBlank()) throw new GenerationFailure(EMPTY_RESPONSE);
        try {
            JsonNode parsed = objectMapper.reader().with(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
                    .readTree(value);
            if (parsed == null || parsed.isNull()) throw new GenerationFailure(EMPTY_RESPONSE);
            return parsed;
        } catch (JsonProcessingException e) { throw new GenerationFailure(INVALID_JSON); }
    }

    private String write(JsonNode value) {
        try { return objectMapper.writeValueAsString(value); }
        catch (JsonProcessingException e) { throw new IllegalStateException("Unable to serialize analysis", e); }
    }

    private AnalysisResponse response(AnalysisCache cache, boolean fromCache) {
        return new AnalysisResponse(cache.getGameId(), cache.getResponseText(), fromCache);
    }

    private String sha256(String input) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(input.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }
}
