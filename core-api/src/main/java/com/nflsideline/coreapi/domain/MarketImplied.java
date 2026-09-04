package com.nflsideline.coreapi.domain;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.MapsId;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@JsonIgnoreProperties({"game"})
@Table(name = "market_implied")
public class MarketImplied {

    @Id
    @Column(name = "game_id")
    private String gameId;

    @OneToOne(fetch = FetchType.LAZY)
    @MapsId
    @JoinColumn(name = "game_id")
    private Game game;

    @Column(name = "home_implied_raw")
    private BigDecimal homeImpliedRaw;

    @Column(name = "away_implied_raw")
    private BigDecimal awayImpliedRaw;

    @Column(name = "home_implied_fair")
    private BigDecimal homeImpliedFair;

    @Column(name = "away_implied_fair")
    private BigDecimal awayImpliedFair;

    @Column(name = "vig_pct")
    private BigDecimal vigPct;

    @Column(name = "computed_at", insertable = false, updatable = false)
    private OffsetDateTime computedAt;
}
