package com.nflsideline.coreapi.editorial.batch;

import java.time.LocalDate;

public record EditorialBatchOptions(int season, LocalDate asOfDate, boolean dryRun,
                                    int maxAnalyses, String revisionKey) {
    static EditorialBatchOptions parse(String[] args) {
        Integer season = null;
        LocalDate asOf = null;
        boolean dryRun = true;
        int max = 32;
        String revision = null;
        for (int i = 0; i < args.length; i++) {
            String argument = args[i];
            if ("--dry-run".equals(argument)) dryRun = true;
            else if ("--execute".equals(argument)) dryRun = false;
            else if (argument.startsWith("--season=")) season = integer(argument.substring(9), "season");
            else if ("--season".equals(argument)) season = integer(value(args, ++i, argument), "season");
            else if (argument.startsWith("--as-of=")) asOf = date(argument.substring(8));
            else if ("--as-of".equals(argument)) asOf = date(value(args, ++i, argument));
            else if (argument.startsWith("--max-analyses=")) max = integer(argument.substring(15), "max-analyses");
            else if ("--max-analyses".equals(argument)) max = integer(value(args, ++i, argument), "max-analyses");
            else if (argument.startsWith("--revision-key=")) revision = argument.substring(15);
            else if ("--revision-key".equals(argument)) revision = value(args, ++i, argument);
            else throw new IllegalArgumentException("Unsupported editorial option");
        }
        if (season == null || season < 1999 || season > 2100) throw new IllegalArgumentException("Valid --season is required");
        if (asOf == null) throw new IllegalArgumentException("--as-of is required");
        if (max < 0) throw new IllegalArgumentException("--max-analyses must be non-negative");
        if (revision == null || revision.isBlank()) throw new IllegalArgumentException("--revision-key is required");
        return new EditorialBatchOptions(season, asOf, dryRun, max, revision);
    }

    private static int integer(String raw, String name) {
        try { return Integer.parseInt(raw); }
        catch (NumberFormatException failure) { throw new IllegalArgumentException("Invalid --" + name); }
    }

    private static LocalDate date(String raw) {
        try { return LocalDate.parse(raw); }
        catch (RuntimeException failure) { throw new IllegalArgumentException("Invalid --as-of"); }
    }

    private static String value(String[] args, int index, String option) {
        if (index >= args.length || args[index].startsWith("--")) throw new IllegalArgumentException(option + " requires a value");
        return args[index];
    }
}
