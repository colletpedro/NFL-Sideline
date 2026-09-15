package com.nflsideline.coreapi.controller;

import com.nflsideline.coreapi.service.AnalysisService;
import com.nflsideline.coreapi.service.dto.AnalysisRequest;
import com.nflsideline.coreapi.service.dto.AnalysisResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Profile("!snapshot")
@RequestMapping("/api/v1")
public class AnalysisController {

    private final AnalysisService analysisService;

    public AnalysisController(AnalysisService analysisService) {
        this.analysisService = analysisService;
    }

    @PostMapping("/analysis/matchup")
    public ResponseEntity<?> generateMatchupAnalysis(@RequestBody @Valid AnalysisRequest request) {
        try {
            return ResponseEntity.ok(analysisService.generateMatchupAnalysis(request));
        } catch (IllegalArgumentException ex) {
            ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST,
                    "Unsupported analysis type or ineligible editorial window");
            problem.setTitle("Invalid analysis request");
            return ResponseEntity.badRequest().body(problem);
        } catch (IllegalStateException ex) {
            // Falha de LLM (timeout, resposta malformada ou alucinação detectada):
            // degradação graciosa — 503 sem derrubar a aplicação.
            ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, ex.getMessage());
            problem.setTitle("LLM Failure");
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(problem);
        }
    }

    @GetMapping("/analysis/matchup/{gameId}")
    public ResponseEntity<AnalysisResponse> getCachedMatchupAnalysis(@PathVariable String gameId) {
        return analysisService.findLatestCachedMatchup(gameId)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
