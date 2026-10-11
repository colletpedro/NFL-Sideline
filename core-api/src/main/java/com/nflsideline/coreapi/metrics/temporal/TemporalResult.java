package com.nflsideline.coreapi.metrics.temporal;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.List;
import static com.nflsideline.coreapi.metrics.temporal.TemporalValue.*;

/** Internal result-v2, deliberately unrelated to editorial/context/snapshot DTOs. */
public record TemporalResult(ObjectValue document, List<Block> blocks) {
    public TemporalResult { blocks = List.copyOf(blocks); }
    public ObjectValue request() { return document.object("request"); }
    public ObjectValue guarantees() { return document.object("guarantees"); }
    public String resultId() { return document.text("result_id"); }
    public String auditId() { return document.text("audit_id"); }
    public record Block(ObjectValue document, List<Aggregate> aggregates) {
        public Block { aggregates = List.copyOf(aggregates); }
        public ObjectValue requestedPeriod() { return document.object("requestedPeriod"); }
        public ObjectValue coverage() { return document.object("coverage"); }
    }
    public record Aggregate(ObjectValue document, Sums sums, Ratio epa, Ratio successRate, Ratio frequency) {}
    public record Sums(BigInteger eligibleN, BigInteger epaN, BigInteger successN,
                       BigInteger missingN, BigInteger nonfiniteN, BigDecimal epaSum) {}
    public record Ratio(BigDecimal numerator, BigInteger denominator, String exact) {}
}
