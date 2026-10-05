package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

@Component
@Profile("!snapshot")
public class AnalysisContextBuilder {
    private final TeamWeekMetricsRepository metricsRepository;
    private final ObjectMapper mapper;

    public AnalysisContextBuilder(TeamWeekMetricsRepository metricsRepository, ObjectMapper mapper) {
        this.metricsRepository = metricsRepository;
        this.mapper = mapper;
    }

    public AnalysisContext build(Game game, LocalDate asOfDate) {
        TeamSlice home = slice(game, game.getHomeTeam().getTeamAbbr());
        TeamSlice away = slice(game, game.getAwayTeam().getTeamAbbr());
        List<Evidence> evidence = new ArrayList<>();
        addEvidence(evidence, home);
        addEvidence(evidence, away);
        evidence.sort(Comparator.comparing(Evidence::id));
        boolean homeObserved = evidence.stream().anyMatch(item -> item.team().equals(home.team()));
        boolean awayObserved = evidence.stream().anyMatch(item -> item.team().equals(away.team()));
        ContextQuality coverage = !homeObserved && !awayObserved ? ContextQuality.MINIMAL
                : homeObserved && awayObserved && !home.historical() && !away.historical()
                ? ContextQuality.COMPLETE : ContextQuality.PARTIAL;
        Map<String, Object> gameMap = new LinkedHashMap<>();
        gameMap.put("game_id", game.getGameId());
        gameMap.put("season", game.getSeason());
        gameMap.put("phase", game.getGameType());
        gameMap.put("week", game.getWeek());
        gameMap.put("gameday", game.getGameday() == null ? null : game.getGameday().toString());
        gameMap.put("as_of_date_utc", asOfDate.toString());
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("contract_version", 3);
        context.put("game", gameMap);
        context.put("home_team", home.team());
        context.put("away_team", away.team());
        context.put("data_coverage", coverage.name());
        context.put("evidence", evidence);
        context.put("recent_windows", EvidenceWindow.from(evidence));
        context.put("window_policy", "LAST_THREE_AVAILABLE_TEAM_WEEKS_BEFORE_GAME; metric coverage may differ; no opponent adjustment");
        List<String> limitations = new ArrayList<>();
        if (!homeObserved || !awayObserved) limitations.add("PBP_METRICS_MISSING");
        if (home.historical() || away.historical()) limitations.add("HISTORICAL_REFERENCE_NOT_CURRENT_FORM");
        if (!"REG".equals(game.getGameType())) limitations.add("POSTSEASON_METRIC_CUTOFF_UNVERIFIABLE");
        context.put("data_limitations", limitations);
        try {
            return new AnalysisContext(mapper.writeValueAsString(context), coverage, List.copyOf(evidence),
                    home.team(), away.team());
        } catch (JsonProcessingException failure) {
            throw new IllegalStateException("Failed to serialize tactical context", failure);
        }
    }

    private TeamSlice slice(Game game, String team) {
        boolean postseason = !"REG".equals(game.getGameType());
        List<TeamWeekMetrics> current = postseason ? List.of() : metricsRepository
                .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(game.getSeason(), team).stream()
                .filter(row -> row.getId().getWeek() < game.getWeek()).toList();
        boolean historical = current.isEmpty();
        List<TeamWeekMetrics> selected = historical ? metricsRepository
                .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(game.getSeason() - 1, team) : current;
        // The source key is season/week/team. Duplicate rows cannot increase coverage or support.
        Map<Integer, TeamWeekMetrics> unique = new TreeMap<>();
        for (TeamWeekMetrics row : selected) {
            TeamWeekMetrics prior = unique.putIfAbsent(row.getId().getWeek(), row);
            if (prior != null && !prior.equals(row))
                throw new IllegalStateException("Conflicting weekly metrics for source key");
        }
        List<TeamWeekMetrics> ordered = new ArrayList<>(unique.values());
        return new TeamSlice(team, historical, ordered.subList(Math.max(0, ordered.size() - 3), ordered.size()));
    }

    private void addEvidence(List<Evidence> out, TeamSlice slice) {
        for (TeamWeekMetrics row : slice.rows()) {
            for (MetricCatalog metric : MetricCatalog.values()) {
                var value = metric.value(row);
                if (value != null) out.add(Evidence.observed(slice.team(), metric, row.getId().getSeason(),
                        row.getId().getWeek(), slice.historical(), value, metric.volume(row)));
            }
        }
    }

    private record TeamSlice(String team, boolean historical, List<TeamWeekMetrics> rows) { }
}
