package com.nflsideline.coreapi.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.Arrays;

@Configuration
@Profile("!snapshot")
public class LocalCorsConfiguration implements WebMvcConfigurer {

    private final String[] localAllowedOrigins;

    public LocalCorsConfiguration(
            @Value("${app.cors.allowed-origins:http://localhost:5173,http://127.0.0.1:5173}")
            String allowedOrigins) {
        this.localAllowedOrigins = Arrays.stream(allowedOrigins.split(","))
                .map(String::trim)
                .filter(origin -> !origin.isEmpty())
                .toArray(String[]::new);
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        if (localAllowedOrigins.length > 0) {
            registry.addMapping("/api/v1/**")
                    .allowedOrigins(localAllowedOrigins)
                    .allowedMethods("GET", "POST", "OPTIONS")
                    .allowedHeaders("Content-Type")
                    .allowCredentials(false)
                    .maxAge(3600);
        }
    }
}
