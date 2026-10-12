package com.nflsideline.coreapi.metrics.temporal;

import java.nio.file.Path;

/** Explicit offline demonstration; no Spring application/context is started. */
public final class TemporalReadApplication {
    private TemporalReadApplication() {}
    public static int run(String[] args) {
        if (args.length != 2 || !args[0].equals("--artifact")) {
            System.err.println("Usage: metrics-temporal-read --artifact NEW_RESULT_DIRECTORY"); return 2;
        }
        try {
            var result = new TemporalResultReader().read(Path.of(args[1]));
            System.out.println(result.resultId() + " " + result.auditId() + " " + result.request().text("mode"));
            for (var block : result.blocks()) for (var a : block.aggregates())
                System.out.println(a.document().text("role") + "/" + a.document().text("foundation") + " " + a.document().text("scope") +
                    " EPA=" + (a.epa() == null ? "null" : a.epa().exact()) + " volume=" + a.sums().eligibleN());
            return 0;
        } catch (Exception error) {
            System.err.println("Temporal result-v2 validation failed: " + error.getMessage()); return 2;
        }
    }
}
