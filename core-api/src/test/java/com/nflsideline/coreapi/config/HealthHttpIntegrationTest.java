package com.nflsideline.coreapi.config;

import com.nflsideline.coreapi.controller.HealthController;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(
        classes = HealthHttpIntegrationTest.TestApplication.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {
                "app.env=production",
                "app.core-api-shared-token=integration-test-token-with-at-least-32-characters",
                "spring.autoconfigure.exclude="
                        + "org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration,"
                        + "org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration,"
                        + "org.springframework.boot.autoconfigure.data.jpa.JpaRepositoriesAutoConfiguration"
        })
class HealthHttpIntegrationTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    void protectedHealthEndpointWorksOverHttpWithCorrectToken() {
        HttpHeaders headers = new HttpHeaders();
        headers.set(ApiSecurityFilter.SHARED_TOKEN_HEADER, "integration-test-token-with-at-least-32-characters");

        ResponseEntity<String> response = restTemplate.exchange(
                "/api/v1/health",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).contains("\"status\":\"UP\"");
    }

    @SpringBootConfiguration(proxyBeanMethods = false)
    @EnableAutoConfiguration
    @Import({ApiSecurityConfiguration.class, HealthController.class})
    static class TestApplication {
    }
}
