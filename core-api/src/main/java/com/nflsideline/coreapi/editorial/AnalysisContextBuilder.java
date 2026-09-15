package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.MarketImplied;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.repository.MarketImpliedRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
@Profile("!snapshot")
public class AnalysisContextBuilder {
    private final TeamWeekMetricsRepository metricsRepository;
    private final MarketImpliedRepository marketRepository;
    private final ObjectMapper objectMapper;

    public AnalysisContextBuilder(TeamWeekMetricsRepository metricsRepository,
                                  MarketImpliedRepository marketRepository,
                                  ObjectMapper objectMapper) {
        this.metricsRepository = metricsRepository;
        this.marketRepository = marketRepository;
        this.objectMapper = objectMapper;
    }

    public AnalysisContext build(Game game, LocalDate asOfDate) {
        TeamContext home = teamContext(game, game.getHomeTeam().getTeamAbbr());
        TeamContext away = teamContext(game, game.getAwayTeam().getTeamAbbr());
        MarketImplied market = marketRepository.findById(game.getGameId()).orElse(null);
        MarketAvailability marketAvailability = marketAvailability(game, market);
        ContextQuality quality = quality(home, away);

        Map<String, Object> context = new LinkedHashMap<>();
        Map<String, Object> gameContext = new LinkedHashMap<>();
        gameContext.put("game_id", game.getGameId());
        gameContext.put("season", game.getSeason());
        gameContext.put("phase", game.getGameType());
        gameContext.put("week", game.getWeek());
        gameContext.put("gameday", game.getGameday() == null ? null : game.getGameday().toString());
        gameContext.put("as_of_date_utc", asOfDate.toString());
        context.put("game", gameContext);
        context.put("context_quality", quality.name());
        context.put("market_availability", marketAvailability.name());
        context.put("home_team", teamMap(home));
        context.put("away_team", teamMap(away));
        context.put("market", marketAvailability == MarketAvailability.COMPLETE ? marketMap(market) : Map.of());
        context.put("odds", marketAvailability == MarketAvailability.COMPLETE ? completeOddsMap(game) : Map.of());
        context.put("data_limitations", limitations(home, away, marketAvailability));
        try {
            return new AnalysisContext(objectMapper.writeValueAsString(context), quality);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Failed to serialize analysis context", e);
        }
    }

    private TeamContext teamContext(Game game, String team) {
        if (!"REG".equals(game.getGameType())) {
            List<TeamWeekMetrics> previous = metricsRepository
                    .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(game.getSeason() - 1, team);
            return new TeamContext(team, game.getSeason() - 1, true, true, lastThree(previous));
        }
        List<TeamWeekMetrics> current = metricsRepository
                .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(game.getSeason(), team).stream()
                .filter(metric -> metric.getId().getWeek() < game.getWeek()).toList();
        if (!current.isEmpty()) {
            return new TeamContext(team, game.getSeason(), false, false, lastThree(current));
        }
        List<TeamWeekMetrics> previous = metricsRepository
                .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(game.getSeason() - 1, team);
        return new TeamContext(team, game.getSeason() - 1, true, false, lastThree(previous));
    }

    private List<TeamWeekMetrics> lastThree(List<TeamWeekMetrics> values) {
        return values.size() <= 3 ? List.copyOf(values) : List.copyOf(values.subList(values.size() - 3, values.size()));
    }

    private Map<String, Object> teamMap(TeamContext team) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("abbr", team.abbr());
        result.put("metrics_season", team.season());
        result.put("metrics_origin", team.historicalReference() ? "HISTORICAL_REFERENCE" : "CURRENT_SEASON_PRIOR_WEEKS");
        result.put("historical_reference", team.historicalReference());
        result.put("recent_form_last_3_eligible_weeks", team.metrics());
        return result;
    }

    private Map<String, Object> marketMap(MarketImplied market) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("home_implied_raw", market.getHomeImpliedRaw());
        result.put("away_implied_raw", market.getAwayImpliedRaw());
        result.put("home_implied_fair", market.getHomeImpliedFair());
        result.put("away_implied_fair", market.getAwayImpliedFair());
        result.put("vig_pct", market.getVigPct());
        return result;
    }

    private Map<String, Object> completeOddsMap(Game game) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("home_moneyline", game.getHomeMoneyline());
        result.put("away_moneyline", game.getAwayMoneyline());
        if (game.getSpreadLine() != null && game.getHomeSpreadOdds() != null && game.getAwaySpreadOdds() != null) {
            result.put("spread_line", game.getSpreadLine());
            result.put("home_spread_odds", game.getHomeSpreadOdds());
            result.put("away_spread_odds", game.getAwaySpreadOdds());
        }
        if (game.getTotalLine() != null && game.getOverOdds() != null && game.getUnderOdds() != null) {
            result.put("total_line", game.getTotalLine());
            result.put("over_odds", game.getOverOdds());
            result.put("under_odds", game.getUnderOdds());
        }
        return result;
    }

    private List<String> limitations(TeamContext home, TeamContext away, MarketAvailability market) {
        java.util.ArrayList<String> result = new java.util.ArrayList<>();
        if (home.metrics().isEmpty() || away.metrics().isEmpty()) result.add("PBP_METRICS_MISSING");
        if (market == MarketAvailability.MISSING) result.add("MARKET_MISSING");
        if (market == MarketAvailability.PARTIAL) result.add("MARKET_PARTIAL_WITHHELD_FROM_PROMPT");
        if (home.historicalReference() || away.historicalReference()) result.add("HISTORICAL_REFERENCE_NOT_CURRENT_FORM");
        if (home.postseasonCutoffUnverifiable() || away.postseasonCutoffUnverifiable()) {
            result.add("POSTSEASON_METRIC_CUTOFF_UNVERIFIABLE");
        }
        return List.copyOf(result);
    }

    private ContextQuality quality(TeamContext home, TeamContext away) {
        if (home.metrics().isEmpty() && away.metrics().isEmpty()) return ContextQuality.MINIMAL;
        if (!home.metrics().isEmpty() && !away.metrics().isEmpty()
                && !home.historicalReference() && !away.historicalReference()
                && !home.postseasonCutoffUnverifiable() && !away.postseasonCutoffUnverifiable()) {
            return ContextQuality.COMPLETE;
        }
        if (!home.metrics().isEmpty() || !away.metrics().isEmpty()) return ContextQuality.PARTIAL;
        return ContextQuality.MINIMAL;
    }

    private MarketAvailability marketAvailability(Game game, MarketImplied market) {
        boolean any = market != null || game.getSpreadLine() != null || game.getTotalLine() != null
                || game.getHomeMoneyline() != null || game.getAwayMoneyline() != null
                || game.getHomeSpreadOdds() != null || game.getAwaySpreadOdds() != null
                || game.getOverOdds() != null || game.getUnderOdds() != null;
        if (!any) return MarketAvailability.MISSING;
        return coherentMarket(market) && game.getHomeMoneyline() != null && game.getAwayMoneyline() != null
                ? MarketAvailability.COMPLETE : MarketAvailability.PARTIAL;
    }

    private boolean coherentMarket(MarketImplied market) {
        if (market == null || market.getHomeImpliedRaw() == null || market.getAwayImpliedRaw() == null
                || market.getHomeImpliedFair() == null || market.getAwayImpliedFair() == null
                || market.getVigPct() == null) return false;
        BigDecimal rawSum = market.getHomeImpliedRaw().add(market.getAwayImpliedRaw());
        BigDecimal fairSum = market.getHomeImpliedFair().add(market.getAwayImpliedFair());
        return probability(market.getHomeImpliedRaw()) && probability(market.getAwayImpliedRaw())
                && probability(market.getHomeImpliedFair()) && probability(market.getAwayImpliedFair())
                && rawSum.compareTo(BigDecimal.ONE) > 0
                && fairSum.subtract(BigDecimal.ONE).abs().compareTo(new BigDecimal("0.01")) <= 0
                && market.getVigPct().compareTo(BigDecimal.ZERO) >= 0
                && rawSum.subtract(BigDecimal.ONE).subtract(market.getVigPct()).abs()
                .compareTo(new BigDecimal("0.02")) <= 0;
    }

    private boolean probability(BigDecimal value) {
        return value.compareTo(BigDecimal.ZERO) > 0 && value.compareTo(BigDecimal.ONE) < 0;
    }

    private enum MarketAvailability { COMPLETE, PARTIAL, MISSING }

    private record TeamContext(String abbr, int season, boolean historicalReference,
                               boolean postseasonCutoffUnverifiable,
                               List<TeamWeekMetrics> metrics) { }
}
