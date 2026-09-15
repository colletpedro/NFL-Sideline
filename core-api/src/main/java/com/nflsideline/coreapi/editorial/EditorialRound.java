package com.nflsideline.coreapi.editorial;

import com.nflsideline.coreapi.domain.Game;

import java.time.LocalDate;
import java.util.List;

public record EditorialRound(RoundKey key, LocalDate startsOn, LocalDate endsOn, List<Game> games) {
    public EditorialRound {
        games = List.copyOf(games);
    }
}
