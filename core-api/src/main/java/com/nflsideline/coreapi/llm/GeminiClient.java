package com.nflsideline.coreapi.llm;

import com.nflsideline.coreapi.llm.dto.GeminiRequest;
import com.nflsideline.coreapi.llm.dto.GeminiResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.List;

/**
 * Isolated HTTP client for the Gemini generateContent API.
 * <p>
 * Forced structured output: {@code generationConfig.responseMimeType} is
 * hardcoded to {@code application/json}, so the model returns a JSON string.
 */
@Component
public class GeminiClient {

    private final String apiKey;
    private final String url;
    private final RestClient restClient;

    public GeminiClient(@Value("${gemini.api-key}") String apiKey,
                        @Value("${gemini.url}") String url) {
        this.apiKey = apiKey;
        this.url = url;
        this.restClient = RestClient.builder()
                .defaultHeader("Content-Type", MediaType.APPLICATION_JSON_VALUE)
                .build();
    }

    public String generateAnalysis(String systemPrompt, String userPrompt) {
        GeminiRequest request = new GeminiRequest(
                new GeminiRequest.SystemInstruction(List.of(new GeminiRequest.Part(systemPrompt))),
                List.of(new GeminiRequest.Content("user", List.of(new GeminiRequest.Part(userPrompt)))),
                new GeminiRequest.GenerationConfig("application/json"));

        GeminiResponse response = restClient.post()
                .uri(url)
                .header("x-goog-api-key", apiKey)
                .body(request)
                .retrieve()
                .body(GeminiResponse.class);

        if (response == null
                || response.candidates() == null
                || response.candidates().isEmpty()
                || response.candidates().getFirst().content() == null
                || response.candidates().getFirst().content().parts() == null
                || response.candidates().getFirst().content().parts().isEmpty()) {
            throw new IllegalStateException("Resposta do Gemini vazia ou malformada (candidates[0].content.parts[0].text ausente)");
        }

        return response.candidates().getFirst().content().parts().getFirst().text();
    }
}