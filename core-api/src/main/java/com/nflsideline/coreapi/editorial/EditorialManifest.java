package com.nflsideline.coreapi.editorial;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;

public record EditorialManifest(int version, List<Selection> selections) {
    public record Selection(String gameId, long analysisCacheId, AnalysisDepth depth,
                            String promptHash, String responseHash, String status,
                            String reviewedBy, OffsetDateTime reviewedAt, LocalDate asOfDate) { }
}
