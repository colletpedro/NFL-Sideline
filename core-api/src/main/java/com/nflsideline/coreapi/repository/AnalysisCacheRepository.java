package com.nflsideline.coreapi.repository;

import com.nflsideline.coreapi.domain.AnalysisCache;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface AnalysisCacheRepository extends JpaRepository<AnalysisCache, Long> {

    Optional<AnalysisCache> findByGameIdAndAnalysisTypeAndPromptHash(
            String gameId, String analysisType, String promptHash);

    @Query("SELECT a FROM AnalysisCache a "
            + "WHERE a.analysisType = 'matchup' AND a.gameId IN :gameIds "
            + "ORDER BY a.gameId ASC, a.createdAt DESC, a.id DESC")
    List<AnalysisCache> findMatchupsForGameIds(@Param("gameIds") List<String> gameIds);

    Optional<AnalysisCache> findFirstByGameIdAndAnalysisTypeOrderByCreatedAtDescIdDesc(
            String gameId, String analysisType);
}
