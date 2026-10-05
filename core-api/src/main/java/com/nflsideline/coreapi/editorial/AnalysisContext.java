package com.nflsideline.coreapi.editorial;

import java.util.List;

public record AnalysisContext(String canonicalJson, ContextQuality quality, List<Evidence> evidence,
                              String homeTeam, String awayTeam) {
    public List<EvidenceWindow> windows() { return EvidenceWindow.from(evidence); }
    /** Compatibility for batch test fixtures; production builds the full typed context. */
    public AnalysisContext(String canonicalJson, ContextQuality quality) {
        this(canonicalJson, quality, List.of(), "", "");
    }
}
