package com.nflsideline.coreapi.editorial;

import com.nflsideline.coreapi.domain.Game;

import java.time.Clock;
import java.time.LocalDate;
import java.util.Comparator;
import java.util.List;

public final class EditorialPlanner {
    private final EditorialRoundResolver resolver;

    public EditorialPlanner(EditorialRoundResolver resolver) {
        this.resolver = resolver;
    }

    public List<EditorialCandidate> plan(List<Game> games, Clock clock) {
        return plan(games, LocalDate.now(clock));
    }

    public List<EditorialCandidate> plan(List<Game> games, LocalDate asOfDate) {
        return plan(games, asOfDate, true);
    }

    public List<EditorialCandidate> planForHistoricalEligibility(List<Game> games, LocalDate asOfDate) {
        return plan(games, asOfDate, false);
    }

    private List<EditorialCandidate> plan(List<Game> games, LocalDate asOfDate, boolean useRecordedResult) {
        RoundWindow window = resolver.resolve(games, asOfDate);
        return games.stream().sorted(Comparator.comparing(Game::getGameday,
                        Comparator.nullsLast(Comparator.naturalOrder())).thenComparing(Game::getGameId))
                .map(game -> candidate(game, window, asOfDate, useRecordedResult)).toList();
    }

    private EditorialCandidate candidate(Game game, RoundWindow window, LocalDate asOfDate,
                                         boolean useRecordedResult) {
        if (game.getGameday() == null) {
            return omitted(game, EditorialReason.MISSING_GAMEDAY);
        }
        if (isFinished(game, asOfDate, useRecordedResult)) {
            return omitted(game, game.getGameday().isBefore(asOfDate) && !hasCompleteResult(game)
                    ? EditorialReason.PAST_WITHOUT_SCORE : EditorialReason.GAME_FINISHED);
        }
        if (window.offseason()) {
            return omitted(game, EditorialReason.OFFSEASON);
        }
        RoundKey key = new RoundKey(game.getSeason(), game.getGameType(), game.getWeek());
        if (window.current().map(round -> round.key().equals(key)).orElse(false)) {
            return new EditorialCandidate(game, AnalysisDepth.FULL, Eligibility.ELIGIBLE, EditorialReason.CURRENT_ROUND);
        }
        if (window.next().map(round -> round.key().equals(key)).orElse(false)) {
            return new EditorialCandidate(game, AnalysisDepth.BASIC, Eligibility.ELIGIBLE, EditorialReason.NEXT_ROUND);
        }
        return omitted(game, EditorialReason.OUTSIDE_EDITORIAL_WINDOW);
    }

    public static boolean isFinished(Game game, LocalDate asOfDate) {
        return isFinished(game, asOfDate, true);
    }

    private static boolean isFinished(Game game, LocalDate asOfDate, boolean useRecordedResult) {
        return (useRecordedResult && hasCompleteResult(game))
                || (game.getGameday() != null && game.getGameday().isBefore(asOfDate));
    }

    private static boolean hasCompleteResult(Game game) {
        return game.getHomeScore() != null && game.getAwayScore() != null && game.getResult() != null;
    }

    private EditorialCandidate omitted(Game game, EditorialReason reason) {
        return new EditorialCandidate(game, null, Eligibility.INELIGIBLE, reason);
    }
}
