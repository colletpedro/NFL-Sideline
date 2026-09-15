package com.nflsideline.coreapi.editorial;

import com.nflsideline.coreapi.domain.Game;

import java.time.Clock;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class EditorialRoundResolver {

    public RoundWindow resolve(List<Game> games, Clock clock) {
        return resolve(games, LocalDate.now(clock));
    }

    public RoundWindow resolve(List<Game> games, LocalDate asOfDate) {
        List<EditorialRound> rounds = rounds(games);
        if (rounds.isEmpty() || asOfDate.isBefore(rounds.getFirst().startsOn().minusDays(7))) {
            return RoundWindow.offseasonWindow();
        }

        EditorialRound current = rounds.stream()
                .filter(round -> !asOfDate.isBefore(round.startsOn()) && !asOfDate.isAfter(round.endsOn()))
                .max(Comparator.comparing(EditorialRound::startsOn)).orElse(null);
        if (current == null) {
            current = rounds.stream().filter(round -> round.startsOn().isAfter(asOfDate)).findFirst().orElse(null);
        }
        if (current == null) {
            return RoundWindow.offseasonWindow();
        }
        int index = rounds.indexOf(current);
        EditorialRound next = index + 1 < rounds.size() ? rounds.get(index + 1) : null;
        return new RoundWindow(java.util.Optional.of(current), java.util.Optional.ofNullable(next), false);
    }

    public List<EditorialRound> rounds(List<Game> games) {
        Map<RoundKey, List<Game>> grouped = new LinkedHashMap<>();
        games.stream().filter(game -> game.getGameday() != null).forEach(game -> grouped
                .computeIfAbsent(new RoundKey(game.getSeason(), game.getGameType(), game.getWeek()), ignored -> new ArrayList<>())
                .add(game));
        return grouped.entrySet().stream().map(entry -> {
                    LocalDate first = entry.getValue().stream().map(Game::getGameday).min(LocalDate::compareTo).orElseThrow();
                    LocalDate last = entry.getValue().stream().map(Game::getGameday).max(LocalDate::compareTo).orElseThrow();
                    List<Game> orderedGames = entry.getValue().stream()
                            .sorted(Comparator.comparing(Game::getGameday).thenComparing(Game::getGameId)).toList();
                    return new EditorialRound(entry.getKey(), first, last, orderedGames);
                })
                .sorted(Comparator.comparing(EditorialRound::startsOn)
                        .thenComparing(round -> round.key().phase())
                        .thenComparing(round -> round.key().week()))
                .toList();
    }
}
