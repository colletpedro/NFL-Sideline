package com.nflsideline.coreapi.service.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.LocalDate;

public record AnalysisRequest(
        @NotBlank(message = "gameId é obrigatório") String gameId,
        @NotBlank(message = "analysisType é obrigatório") String analysisType,
        @NotNull(message = "asOfDate UTC é obrigatório") LocalDate asOfDate,
        @NotBlank(message = "revisionKey é obrigatório") String revisionKey) {
}
