package com.nflsideline.coreapi.repository;

import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.domain.TeamWeekMetricsId;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface TeamWeekMetricsRepository extends JpaRepository<TeamWeekMetrics, TeamWeekMetricsId> {

    List<TeamWeekMetrics> findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(Integer season, String teamAbbr);

    List<TeamWeekMetrics> findByIdSeasonAndIdTeamAbbrOrderByIdWeekDesc(Integer season, String teamAbbr, Pageable pageable);
}
