package com.nflsideline.coreapi.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "games")
public class Game {

    @Id
    @Column(name = "game_id")
    private String gameId;

    @Column(name = "season", nullable = false)
    private Integer season;

    @Column(name = "week", nullable = false)
    private Integer week;

    @Column(name = "game_type", nullable = false)
    private String gameType;

    @Column(name = "gameday")
    private LocalDate gameday;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "home_team")
    private Team homeTeam;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "away_team")
    private Team awayTeam;

    @Column(name = "home_score")
    private Integer homeScore;

    @Column(name = "away_score")
    private Integer awayScore;

    @Column(name = "result")
    private Integer result;

    @Column(name = "spread_line")
    private BigDecimal spreadLine;

    @Column(name = "total_line")
    private BigDecimal totalLine;

    @Column(name = "home_moneyline")
    private Integer homeMoneyline;

    @Column(name = "away_moneyline")
    private Integer awayMoneyline;

    @Column(name = "home_spread_odds")
    private Integer homeSpreadOdds;

    @Column(name = "away_spread_odds")
    private Integer awaySpreadOdds;

    @Column(name = "over_odds")
    private Integer overOdds;

    @Column(name = "under_odds")
    private Integer underOdds;

    @Column(name = "roof")
    private String roof;

    @Column(name = "surface")
    private String surface;

    @Column(name = "div_game")
    private Boolean divGame;

    @Column(name = "updated_at", insertable = false, updatable = false)
    private OffsetDateTime updatedAt;
}
