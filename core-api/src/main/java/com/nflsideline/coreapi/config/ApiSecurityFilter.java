package com.nflsideline.coreapi.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

public final class ApiSecurityFilter extends OncePerRequestFilter {

    public static final String SHARED_TOKEN_HEADER = "X-NFL-Sideline-Token";

    private final boolean authenticationRequired;
    private final byte[] expectedTokenDigest;

    public ApiSecurityFilter(boolean authenticationRequired, String sharedToken) {
        this.authenticationRequired = authenticationRequired;
        this.expectedTokenDigest = digest(sharedToken);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return !authenticationRequired
                || !(path.equals("/api/v1") || path.startsWith("/api/v1/"));
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {
        byte[] actualTokenDigest = digest(request.getHeader(SHARED_TOKEN_HEADER));
        if (!MessageDigest.isEqual(expectedTokenDigest, actualTokenDigest)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write("{\"error\":{\"code\":\"UNAUTHORIZED\",\"message\":\"Unauthorized.\"}}");
            return;
        }
        filterChain.doFilter(request, response);
    }

    private static byte[] digest(String value) {
        try {
            return MessageDigest.getInstance("SHA-256")
                    .digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8));
        } catch (java.security.NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable", impossible);
        }
    }
}
