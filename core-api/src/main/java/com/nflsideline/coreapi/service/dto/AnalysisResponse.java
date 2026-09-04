package com.nflsideline.coreapi.service.dto;

public record AnalysisResponse(String gameId, String markdownText, boolean fromCache) {
}