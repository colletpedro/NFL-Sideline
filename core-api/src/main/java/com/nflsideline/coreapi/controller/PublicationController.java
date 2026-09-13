package com.nflsideline.coreapi.controller;

import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.service.NflSeason;
import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

@RestController
@Profile("!snapshot")
public class PublicationController {
    private final GameRepository games;

    public PublicationController(GameRepository games) {
        this.games = games;
    }

    @GetMapping("/api/v1/publication")
    public PublicationContext publication() {
        int season = NflSeason.current(Clock.systemUTC());
        OffsetDateTime updated = games.latestUpdatedAt(season);
        return new PublicationContext(season, updated == null ? null : updated.withOffsetSameInstant(ZoneOffset.UTC));
    }

    public record PublicationContext(int defaultSeason, OffsetDateTime generatedAt) {}
}
