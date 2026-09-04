package com.nflsideline.coreapi.domain;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "team_week_metrics")
public class TeamWeekMetrics {

    @EmbeddedId
    private TeamWeekMetricsId id;

    @Column(name = "off_epa_play")
    private BigDecimal offEpaPlay;

    @Column(name = "def_epa_play")
    private BigDecimal defEpaPlay;

    @Column(name = "off_epa_pass")
    private BigDecimal offEpaPass;

    @Column(name = "off_epa_rush")
    private BigDecimal offEpaRush;

    @Column(name = "def_epa_pass")
    private BigDecimal defEpaPass;

    @Column(name = "def_epa_rush")
    private BigDecimal defEpaRush;

    @Column(name = "off_success_rate")
    private BigDecimal offSuccessRate;

    @Column(name = "def_success_rate")
    private BigDecimal defSuccessRate;

    @Column(name = "early_down_epa")
    private BigDecimal earlyDownEpa;

    @Column(name = "dropback_rate")
    private BigDecimal dropbackRate;

    @Column(name = "explosive_play_rate")
    private BigDecimal explosivePlayRate;

    @Column(name = "plays_offense")
    private Integer playsOffense;

    @Column(name = "plays_defense")
    private Integer playsDefense;
}
