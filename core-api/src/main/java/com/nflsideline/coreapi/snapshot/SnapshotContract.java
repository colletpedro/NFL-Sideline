package com.nflsideline.coreapi.snapshot;

import com.fasterxml.jackson.annotation.JsonPropertyOrder;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.SortedMap;

public final class SnapshotContract {

    public static final int SCHEMA_VERSION = 1;

    private SnapshotContract() {
    }

    @JsonPropertyOrder({"schemaVersion", "generatedAt", "defaultSeason", "seasons"})
    public record Manifest(int schemaVersion, OffsetDateTime generatedAt,
                           int defaultSeason, List<Integer> seasons) {
    }

    @JsonPropertyOrder({"schemaVersion", "season", "generatedAt", "teams", "games", "metricsByTeam", "analysesByGame"})
    public record SeasonSnapshot(int schemaVersion, int season, OffsetDateTime generatedAt,
                                 List<TeamDto> teams, List<GameDto> games,
                                 SortedMap<String, List<MetricDto>> metricsByTeam,
                                 SortedMap<String, AnalysisDto> analysesByGame) {
    }

    @JsonPropertyOrder({"teamAbbr", "teamName", "conference", "division", "logoUrl"})
    public record TeamDto(String teamAbbr, String teamName, String conference,
                          String division, String logoUrl) {
    }

    @JsonPropertyOrder({"gameId", "season", "week", "gameType", "gameday", "homeTeamAbbr", "awayTeamAbbr",
            "homeScore", "awayScore", "result", "spreadLine", "totalLine", "homeMoneyline", "awayMoneyline",
            "homeSpreadOdds", "awaySpreadOdds", "overOdds", "underOdds", "roof", "surface", "divisionGame",
            "updatedAt", "market"})
    public record GameDto(String gameId, int season, int week, String gameType, LocalDate gameday,
                          String homeTeamAbbr, String awayTeamAbbr, Integer homeScore, Integer awayScore,
                          Integer result, BigDecimal spreadLine, BigDecimal totalLine,
                          Integer homeMoneyline, Integer awayMoneyline,
                          Integer homeSpreadOdds, Integer awaySpreadOdds, Integer overOdds, Integer underOdds,
                          String roof, String surface, Boolean divisionGame, OffsetDateTime updatedAt,
                          MarketDto market) {
    }

    @JsonPropertyOrder({"homeImpliedRaw", "awayImpliedRaw", "homeImpliedFair", "awayImpliedFair", "vigPct", "computedAt"})
    public record MarketDto(BigDecimal homeImpliedRaw, BigDecimal awayImpliedRaw,
                            BigDecimal homeImpliedFair, BigDecimal awayImpliedFair,
                            BigDecimal vigPct, OffsetDateTime computedAt) {
    }

    @JsonPropertyOrder({"season", "week", "teamAbbr", "offEpaPlay", "offEpaPass", "offEpaRush", "defEpaPass",
            "defEpaRush", "dropbackRate", "playsOffense"})
    public record MetricDto(int season, int week, String teamAbbr,
                            BigDecimal offEpaPlay, BigDecimal offEpaPass, BigDecimal offEpaRush,
                            BigDecimal defEpaPass, BigDecimal defEpaRush,
                            BigDecimal dropbackRate, Integer playsOffense) {
    }

    @JsonPropertyOrder({"gameId", "analysisType", "createdAt", "fatorChave", "vantagemTatica", "alertaVermelho", "veredito"})
    public record AnalysisDto(String gameId, String analysisType, OffsetDateTime createdAt,
                              String fatorChave, String vantagemTatica,
                              String alertaVermelho, String veredito) {
    }
}
