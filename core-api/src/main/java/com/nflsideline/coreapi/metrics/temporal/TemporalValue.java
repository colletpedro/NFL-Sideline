package com.nflsideline.coreapi.metrics.temporal;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.List;
import java.util.Map;

/** Lossless immutable internal JSON algebra; no floating point or mutable nodes escape. */
public sealed interface TemporalValue {
    record ObjectValue(Map<String, TemporalValue> fields) implements TemporalValue {
        public ObjectValue { fields = Map.copyOf(fields); }
        public TemporalValue get(String key) {
            var value = fields.get(key);
            if (value == null) throw new IllegalArgumentException("Missing field: " + key);
            return value;
        }
        public ObjectValue object(String key) { return (ObjectValue) get(key); }
        public List<TemporalValue> array(String key) { return ((ArrayValue) get(key)).values(); }
        public String text(String key) { return ((TextValue) get(key)).value(); }
        public BigInteger integer(String key) { return ((IntegerValue) get(key)).value(); }
        public BigDecimal decimal(String key) { return new BigDecimal(text(key)); }
        public boolean bool(String key) { return ((BooleanValue) get(key)).value(); }
        public boolean isNull(String key) { return get(key) == NullValue.INSTANCE; }
        public ObjectValue without(String... keys) {
            var copy = new java.util.HashMap<>(fields);
            for (var key : keys) copy.remove(key);
            return new ObjectValue(copy);
        }
    }
    record ArrayValue(List<TemporalValue> values) implements TemporalValue {
        public ArrayValue { values = List.copyOf(values); }
    }
    record TextValue(String value) implements TemporalValue {}
    record IntegerValue(BigInteger value) implements TemporalValue {}
    record BooleanValue(boolean value) implements TemporalValue {}
    enum NullValue implements TemporalValue { INSTANCE }
}
