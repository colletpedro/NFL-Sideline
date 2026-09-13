package com.nflsideline.coreapi.snapshot;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.MarketImplied;
import com.nflsideline.coreapi.domain.Team;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import org.springframework.stereotype.Component;
import org.springframework.context.annotation.Profile;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

@Component
@Profile("snapshot")
public class SnapshotAssembler {

    private static final List<String> ANALYSIS_FIELDS =
            List.of("fator_chave", "vantagem_tatica", "alerta_vermelho", "veredito");

    private final ObjectMapper objectMapper;

    public SnapshotAssembler(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public AssemblyResult assemble(int season, OffsetDateTime generatedAt,
                                   List<Game> sourceGames,
                                   List<TeamWeekMetrics> sourceMetrics,
                                   List<AnalysisCache> sourceAnalyses) {
        List<Game> games = sourceGames.stream().sorted(gameOrder()).toList();
        SortedMap<String, SnapshotContract.TeamDto> teamMap = new TreeMap<>();
        List<SnapshotContract.GameDto> gameDtos = new ArrayList<>();
        LinkedHashSet<String> gameIds = new LinkedHashSet<>();
        for (Game game : games) {
            addTeam(teamMap, game.getHomeTeam());
            addTeam(teamMap, game.getAwayTeam());
            gameDtos.add(toGame(game));
            gameIds.add(game.getGameId());
        }

        SortedMap<String, List<SnapshotContract.MetricDto>> metricsByTeam = new TreeMap<>();
        sourceMetrics.stream()
                .sorted(Comparator.comparing((TeamWeekMetrics metric) -> metric.getId().getTeamAbbr())
                        .thenComparing(metric -> metric.getId().getWeek()))
                .forEach(metric -> metricsByTeam
                        .computeIfAbsent(metric.getId().getTeamAbbr(), ignored -> new ArrayList<>())
                        .add(toMetric(metric)));

        SortedMap<String, SnapshotContract.AnalysisDto> analysesByGame = new TreeMap<>();
        int rejected = 0;
        Map<String, AnalysisCache> latest = new TreeMap<>();
        sourceAnalyses.stream()
                .filter(analysis -> "matchup".equals(analysis.getAnalysisType()))
                .filter(analysis -> gameIds.contains(analysis.getGameId()))
                .sorted(analysisOrder())
                .forEach(analysis -> latest.putIfAbsent(analysis.getGameId(), analysis));
        for (Map.Entry<String, AnalysisCache> entry : latest.entrySet()) {
            SnapshotContract.AnalysisDto analysis = parseAnalysis(entry.getValue());
            if (analysis == null) {
                rejected++;
            } else {
                analysesByGame.put(entry.getKey(), analysis);
            }
        }

        int missing = games.size() - analysesByGame.size() - rejected;
        SnapshotContract.SeasonSnapshot snapshot = new SnapshotContract.SeasonSnapshot(
                SnapshotContract.SCHEMA_VERSION,
                season,
                generatedAt,
                List.copyOf(teamMap.values()),
                List.copyOf(gameDtos),
                immutableMetricMap(metricsByTeam),
                analysesByGame);
        return new AssemblyResult(snapshot, analysesByGame.size(), missing, rejected,
                metricsByTeam.values().stream().mapToInt(List::size).sum());
    }

    private Comparator<Game> gameOrder() {
        return Comparator.comparing(Game::getWeek)
                .thenComparing(Game::getGameday, Comparator.nullsLast(Comparator.naturalOrder()))
                .thenComparing(Game::getGameId);
    }

    private Comparator<AnalysisCache> analysisOrder() {
        return Comparator.comparing(AnalysisCache::getGameId)
                .thenComparing(AnalysisCache::getCreatedAt,
                        Comparator.nullsLast(Comparator.reverseOrder()))
                .thenComparing(AnalysisCache::getId,
                        Comparator.nullsLast(Comparator.reverseOrder()));
    }

    private void addTeam(SortedMap<String, SnapshotContract.TeamDto> teams, Team team) {
        if (team != null) {
            teams.put(team.getTeamAbbr(), new SnapshotContract.TeamDto(
                    team.getTeamAbbr(), team.getTeamName(), team.getConference(),
                    team.getDivision(), team.getLogoUrl()));
        }
    }

    private SnapshotContract.GameDto toGame(Game game) {
        MarketImplied market = game.getMarketImplied();
        SnapshotContract.MarketDto marketDto = market == null ? null : new SnapshotContract.MarketDto(
                market.getHomeImpliedRaw(), market.getAwayImpliedRaw(),
                market.getHomeImpliedFair(), market.getAwayImpliedFair(),
                market.getVigPct(), utc(market.getComputedAt()));
        return new SnapshotContract.GameDto(
                game.getGameId(), game.getSeason(), game.getWeek(), game.getGameType(), game.getGameday(),
                game.getHomeTeam().getTeamAbbr(), game.getAwayTeam().getTeamAbbr(),
                game.getHomeScore(), game.getAwayScore(), game.getResult(), game.getSpreadLine(),
                game.getTotalLine(), game.getHomeMoneyline(), game.getAwayMoneyline(),
                game.getHomeSpreadOdds(), game.getAwaySpreadOdds(), game.getOverOdds(), game.getUnderOdds(),
                game.getRoof(), game.getSurface(), game.getDivGame(), utc(game.getUpdatedAt()), marketDto);
    }

    private SnapshotContract.MetricDto toMetric(TeamWeekMetrics metric) {
        return new SnapshotContract.MetricDto(
                metric.getId().getSeason(), metric.getId().getWeek(), metric.getId().getTeamAbbr(),
                metric.getOffEpaPlay(), metric.getOffEpaPass(), metric.getOffEpaRush(),
                metric.getDefEpaPass(), metric.getDefEpaRush(), metric.getDropbackRate(), metric.getPlaysOffense());
    }

    private SnapshotContract.AnalysisDto parseAnalysis(AnalysisCache analysis) {
        try {
            JsonNode root = objectMapper.readTree(analysis.getResponseText());
            if (!root.isObject()) {
                return null;
            }
            for (String field : ANALYSIS_FIELDS) {
                if (!root.path(field).isTextual() || root.path(field).textValue().trim().isEmpty()) {
                    return null;
                }
            }
            return new SnapshotContract.AnalysisDto(
                    analysis.getGameId(), "matchup", utc(analysis.getCreatedAt()),
                    root.path("fator_chave").textValue(), root.path("vantagem_tatica").textValue(),
                    root.path("alerta_vermelho").textValue(), root.path("veredito").textValue());
        } catch (Exception ignored) {
            return null;
        }
    }

    private OffsetDateTime utc(OffsetDateTime value) {
        return value == null ? null : value.withOffsetSameInstant(ZoneOffset.UTC);
    }

    private SortedMap<String, List<SnapshotContract.MetricDto>> immutableMetricMap(
            SortedMap<String, List<SnapshotContract.MetricDto>> source) {
        SortedMap<String, List<SnapshotContract.MetricDto>> result = new TreeMap<>();
        source.forEach((team, metrics) -> result.put(team, List.copyOf(metrics)));
        return result;
    }

    public record AssemblyResult(SnapshotContract.SeasonSnapshot snapshot,
                                 int validAnalyses, int missingAnalyses,
                                 int rejectedAnalyses, int metrics) {
    }
}
