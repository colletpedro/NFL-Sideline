package com.nflsideline.coreapi.repository;

import com.nflsideline.coreapi.domain.IngestionRuns;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IngestionRunsRepository extends JpaRepository<IngestionRuns, Long> {
}
