package com.nflsideline.coreapi.snapshot;

import java.nio.file.Path;
import java.time.Clock;
import com.nflsideline.coreapi.service.NflSeason;
import java.util.List;
import java.util.TreeSet;

public record SnapshotOptions(List<Integer> seasons, Path outputDirectory, boolean allowEmpty) {

    static SnapshotOptions parse(String[] args, Clock clock) {
        TreeSet<Integer> seasons = new TreeSet<>();
        Path output = null;
        boolean allowEmpty = false;
        for (int i = 0; i < args.length; i++) {
            String argument = args[i];
            if ("--allow-empty".equals(argument)) {
                allowEmpty = true;
            } else if (argument.startsWith("--season=")) {
                seasons.add(parseSeason(argument.substring("--season=".length())));
            } else if ("--season".equals(argument)) {
                seasons.add(parseSeason(requireValue(args, ++i, "--season")));
            } else if (argument.startsWith("--output=")) {
                output = Path.of(argument.substring("--output=".length()));
            } else if ("--output".equals(argument)) {
                output = Path.of(requireValue(args, ++i, "--output"));
            } else {
                throw new IllegalArgumentException("Unsupported snapshot option");
            }
        }
        if (output == null) {
            throw new IllegalArgumentException("--output is required");
        }
        if (seasons.isEmpty()) {
            seasons.add(currentSeason(clock));
        }
        return new SnapshotOptions(List.copyOf(seasons), output.toAbsolutePath().normalize(), allowEmpty);
    }

    static int currentSeason(Clock clock) {
        return NflSeason.current(clock);
    }

    private static int parseSeason(String raw) {
        try {
            int season = Integer.parseInt(raw);
            if (season < 1999 || season > 2100) {
                throw new IllegalArgumentException("Season is outside the supported range");
            }
            return season;
        } catch (NumberFormatException exception) {
            throw new IllegalArgumentException("Season must be an integer");
        }
    }

    private static String requireValue(String[] args, int index, String option) {
        if (index >= args.length || args[index].startsWith("--")) {
            throw new IllegalArgumentException(option + " requires a value");
        }
        return args[index];
    }
}
