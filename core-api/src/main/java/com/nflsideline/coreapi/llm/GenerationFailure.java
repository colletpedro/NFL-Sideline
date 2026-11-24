package com.nflsideline.coreapi.llm;

import com.fasterxml.jackson.core.JsonProcessingException;
import org.springframework.web.client.RestClientResponseException;
import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import java.util.concurrent.TimeoutException;

/** Safe diagnostic boundary: never retain remote bodies, messages or causes. */
public final class GenerationFailure extends IllegalStateException {
    public enum Category {
        HTTP_400, HTTP_401, HTTP_403, HTTP_404, HTTP_429, HTTP_4XX, HTTP_5XX,
        TIMEOUT, INVALID_JSON, MISSING_FIELDS, INVALID_NUMERIC_CITATIONS, INVALID_REFERENCE,
        FALSE_COMPARISON, INCOMPATIBLE_PREDICATE, EMPTY_RESPONSE, UNKNOWN
    }
    private final Category category;
    private final java.util.List<String> diagnosticTypes;
    private Integer httpStatus;
    public GenerationFailure(Category category) {
        this(category, java.util.List.of());
    }
    private GenerationFailure(Category category, java.util.List<String> diagnosticTypes) {
        super(category.name());
        this.category = category;
        this.diagnosticTypes = java.util.List.copyOf(diagnosticTypes);
    }
    /** Class names only: never retain messages, remote bodies, credentials or causes. */
    public static GenerationFailure sanitized(Throwable failure) {
        var types = new java.util.ArrayList<String>();
        for (Throwable cause = failure; cause != null && types.size() < 8; cause = cause.getCause())
            types.add(cause.getClass().getName());
        var safe = new GenerationFailure(classify(failure), types);
        for (Throwable cause = failure; cause != null; cause = cause.getCause())
            if (cause instanceof RestClientResponseException http) {
                safe.httpStatus = http.getStatusCode().value();
                break;
            }
        return safe;
    }
    public java.util.List<String> diagnosticTypes() { return diagnosticTypes; }
    public Integer httpStatus() { return httpStatus; }
    public static Category classify(Throwable failure) {
        for (Throwable cause = failure; cause != null; cause = cause.getCause()) {
            if (cause instanceof GenerationFailure known) return known.category;
            if (cause instanceof RestClientResponseException http) {
                int status = http.getStatusCode().value();
                if (status >= 500 && status <= 599) return Category.HTTP_5XX;
                return switch (status) {
                    case 400 -> Category.HTTP_400;
                    case 401 -> Category.HTTP_401;
                    case 403 -> Category.HTTP_403;
                    case 404 -> Category.HTTP_404;
                    case 429 -> Category.HTTP_429;
                    default -> status >= 400 && status < 500 ? Category.HTTP_4XX : Category.UNKNOWN;
                };
            }
            if (cause instanceof SocketTimeoutException || cause instanceof HttpTimeoutException
                    || cause instanceof TimeoutException) return Category.TIMEOUT;
            if (cause instanceof JsonProcessingException) return Category.INVALID_JSON;
        }
        return Category.UNKNOWN;
    }
}
