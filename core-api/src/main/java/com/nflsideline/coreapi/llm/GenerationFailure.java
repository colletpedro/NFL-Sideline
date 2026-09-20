package com.nflsideline.coreapi.llm;

import com.fasterxml.jackson.core.JsonProcessingException;
import org.springframework.web.client.RestClientResponseException;
import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import java.util.concurrent.TimeoutException;

/** Safe diagnostic boundary: never retain remote bodies, messages or causes. */
public final class GenerationFailure extends IllegalStateException {
    public enum Category {
        HTTP_400, HTTP_401, HTTP_403, HTTP_404, HTTP_429, HTTP_5XX,
        TIMEOUT, INVALID_JSON, MISSING_FIELDS, INVALID_NUMERIC_CITATIONS, EMPTY_RESPONSE, UNKNOWN
    }
    private final Category category;
    public GenerationFailure(Category category) {
        super(category.name());
        this.category = category;
    }
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
                    default -> Category.UNKNOWN;
                };
            }
            if (cause instanceof SocketTimeoutException || cause instanceof HttpTimeoutException
                    || cause instanceof TimeoutException) return Category.TIMEOUT;
            if (cause instanceof JsonProcessingException) return Category.INVALID_JSON;
        }
        return Category.UNKNOWN;
    }
}
