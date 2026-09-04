package com.nflsideline.coreapi.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "teams")
public class Team {

    @Id
    @Column(name = "team_abbr")
    private String teamAbbr;

    @Column(name = "team_name", nullable = false)
    private String teamName;

    @Column(name = "conference")
    private String conference;

    @Column(name = "division")
    private String division;

    @Column(name = "logo_url")
    private String logoUrl;
}
