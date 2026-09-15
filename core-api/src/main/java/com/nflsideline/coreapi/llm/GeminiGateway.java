package com.nflsideline.coreapi.llm;

public interface GeminiGateway {
    String generateAnalysis(String systemPrompt, String userPrompt);
}
