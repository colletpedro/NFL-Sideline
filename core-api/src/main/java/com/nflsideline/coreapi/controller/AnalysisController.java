package com.nflsideline.coreapi.controller;

import com.nflsideline.coreapi.service.AnalysisService;
import com.nflsideline.coreapi.service.dto.AnalysisRequest;
import com.nflsideline.coreapi.service.dto.AnalysisResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
@CrossOrigin
public class AnalysisController {

    private final AnalysisService analysisService;

    public AnalysisController(AnalysisService analysisService) {
        this.analysisService = analysisService;
    }

    @PostMapping("/analysis/matchup")
    public ResponseEntity<?> generateMatchupAnalysis(@RequestBody @Valid AnalysisRequest request) {
        try {
            return ResponseEntity.ok(analysisService.generateMatchupAnalysis(request));
        } catch (IllegalStateException ex) {
            // Falha de LLM (timeout, resposta malformada ou alucinação detectada):
            // degradação graciosa — 503 sem derrubar a aplicação.
            ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, ex.getMessage());
            problem.setTitle("LLM Failure");
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(problem);
        }
    }
}