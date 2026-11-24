package com.nflsideline.coreapi.editorial;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.*;

class EvidenceWindowTest {
    @Test void knownPlayDenominatorsWeightTheMeanAndRetainSourcesAndRange() {
        Evidence a = ev(1, MetricCatalog.OFF_EPA_PLAY, "0.4", 25);
        Evidence b = ev(3, MetricCatalog.OFF_EPA_PLAY, "-0.2", 75);
        EvidenceWindow window = EvidenceWindow.from(List.of(b, a)).getFirst();
        assertThat(window.value()).isEqualByComparingTo("-0.05");
        assertThat(window.volume()).isEqualTo(100L);
        assertThat(window.aggregation()).isEqualTo(EvidenceWindow.Aggregation.PLAY_WEIGHTED_MEAN);
        assertThat(window.weeks()).containsExactly(1, 3);
        assertThat(window.evidenceIds()).containsExactly(a.id(), b.id());
        assertThat(window.minimum()).isEqualByComparingTo("-0.2");
        assertThat(window.maximum()).isEqualByComparingTo("0.4");
    }

    @Test void passMeansNeverUseTotalPlayVolumeAndMissingVolumeDoesNotBecomeZero() {
        EvidenceWindow passes = EvidenceWindow.from(List.of(
                ev(1, MetricCatalog.OFF_EPA_PASS, "0.4", 25),
                ev(2, MetricCatalog.OFF_EPA_PASS, "-0.2", 75))).getFirst();
        assertThat(passes.value()).isEqualByComparingTo("0.1");
        assertThat(passes.volume()).isNull();
        assertThat(passes.aggregation()).isEqualTo(EvidenceWindow.Aggregation.MEAN_OF_WEEKLY_MEANS);
        EvidenceWindow incomplete = EvidenceWindow.from(List.of(
                ev(1, MetricCatalog.OFF_EPA_PLAY, "0.4", 25),
                ev(2, MetricCatalog.OFF_EPA_PLAY, "-0.2", null))).getFirst();
        assertThat(incomplete.value()).isEqualByComparingTo("0.1");
        assertThat(incomplete.volume()).isNull();
    }

    @Test void duplicateOrReorderedSourcesCannotChangeWindowOrSampleSize() {
        Evidence a = ev(1, MetricCatalog.OFF_EPA_PASS, "0.2", null);
        Evidence b = ev(3, MetricCatalog.OFF_EPA_PASS, "0.1", null);
        assertThat(EvidenceWindow.from(List.of(b, a, b)))
                .isEqualTo(EvidenceWindow.from(List.of(a, b)));
        assertThatThrownBy(() -> EvidenceWindow.from(List.of(a, ev(1, MetricCatalog.OFF_EPA_PASS, "0.9", null))))
                .hasMessage("Conflicting evidence for window");
    }

    @Test void metricSpecificMissingWeeksRemainExplicitInsteadOfFilled() {
        var windows = EvidenceWindow.from(List.of(ev(1, MetricCatalog.OFF_EPA_PASS, "0.2", null),
                ev(1, MetricCatalog.OFF_EPA_PLAY, "0.1", 50), ev(2, MetricCatalog.OFF_EPA_PLAY, "0.3", 60)));
        EvidenceWindow passes = windows.stream().filter(w -> w.metric() == MetricCatalog.OFF_EPA_PASS).findFirst().orElseThrow();
        assertThat(passes.weeks()).containsExactly(1);
        assertThat(passes.missingMetricWeeks()).containsExactly(2);
        assertThat(passes.value()).isEqualByComparingTo("0.2");
    }

    @Test void positiveMeanDoesNotHideNegativeWeekAndZeroIsNotPositive() {
        EvidenceWindow mixed = EvidenceWindow.from(List.of(ev(1, MetricCatalog.OFF_EPA_PASS, "1.06", null),
                ev(2, MetricCatalog.OFF_EPA_PASS, "-0.1", null))).getFirst();
        assertThat(mixed.value()).isPositive();
        assertThat(mixed.positiveInEveryObservedWeek()).isFalse();
        assertThat(EvidenceWindow.from(List.of(ev(1, MetricCatalog.OFF_EPA_PASS, "0", null)))
                .getFirst().positiveInEveryObservedWeek()).isFalse();
    }

    @Test void historicalAndCurrentEvidenceAreNeverPooled() {
        Evidence old = Evidence.observed("A", MetricCatalog.OFF_EPA_PASS, 2025, 18, true, new BigDecimal("1"), null);
        var windows = EvidenceWindow.from(List.of(old, ev(1, MetricCatalog.OFF_EPA_PASS, "-0.1", null)));
        assertThat(windows).hasSize(2);
        assertThat(windows).allMatch(w -> w.evidenceIds().size() == 1);
    }

    private Evidence ev(int week, MetricCatalog metric, String value, Integer volume) {
        return Evidence.observed("A", metric, 2026, week, false, new BigDecimal(value), volume);
    }
}
