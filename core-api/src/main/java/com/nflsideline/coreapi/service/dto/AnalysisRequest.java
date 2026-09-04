package com.nflsideline.coreapi.service.dto;

import jakarta.validation.constraints.NotBlank;

public record AnalysisRequest(
        @NotBlank(message = "gameId é obrigatório") String gameId,
        @NotBlank(message = "analysisType é obrigatório") String analysisType) {
}