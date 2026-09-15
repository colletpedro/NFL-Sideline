package com.nflsideline.coreapi.editorial;

import com.nflsideline.coreapi.domain.Game;

public record EditorialCandidate(Game game, AnalysisDepth depth, Eligibility eligibility, EditorialReason reason) {
}
