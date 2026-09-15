package com.nflsideline.coreapi.editorial;

public enum AnalysisDepth {
    FULL("matchup_full_v0"),
    BASIC("matchup_basic_v0"),
    LEGACY_PUBLISHED("matchup");

    private final String analysisType;

    AnalysisDepth(String analysisType) {
        this.analysisType = analysisType;
    }

    public String analysisType() {
        return analysisType;
    }

    public static AnalysisDepth fromAnalysisType(String value) {
        for (AnalysisDepth depth : values()) {
            if (depth.analysisType.equals(value)) {
                return depth;
            }
        }
        throw new IllegalArgumentException("Unsupported analysis type");
    }
}
