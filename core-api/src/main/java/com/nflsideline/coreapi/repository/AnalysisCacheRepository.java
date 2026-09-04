package com.nflsideline.coreapi.repository;

import com.nflsideline.coreapi.domain.AnalysisCache;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AnalysisCacheRepository extends JpaRepository<AnalysisCache, Long> {

    Optional<AnalysisCache> findByGameIdAndAnalysisTypeAndPromptHash(
            String gameId, String analysisType, String promptHash);
}
