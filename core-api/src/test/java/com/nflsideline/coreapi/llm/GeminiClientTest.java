package com.nflsideline.coreapi.llm;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.llm.dto.GeminiRequest;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.http.MediaType;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.convert.DurationStyle;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.env.MapPropertySource;
import org.springframework.beans.factory.config.YamlPropertiesFactoryBean;
import org.springframework.core.io.ClassPathResource;
import org.springframework.web.client.RestClientResponseException;
import java.net.SocketTimeoutException;
import java.time.Duration;
import java.util.Map;
import static org.assertj.core.api.Assertions.*;

class GeminiClientTest {
    @Test void classifiesWithoutRetainingRemoteDetails() throws Exception {
        int[] statuses = {400,401,403,404,429,500,503,418};
        String[] categories = {"HTTP_400","HTTP_401","HTTP_403","HTTP_404","HTTP_429","HTTP_5XX","HTTP_5XX","UNKNOWN"};
        for (int i=0; i<statuses.length; i++) {
            var remote = new RestClientResponseException("SECRET", statuses[i], "SECRET", null, "SECRET".getBytes(), null);
            var safe = new GenerationFailure(GenerationFailure.classify(new RuntimeException(remote)));
            assertThat(safe.getMessage()).isEqualTo(categories[i]);
            assertThat(safe.getCause()).isNull();
        }
        assertThat(GenerationFailure.classify(new RuntimeException(new SocketTimeoutException("SECRET"))))
                .isEqualTo(GenerationFailure.Category.TIMEOUT);
        for (var category : GenerationFailure.Category.values())
            assertThat(GenerationFailure.classify(new GenerationFailure(category))).isEqualTo(category);
        assertThat(GenerationFailure.classify(new RuntimeException("SECRET"))).isEqualTo(GenerationFailure.Category.UNKNOWN);
    }

    @Test void structuredSchemaRequiresEditorialFieldsAndScalarCitations() throws Exception {
        var schema = new ObjectMapper().valueToTree(GeminiRequest.GenerationConfig.editorial());
        assertThat(schema.path("responseMimeType").asText()).isEqualTo("application/json");
        var json = schema.path("responseJsonSchema");
        assertThat(json.path("required").size()).isEqualTo(5);
        for (String key : new String[]{"fator_chave","vantagem_tatica","alerta_vermelho","veredito"}) {
            assertThat(json.path("properties").path(key).path("minLength").asInt()).isEqualTo(1);
        }
        assertThat(json.path("properties").path("metricas_citadas").path("additionalProperties").path("type").asText()).isEqualTo("number");
    }

    @Test void collectsAllNonemptyTextPartsAndClassifiesBadResponses() throws Exception {
        assertThat(call("{\"candidates\":[{\"content\":{\"parts\":[{\"text\":\"{\"},{},{\"text\":\" \"},{\"text\":\"}末\"}]}}]}"))
                .isEqualTo("{}末");
        assertThatThrownBy(() -> call("{\"candidates\":[]}")).hasMessage("EMPTY_RESPONSE");
        assertThatThrownBy(() -> call("not json")).hasMessage("INVALID_JSON");
    }

    private String call(String body) throws Exception {
        var builder = RestClient.builder();
        var server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://example.test/generate"))
                .andRespond(withSuccess(body, MediaType.APPLICATION_JSON));
        var client = new GeminiClient("fake", "https://example.test/generate", Duration.ofSeconds(2));
        ReflectionTestUtils.setField(client, "restClient", builder.build());
        try { return client.generateAnalysis("system", "user"); }
        finally { server.verify(); }
    }

    @Test void timeoutDefaultAndEnvironmentOverride() throws Exception {
        var yaml = new YamlPropertiesFactoryBean();
        yaml.setResources(new ClassPathResource("application.yml"));
        String configured = yaml.getObject().getProperty("gemini.timeout");
        var environment = new StandardEnvironment();
        environment.getPropertySources().remove("systemEnvironment");
        assertThat(DurationStyle.detectAndParse(environment.resolveRequiredPlaceholders(configured))).isEqualTo(Duration.ofSeconds(180));
        environment.getPropertySources().addFirst(new MapPropertySource("override", Map.of("GEMINI_TIMEOUT", "7s")));
        assertThat(DurationStyle.detectAndParse(environment.resolveRequiredPlaceholders(configured))).isEqualTo(Duration.ofSeconds(7));
        assertThat(GeminiClient.class.getConstructors()[0].getParameters()[2].getAnnotation(Value.class).value()).isEqualTo("${gemini.timeout:180s}");
    }
}
