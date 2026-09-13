package com.nflsideline.coreapi.service;

import java.time.Clock;
import java.time.LocalDate;
import java.time.Month;

/** Shared season boundary for REST and batch. */
public final class NflSeason {
    private NflSeason() {}

    public static int current(Clock clock) {
        LocalDate today = LocalDate.now(clock);
        return today.getMonth().compareTo(Month.MARCH) >= 0 ? today.getYear() : today.getYear() - 1;
    }
}
