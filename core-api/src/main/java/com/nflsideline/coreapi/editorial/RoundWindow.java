package com.nflsideline.coreapi.editorial;

import java.util.Optional;

public record RoundWindow(Optional<EditorialRound> current, Optional<EditorialRound> next, boolean offseason) {
    public static RoundWindow offseasonWindow() {
        return new RoundWindow(Optional.empty(), Optional.empty(), true);
    }
}
