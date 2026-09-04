package com.nflsideline.coreapi.service;

import com.nflsideline.coreapi.domain.Team;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.repository.TeamRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;

@Service
public class TeamService {

    private static final int WINDOW_L4 = 4;
    private static final int WINDOW_L6 = 6;

    private final TeamRepository teamRepository;
    private final TeamWeekMetricsRepository metricsRepository;

    public TeamService(TeamRepository teamRepository, TeamWeekMetricsRepository metricsRepository) {
        this.teamRepository = teamRepository;
        this.metricsRepository = metricsRepository;
    }

    public List<Team> findAll() {
        return teamRepository.findAll(Sort.by("teamName"));
    }

    public boolean existsByAbbr(String abbr) {
        return teamRepository.existsById(abbr);
    }

    /**
     * Métricas semanais de um time em uma temporada.
     *
     * @param window "season" retorna todas as semanas; "l4"/"l6" retornam as
     *               últimas 4/6 semanas com dados registrados.
     */
    public List<TeamWeekMetrics> findTeamMetrics(String abbr, Integer season, String window) {
        List<TeamWeekMetrics> metrics;
        switch (window) {
            case "season" -> metrics = metricsRepository
                    .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(season, abbr);
            case "l4" -> metrics = findLastWeeks(season, abbr, WINDOW_L4);
            case "l6" -> metrics = findLastWeeks(season, abbr, WINDOW_L6);
            default -> throw new IllegalArgumentException("window inválido: use season, l4 ou l6");
        }
        return metrics;
    }

    private List<TeamWeekMetrics> findLastWeeks(Integer season, String abbr, int n) {
        List<TeamWeekMetrics> latest = metricsRepository
                .findByIdSeasonAndIdTeamAbbrOrderByIdWeekDesc(season, abbr, PageRequest.of(0, n));
        Collections.reverse(latest); // retorna em ordem cronológica ascendente
        return latest;
    }
}
