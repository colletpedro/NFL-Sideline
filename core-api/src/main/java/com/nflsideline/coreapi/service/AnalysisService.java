package com.nflsideline.coreapi.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class AnalysisService {

    private static final String MODEL_NAME = "gemini-2.5-flash";

    private static final String SYSTEM_PROMPT = "Você é um analista tático da NFL. Responda ESTRITAMENTE em JSON com duas "
            + "chaves: 'narrativa_markdown' (com Panorama, Análise e Fechamento) e 'metricas_citadas' (um objeto "
            + "chave-valor apenas com os números exatos que você mencionou no texto). Nunca cite dados fora do "
            + "contexto fornecido.";

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

        // 6. Validação numérica (anti-alucinação)
        validateCitedNumbers(llmOutput, contextJson);

        // 7. Persistência
        cacheRepository.save(AnalysisCache.builder()
                .gameId(request.gameId())
                .analysisType(request.analysisType())
                .promptHash(promptHash)
                .contextJson(contextJson)
                .responseText(llmOutput)
                .modelName(MODEL_NAME)
                .build());

        return new AnalysisResponse(request.gameId(), llmOutput, false);
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
            case "matchup" -> "Com base ESTRITAMENTE no contexto acima, escreva uma análise tática do confronto em "
                    + "português, com os blocos Panorama, Análise e Fechamento.";
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

    private String toJson(Map<String, Object> contextMap) {
        try {
            return objectMapper.writeValueAsString(contextMap);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Falha ao serializar o contexto para JSON", e);
        }
    }

    /**
     * Anti-alucinação: todo número citado pelo LLM em {@code metricas_citadas}
     * deve existir literalmente na string {@code contextJson}. Um número
     * inventado invalida a resposta inteira.
     */
    private void validateCitedNumbers(String llmOutput, String contextJson) {
        try {
            JsonNode root = objectMapper.readTree(llmOutput);
            JsonNode cited = root.path("metricas_citadas");
            if (!cited.isObject()) {
                return; // nenhum número citado, nada a validar
            }
            Iterator<Map.Entry<String, JsonNode>> fields = cited.fields();
            while (fields.hasNext()) {
                JsonNode value = fields.next().getValue();
                if (value.isNumber() && !contextJson.contains(value.asText())) {
                    throw new IllegalStateException("Validação numérica falhou: número inventado pelo LLM");
                }
            }
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Falha ao interpretar a resposta do LLM", e);
        }
    }
}