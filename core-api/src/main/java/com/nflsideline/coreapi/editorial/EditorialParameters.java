package com.nflsideline.coreapi.editorial;

import java.util.List;
import java.util.stream.IntStream;

/** Calendar metadata, never a prompt, market input or provider configuration. */
public record EditorialParameters(int season, int gameWeek, String phase) {
    public EditorialParameters {
        if (season < 1999 || gameWeek < 1 || gameWeek > 30 || phase == null) throw new IllegalArgumentException("Invalid calendar");
    }
    public List<Integer> expectedRecentWeeks() {
        return IntStream.range(Math.max(1, gameWeek - 3), gameWeek).boxed().toList();
    }
}
