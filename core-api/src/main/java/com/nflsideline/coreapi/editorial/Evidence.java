package com.nflsideline.coreapi.editorial;

import java.math.BigDecimal;

/** A single source-row observation; no aggregates or inferred denominators. */
public record Evidence(String id, String team, MetricCatalog metric, int season, int week,
                       Origin origin, BigDecimal value, MetricCatalog.Unit unit, Integer volume,
                       String sourceTable, String sourceKey) {
    public enum Origin { CURRENT_SEASON_PRIOR_WEEKS, HISTORICAL_REFERENCE }

    public static Evidence observed(String team, MetricCatalog metric, int season, int week,
                                    boolean historical, BigDecimal value, Integer volume) {
        String key = season + ":" + week + ":" + team;
        return new Evidence("tw:" + key + ":" + metric.name(), team, metric, season, week,
                historical ? Origin.HISTORICAL_REFERENCE : Origin.CURRENT_SEASON_PRIOR_WEEKS,
                value, metric.unit(), volume, "team_week_metrics", key);
    }
}
