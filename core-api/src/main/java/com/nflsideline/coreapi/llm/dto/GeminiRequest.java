package com.nflsideline.coreapi.llm.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

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

    public record GenerationConfig(String responseMimeType) {
    }
}