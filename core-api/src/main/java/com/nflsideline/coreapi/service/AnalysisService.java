package com.nflsideline.coreapi.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.MarketImplied;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.llm.GeminiClient;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.repository.MarketImpliedRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import com.nflsideline.coreapi.service.dto.AnalysisRequest;
import com.nflsideline.coreapi.service.dto.AnalysisResponse;
import jakarta.persistence.EntityNotFoundException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class AnalysisService {

    private static final String MODEL_NAME = "gemini-3.1-pro-preview";

    /** Tolerância de arredondamento da validação anti-alucinação (spec §9: 0.01). */
    private static final double NUMERIC_TOLERANCE = 0.01;

    /** Chaves do objeto preditivo exigido do LLM (contrato da Fase 9). */
    private static final List<String> PREDICTION_KEYS =
            List.of("fator_chave", "vantagem_tatica", "alerta_vermelho", "veredito");

    private static final Logger LOGGER = LoggerFactory.getLogger(AnalysisService.class);

    private static final String SYSTEM_PROMPT = "Você é um analista PREDITIVO da NFL. Responda ESTRITAMENTE em JSON "
            + "com EXATAMENTE estas chaves: 'fator_chave' (texto direto sobre a métrica principal que define o "
            + "confronto), 'vantagem_tatica' (qual time leva a melhor no confronto de setores), 'alerta_vermelho' "
            + "(o maior risco ou tendência de previsibilidade), 'veredito' (previsão final direta) e "
            + "'metricas_citadas' (objeto chave-valor apenas com os números exatos que você mencionou). "
            + "Nunca cite dados fora do contexto fornecido.";

    private final GameRepository gameRepository;
    private final TeamWeekMetricsRepository metricsRepository;
    private final MarketImpliedRepository marketRepository;
    private final AnalysisCacheRepository cacheRepository;
    private final GeminiClient geminiClient;
    private final ObjectMapper objectMapper;

    public AnalysisService(GameRepository gameRepository,
                           TeamWeekMetricsRepository metricsRepository,
                           MarketImpliedRepository marketRepository,
                           AnalysisCacheRepository cacheRepository,
                           GeminiClient geminiClient,
                           ObjectMapper objectMapper) {
        this.gameRepository = gameRepository;
        this.metricsRepository = metricsRepository;
        this.marketRepository = marketRepository;
        this.cacheRepository = cacheRepository;
        this.geminiClient = geminiClient;
        this.objectMapper = objectMapper;
    }

    public AnalysisResponse generateMatchupAnalysis(AnalysisRequest request) {
        // 1. Coleta de contexto
        Game game = gameRepository.findById(request.gameId())
                .orElseThrow(() -> new EntityNotFoundException("Jogo não encontrado: " + request.gameId()));
        MarketImplied market = marketRepository.findById(request.gameId()).orElse(null);
        List<TeamWeekMetrics> homeMetrics = metricsRepository
                .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(game.getSeason(), game.getHomeTeam().getTeamAbbr());
        List<TeamWeekMetrics> awayMetrics = metricsRepository
                .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(game.getSeason(), game.getAwayTeam().getTeamAbbr());

        // 2. Construção do JSON de contexto (única fonte factual)
        Map<String, Object> contextMap = new LinkedHashMap<>();
        contextMap.put("game_id", game.getGameId());
        contextMap.put("season", game.getSeason());
        contextMap.put("week", game.getWeek());
        contextMap.put("gameday", game.getGameday());
        contextMap.put("home_team", Map.of("abbr", game.getHomeTeam().getTeamAbbr(), "metricas_semanais", homeMetrics));
        contextMap.put("away_team", Map.of("abbr", game.getAwayTeam().getTeamAbbr(), "metricas_semanais", awayMetrics));
        contextMap.put("mercado", market != null ? market : Map.of());
        contextMap.put("odds", oddsOf(game));
        String contextJson = toJson(contextMap);

        // 3. Prompts
        String userPrompt = contextJson + "\n\n" + instructionFor(request.analysisType());

        // 4. Cache (SHA-256 do prompt completo)
        String promptHash = sha256(SYSTEM_PROMPT + userPrompt);
        AnalysisResponse cached = cacheRepository
                .findByGameIdAndAnalysisTypeAndPromptHash(request.gameId(), request.analysisType(), promptHash)
                .map(c -> new AnalysisResponse(c.getGameId(), c.getResponseText(), true))
                .orElse(null);
        if (cached != null) {
            return cached;
        }

        // 5. Chamada LLM
        String llmOutput = geminiClient.generateAnalysis(SYSTEM_PROMPT, userPrompt);

        // 6. Parse, validação numérica (anti-alucinação) e extração do objeto preditivo
        JsonNode llmRoot = parseLlmResponse(llmOutput);
        validateCitedNumbers(llmRoot, contextJson);
        JsonNode prediction = extractPredictionObject(llmRoot);
        String responseText = writeJson(prediction);

        // 7. Persistência (apenas o objeto preditivo validado é armazenado)
        try {
            cacheRepository.save(AnalysisCache.builder()
                    .gameId(request.gameId())
                    .analysisType(request.analysisType())
                    .promptHash(promptHash)
                    .contextJson(contextJson)
                    .responseText(responseText)
                    .modelName(MODEL_NAME)
                    .build());
        } catch (DataIntegrityViolationException e) {
            // Requisição concorrente idêntica já persistiu a mesma análise (mesma chave
            // game_id + analysis_type + prompt_hash): devolve o que já está no cache.
            return cacheRepository
                    .findByGameIdAndAnalysisTypeAndPromptHash(request.gameId(), request.analysisType(), promptHash)
                    .map(c -> new AnalysisResponse(c.getGameId(), c.getResponseText(), true))
                    .orElseGet(() -> new AnalysisResponse(request.gameId(), responseText, false));
        }

        return new AnalysisResponse(request.gameId(), responseText, false);
    }

    private JsonNode parseLlmResponse(String llmOutput) {
        try {
            return objectMapper.readTree(llmOutput);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Falha ao interpretar a resposta do LLM", e);
        }
    }

    /**
     * Extrai o objeto preditivo do contrato da Fase 9 (fator_chave,
     * vantagem_tatica, alerta_vermelho, veredito) da resposta do LLM e o
     * devolve sem as chaves auxiliares (ex.: metricas_citadas, usada apenas
     * na validação numérica). O objeto pode estar no nível raiz ou aninhado.
     */
    private JsonNode extractPredictionObject(JsonNode root) {
        JsonNode target = root.isObject() && root.has("fator_chave") ? root : findPredictionObject(root);
        if (target == null || !target.isObject()) {
            LOGGER.warn("Resposta do LLM sem objeto preditivo: {}", truncate(String.valueOf(root), 2000));
            throw new IllegalStateException("Resposta do LLM sem objeto preditivo");
        }
        ObjectNode out = objectMapper.createObjectNode();
        for (String key : PREDICTION_KEYS) {
            JsonNode value = target.get(key);
            if (value == null || value.isNull() || value.asText("").trim().isEmpty()) {
                throw new IllegalStateException("Resposta do LLM incompleta: chave ausente '" + key + "'");
            }
            out.set(key, value);
        }
        return out;
    }

    /** Busca recursivamente o objeto preditivo (com fator_chave + vantagem_tatica). */
    private JsonNode findPredictionObject(JsonNode node) {
        if (node == null) {
            return null;
        }
        if (node.isObject()) {
            if (node.has("fator_chave") && node.has("vantagem_tatica")) {
                return node;
            }
            Iterator<JsonNode> children = node.elements();
            while (children.hasNext()) {
                JsonNode found = findPredictionObject(children.next());
                if (found != null) {
                    return found;
                }
            }
        }
        return null;
    }

    private String writeJson(JsonNode node) {
        try {
            return objectMapper.writeValueAsString(node);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Falha ao serializar a resposta do LLM", e);
        }
    }

    private Map<String, Object> oddsOf(Game game) {
        Map<String, Object> odds = new LinkedHashMap<>();
        odds.put("spread_line", game.getSpreadLine());
        odds.put("total_line", game.getTotalLine());
        odds.put("home_moneyline", game.getHomeMoneyline());
        odds.put("away_moneyline", game.getAwayMoneyline());
        return odds;
    }

    private String instructionFor(String analysisType) {
        String type = analysisType == null ? "" : analysisType.trim();
        return switch (type) {
            case "matchup" -> "Este confronto AINDA VAI ACONTECER. Com base ESTRITAMENTE no contexto acima, monte a "
                    + "previsão em português: 'fator_chave' destaca a métrica passada (ex.: off_epa_pass, "
                    + "off_epa_rush, dropback_rate) que mais define o jogo; 'vantagem_tatica' indica qual time "
                    + "leva a melhor no confronto de setores, projetando como a eficiência aérea vs terrestre de "
                    + "cada ataque se contrapõe à defesa adversária; 'alerta_vermelho' aponta o maior risco ou a "
                    + "tendência de previsibilidade (ex.: dropback alto) que pode ser explorada; 'veredito' é a "
                    + "previsão final direta do vencedor.";
            default -> "Com base ESTRITAMENTE no contexto acima, escreva a análise solicitada para este jogo em "
                    + "português, com os blocos Panorama, Análise e Fechamento.";
        };
    }

    private String sha256(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 indisponível no runtime", e);
        }
    }

    private static String truncate(String value, int max) {
        return value != null && value.length() > max ? value.substring(0, max) + "…" : value;
    }

    private String toJson(Map<String, Object> contextMap) {
        try {
            return objectMapper.writeValueAsString(contextMap);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Falha ao serializar o contexto para JSON", e);
        }
    }

    /**
     * Anti-alucinação (spec §9): todo número citado pelo LLM em
     * {@code metricas_citadas} deve existir no contexto. A comparação é
     * numérica com tolerância de arredondamento de 0.01 (conforme a spec) —
     * não literal, pois o contexto carrega decimais longos (ex.: EPA por tipo
     * de jogada) e o modelo arredonda ao citar. Um número inventado (sem
     * correspondente no contexto dentro da tolerância) invalida a resposta.
     */
    private void validateCitedNumbers(JsonNode root, String contextJson) {
        JsonNode cited = root.path("metricas_citadas");
        if (!cited.isObject()) {
            return; // nenhum número citado, nada a validar
        }
        JsonNode contextNode = parseLlmResponse(contextJson);
        List<Double> contextNumbers = new ArrayList<>();
        collectNumbers(contextNode, contextNumbers);

        Iterator<Map.Entry<String, JsonNode>> fields = cited.fields();
        while (fields.hasNext()) {
            JsonNode value = fields.next().getValue();
            if (!value.isNumber()) {
                continue;
            }
            double citedNumber = value.doubleValue();
            boolean foundInContext = contextNumbers.stream()
                    .anyMatch(contextNumber -> Math.abs(contextNumber - citedNumber) <= NUMERIC_TOLERANCE);
            if (!foundInContext) {
                throw new IllegalStateException("Validação numérica falhou: número inventado pelo LLM");
            }
        }
    }

    /** Coleta recursivamente todos os nós numéricos do contexto serializado. */
    private void collectNumbers(JsonNode node, List<Double> out) {
        if (node.isNumber()) {
            out.add(node.doubleValue());
        } else if (node.isContainerNode()) {
            node.forEach(child -> collectNumbers(child, out));
        }
    }
}