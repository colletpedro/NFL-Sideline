package com.nflsideline.coreapi.llm.dto;

import java.util.List;

/**
 * Minimal mapping of the Gemini generateContent response tree, enough to
 * extract the generated text from {@code candidates[0].content.parts[0].text}.
 */
public record GeminiResponse(List<Candidate> candidates) {

    public record Candidate(Content content) {
    }

    public record Content(List<Part> parts) {
    }

    public record Part(String text) {
    }
}