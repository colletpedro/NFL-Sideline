package com.nflsideline.coreapi.llm;

import com.nflsideline.coreapi.llm.dto.GeminiRequest;
import com.nflsideline.coreapi.llm.dto.GeminiResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.http.client.SimpleClientHttpRequestFactory;

import java.time.Duration;

import java.util.List;

/**
 * Isolated HTTP client for the Gemini generateContent API.
 * <p>
 * Forced structured output: {@code generationConfig.responseMimeType} is
 * hardcoded to {@code application/json}, so the model returns a JSON string.
 */
@Component
@Profile("!snapshot")
public class GeminiClient implements GeminiGateway {

    private final String apiKey;
    private final String url;
    private final RestClient restClient;

    public GeminiClient(@Value("${gemini.api-key}") String apiKey,
                        @Value("${gemini.url}") String url,
                        @Value("${gemini.timeout:180s}") Duration timeout) {
        this.apiKey = apiKey;
        this.url = url;
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(timeout);
        requestFactory.setReadTimeout(timeout);
        this.restClient = RestClient.builder()
                .requestFactory(requestFactory)
                .defaultHeader("Content-Type", MediaType.APPLICATION_JSON_VALUE)
                .build();
    }

    public String generateAnalysis(String systemPrompt, String userPrompt) {
        GeminiRequest request = new GeminiRequest(
                new GeminiRequest.SystemInstruction(List.of(new GeminiRequest.Part(systemPrompt))),
                List.of(new GeminiRequest.Content("user", List.of(new GeminiRequest.Part(userPrompt)))),
                GeminiRequest.GenerationConfig.editorial());

        final GeminiResponse response;
        try {
            response = restClient.post().uri(url).header("x-goog-api-key", apiKey)
                    .body(request).retrieve().body(GeminiResponse.class);
        } catch (RuntimeException failure) {
            throw new GenerationFailure(GenerationFailure.classify(failure));
        }

        if (response == null
                || response.candidates() == null
                || response.candidates().isEmpty()
                || response.candidates().getFirst() == null
                || response.candidates().getFirst().content() == null
                || response.candidates().getFirst().content().parts() == null
                || response.candidates().getFirst().content().parts().isEmpty()) {
            throw new GenerationFailure(GenerationFailure.Category.EMPTY_RESPONSE);
        }

        String text = response.candidates().getFirst().content().parts().stream()
                .filter(java.util.Objects::nonNull).map(GeminiResponse.Part::text)
                .filter(part -> part != null && !part.isBlank())
                .collect(java.util.stream.Collectors.joining());
        if (text.isBlank()) throw new GenerationFailure(GenerationFailure.Category.EMPTY_RESPONSE);
        return text;
    }
}
