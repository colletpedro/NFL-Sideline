package com.nflsideline.coreapi.editorial;

import java.math.BigDecimal;
import java.math.MathContext;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** A descriptive summary of all available observations of a metric in the selected recent slice. */
public record EvidenceWindow(String id, String team, MetricCatalog metric, int season,
                             Evidence.Origin origin, List<Integer> weeks, List<String> evidenceIds,
                             BigDecimal value, Aggregation aggregation, Long volume,
                             BigDecimal minimum, BigDecimal maximum, List<Integer> missingMetricWeeks) {
    public enum Aggregation { PLAY_WEIGHTED_MEAN, MEAN_OF_WEEKLY_MEANS }

    public static List<EvidenceWindow> from(List<Evidence> evidence) {
        Map<String, Evidence> unique = new TreeMap<>();
        for (Evidence item : evidence) {
            Evidence previous = unique.putIfAbsent(item.id(), item);
            if (previous != null && !previous.equals(item))
                throw new IllegalArgumentException("Conflicting evidence for window");
        }
        Map<String, List<Evidence>> groups = new TreeMap<>();
        unique.values().forEach(item -> groups.computeIfAbsent(item.team() + ":" + item.season() + ":"
                + item.origin() + ":" + item.metric(), ignored -> new java.util.ArrayList<>()).add(item));
        return groups.values().stream().map(items -> {
            items.sort(Comparator.comparingInt(Evidence::week));
            Evidence first = items.getFirst();
            List<Integer> weeks = items.stream().map(Evidence::week).toList();
            // A total-play denominator is never used for pass/rush or early-down means.
            boolean weighted = first.metric().hasTotalPlayDenominator()
                    && items.stream().allMatch(item -> item.volume() != null && item.volume() > 0);
            long denominator = weighted ? items.stream().mapToLong(Evidence::volume).sum() : items.size();
            BigDecimal numerator = items.stream().map(item -> weighted
                    ? item.value().multiply(BigDecimal.valueOf(item.volume())) : item.value())
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            List<Integer> missing = unique.values().stream()
                    .filter(item -> item.team().equals(first.team()) && item.season() == first.season()
                            && item.origin() == first.origin() && !weeks.contains(item.week()))
                    .map(Evidence::week).distinct().sorted().toList();
            String suffix = weeks.stream().map(String::valueOf).collect(java.util.stream.Collectors.joining(","));
            return new EvidenceWindow("rw:" + first.season() + ":" + first.team() + ":" + first.metric()
                    + ":" + first.origin() + ":" + suffix, first.team(), first.metric(), first.season(), first.origin(),
                    weeks, items.stream().map(Evidence::id).toList(),
                    numerator.divide(BigDecimal.valueOf(denominator), MathContext.DECIMAL128),
                    weighted ? Aggregation.PLAY_WEIGHTED_MEAN : Aggregation.MEAN_OF_WEEKLY_MEANS,
                    weighted ? denominator : null,
                    items.stream().map(Evidence::value).min(BigDecimal::compareTo).orElseThrow(),
                    items.stream().map(Evidence::value).max(BigDecimal::compareTo).orElseThrow(), missing);
        }).toList();
    }

    /** Zero is the EPA reference, not a league-average or team-strength threshold. */
    public boolean positiveInEveryObservedWeek() { return minimum.signum() > 0; }
}
