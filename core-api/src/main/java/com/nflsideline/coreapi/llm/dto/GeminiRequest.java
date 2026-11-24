package com.nflsideline.coreapi.llm.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * Payload for the Gemini generateContent API.
 * <p>
 * Jackson serializes nested records using their component names, which already
 * match the API's camelCase keys ({@code contents}, {@code generationConfig},
 * {@code responseMimeType}). Only {@code system_instruction} deviates from the
 * Java naming convention and needs an explicit {@link JsonProperty}.
 */
public record GeminiRequest(
        @JsonProperty("system_instruction") SystemInstruction systemInstruction,
        List<Content> contents,
        GenerationConfig generationConfig) {

    public record SystemInstruction(List<Part> parts) {
    }

    public record Content(String role, List<Part> parts) {
    }

    public record Part(String text) {
    }

    public record GenerationConfig(String responseMimeType, Map<String, Object> responseJsonSchema) {
        public static GenerationConfig editorial() {
            Map<String, Object> text = Map.of("type", "string", "minLength", 1);
            Map<String, Object> claim = Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "claim_id", text,
                            "type", Map.of("type", "string", "enum", List.of("OBSERVATION", "COMPARISON", "WINDOW_COMPARISON", "MATCHUP", "LIMITATION")),
                            "subject", text,
                            "predicate", Map.of("type", "string", "enum", List.of("RECORDED", "GREATER_THAN", "LESS_THAN",
                                    "ATTACK_DEFENSE_PROFILE", "POSITIVE_EPA_CONVERGENCE", "NO_DATA", "HISTORICAL_ONLY",
                                    "SMALL_SAMPLE", "LIMITED_WINDOW", "NO_MATCHUP_SUPPORT", "UNEVEN_WINDOWS", "MIXED_SIGNALS", "PARTIAL_DATA")),
                            "period", Map.of("type", "string", "enum", List.of("CURRENT", "HISTORICAL", "NONE")),
                            "evidence_ids", Map.of("type", "array", "items", text),
                            "role", Map.of("type", "string", "enum", List.of("SUPPORT", "COUNTER", "LIMITATION")),
                            "thesis_id", text),
                    "required", List.of("claim_id", "type", "subject", "predicate", "period", "evidence_ids", "role"),
                    "additionalProperties", false);
            Map<String, Object> section = Map.of("type", "array", "items", text, "minItems", 1);
            return new GenerationConfig("application/json", Map.of(
                    "type", "object",
                    "properties", Map.of(
                            "contract_version", Map.of("type", "integer", "enum", List.of(3)),
                            "thesis_team", text,
                            "verdict", Map.of("type", "string", "enum", List.of("INCONCLUSIVE", "SLIGHT_HOME", "SLIGHT_AWAY")),
                            "claims", Map.of("type", "array", "items", claim),
                            "sections", Map.of("type", "object", "properties", Map.of(
                                    "fator_chave", section, "vantagem_tatica", section,
                                    "alerta_vermelho", section, "veredito", section),
                                    "required", List.of("fator_chave", "vantagem_tatica", "alerta_vermelho", "veredito"),
                                    "additionalProperties", false)),
                    "required", List.of("contract_version", "thesis_team", "verdict", "claims", "sections"),
                    "additionalProperties", false));
        }
    }
}
