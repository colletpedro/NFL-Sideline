package com.nflsideline.coreapi.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Embeddable
public class TeamWeekMetricsId implements Serializable {

    @Column(name = "season", nullable = false)
    private Integer season;

    @Column(name = "week", nullable = false)
    private Integer week;

    @Column(name = "team_abbr", nullable = false)
    private String teamAbbr;
}
