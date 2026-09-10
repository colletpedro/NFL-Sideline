package com.nflsideline.coreapi.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.Arrays;
import java.util.Locale;

@Configuration
public class ApiSecurityConfiguration implements WebMvcConfigurer {

    static final int MIN_SHARED_TOKEN_LENGTH = 32;

    private final AppEnvironment appEnvironment;
    private final String sharedToken;
    private final String[] localAllowedOrigins;

    public ApiSecurityConfiguration(
            @Value("${app.env:}") String appEnvironment,
            @Value("${app.core-api-shared-token:}") String sharedToken,
            @Value("${app.cors.allowed-origins:http://localhost:5173,http://127.0.0.1:5173}")
            String allowedOrigins) {
        this.appEnvironment = AppEnvironment.from(appEnvironment);
        this.sharedToken = sharedToken == null ? "" : sharedToken.trim();
        this.localAllowedOrigins = Arrays.stream(allowedOrigins.split(","))
                .map(String::trim)
                .filter(origin -> !origin.isEmpty())
                .toArray(String[]::new);

        if (requiresAuthentication() && this.sharedToken.length() < MIN_SHARED_TOKEN_LENGTH) {
            throw new IllegalStateException(
                    "CORE_API_SHARED_TOKEN must contain at least 32 characters when APP_ENV is preview or production");
        }
    }

    @Bean
    public ApiSecurityFilter apiSecurityFilter() {
        return new ApiSecurityFilter(requiresAuthentication(), sharedToken);
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        if (!requiresAuthentication() && localAllowedOrigins.length > 0) {
            registry.addMapping("/api/v1/**")
                    .allowedOrigins(localAllowedOrigins)
                    .allowedMethods("GET", "POST", "OPTIONS")
                    .allowedHeaders("Content-Type")
                    .allowCredentials(false)
                    .maxAge(3600);
        }
    }

    private boolean requiresAuthentication() {
        return appEnvironment != AppEnvironment.LOCAL;
    }

    private enum AppEnvironment {
        LOCAL,
        PREVIEW,
        PRODUCTION;

        static AppEnvironment from(String rawValue) {
            String normalized = rawValue == null ? "" : rawValue.trim().toUpperCase(Locale.ROOT);
            try {
                return AppEnvironment.valueOf(normalized);
            } catch (IllegalArgumentException exception) {
                throw new IllegalStateException(
                        "APP_ENV must be explicitly set to local, preview, or production");
            }
        }
    }
}
