package com.nflsideline.coreapi.metrics.temporal;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.regex.Pattern;

/** Epoch seconds with arbitrary decimal precision, retaining the original string in the result. */
public final class ExactInstant {
    private static final Pattern ISO = Pattern.compile("^(\\d{4}-\\d\\d-\\d\\d)T(\\d\\d:\\d\\d:\\d\\d)(\\.\\d+)?(Z|[+-]\\d\\d:\\d\\d)$");
    private ExactInstant() {}
    public static BigDecimal epochSeconds(String text) {
        var m = ISO.matcher(text);
        if (!m.matches()) throw new IllegalArgumentException("Invalid exact ISO instant");
        var offset = m.group(4);
        // E5b-3 permits offsets up to 23:59 (java.time.ZoneOffset stops at 18h).
        int seconds = 0;
        if (!offset.equals("Z")) {
            int hours = Integer.parseInt(offset.substring(1, 3)), mins = Integer.parseInt(offset.substring(4));
            if (hours > 23 || mins > 59) throw new IllegalArgumentException("Invalid offset");
            seconds = (hours * 3600 + mins * 60) * (offset.charAt(0) == '-' ? -1 : 1);
        }
        long whole = LocalDateTime.parse(m.group(1) + "T" + m.group(2)).toEpochSecond(ZoneOffset.UTC) - seconds;
        return BigDecimal.valueOf(whole).add(m.group(3) == null ? BigDecimal.ZERO : new BigDecimal(m.group(3)));
    }
}
