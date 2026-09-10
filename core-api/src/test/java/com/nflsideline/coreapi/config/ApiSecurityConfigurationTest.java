package com.nflsideline.coreapi.config;

import com.nflsideline.coreapi.controller.HealthController;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ApiSecurityConfigurationTest {

    private static final String VALID_TOKEN = "test-token-with-at-least-thirty-two-characters";

    @Test
    void localWithoutTokenStartsAndAcceptsRequests() throws Exception {
        context("local", "").run(context -> assertThat(context).hasNotFailed());

        mockMvc(false, "")
                .perform(get("/api/v1/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void previewWithoutTokenFailsAtStartup() {
        assertStartupFails("preview", "");
    }

    @Test
    void productionWithoutTokenFailsAtStartup() {
        assertStartupFails("production", "");
    }

    @Test
    void missingAppEnvironmentFailsClosed() {
        new ApplicationContextRunner()
                .withUserConfiguration(ApiSecurityConfiguration.class)
                .run(this::assertInvalidEnvironmentFailure);
    }

    @Test
    void emptyAppEnvironmentFailsClosed() {
        context("", VALID_TOKEN).run(this::assertInvalidEnvironmentFailure);
    }

    @Test
    void unknownAppEnvironmentFailsClosed() {
        context("staging", VALID_TOKEN).run(this::assertInvalidEnvironmentFailure);
    }

    @Test
    void shortTokenFailsInPreviewAndProduction() {
        for (String environment : List.of("preview", "production")) {
            assertStartupFails(environment, "too-short");
        }
    }

    @Test
    void validTokenStartsAndProtectsPreviewAndProduction() throws Exception {
        for (String environment : List.of("preview", "production")) {
            context(environment, VALID_TOKEN).run(context -> assertThat(context).hasNotFailed());

            mockMvc(true, VALID_TOKEN)
                    .perform(get("/api/v1/health"))
                    .andExpect(status().isUnauthorized())
                    .andExpect(content().contentTypeCompatibleWith("application/json"))
                    .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
            mockMvc(true, VALID_TOKEN)
                    .perform(get("/api/v1/health")
                            .header(ApiSecurityFilter.SHARED_TOKEN_HEADER, VALID_TOKEN))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.status").value("UP"));
        }
    }

    @Test
    void startupFailureNeverContainsTheTokenValue() {
        String token = "secret-value-that-must-not-appear-in-startup-errors";
        context("unknown", token).run(context -> {
            assertThat(context).hasFailed();
            assertThat(stackTrace(context.getStartupFailure())).doesNotContain(token);
        });
    }

    private ApplicationContextRunner context(String environment, String token) {
        return new ApplicationContextRunner()
                .withUserConfiguration(ApiSecurityConfiguration.class)
                .withPropertyValues(
                        "app.env=" + environment,
                        "app.core-api-shared-token=" + token);
    }

    private void assertStartupFails(String environment, String token) {
        context(environment, token).run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure())
                    .hasRootCauseInstanceOf(IllegalStateException.class)
                    .hasStackTraceContaining("CORE_API_SHARED_TOKEN must contain at least 32 characters");
        });
    }

    private void assertInvalidEnvironmentFailure(
            org.springframework.boot.test.context.assertj.AssertableApplicationContext context) {
        assertThat(context).hasFailed();
        assertThat(context.getStartupFailure())
                .hasRootCauseInstanceOf(IllegalStateException.class)
                .hasStackTraceContaining("APP_ENV must be explicitly set to local, preview, or production");
    }

    private MockMvc mockMvc(boolean authenticationRequired, String token) {
        return MockMvcBuilders.standaloneSetup(new HealthController())
                .addFilters(new ApiSecurityFilter(authenticationRequired, token))
                .build();
    }

    private String stackTrace(Throwable throwable) {
        StringWriter writer = new StringWriter();
        throwable.printStackTrace(new PrintWriter(writer));
        return writer.toString();
    }
}
