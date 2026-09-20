package com.nflsideline.coreapi.editorial.batch;

import com.nflsideline.coreapi.CoreApiApplication;
import com.nflsideline.coreapi.editorial.AnalysisDepth;
import org.springframework.boot.Banner;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

import java.util.Map;

public final class EditorialBatchApplication {
    private EditorialBatchApplication() { }

    public static int run(String[] args) {
        try {
            EditorialBatchOptions options = EditorialBatchOptions.parse(args);
            if (!options.dryRun() && System.getenv().getOrDefault("GEMINI_API_KEY", "").isBlank()) {
                throw new IllegalStateException("GEMINI_API_KEY is required for execution");
            }
            try (ConfigurableApplicationContext context = new SpringApplicationBuilder(CoreApiApplication.class)
                    .profiles("editorial").web(WebApplicationType.NONE).bannerMode(Banner.Mode.OFF)
                    .logStartupInfo(false).properties(Map.of(
                            "spring.main.web-application-type", "none",
                            "spring.jpa.open-in-view", "false",
                            "logging.level.root", "OFF"))
                    .run()) {
                EditorialBatchService.Summary summary = context.getBean(EditorialBatchService.class).run(options);
                System.out.printf("mode=%s eligible_full=%d eligible_basic=%d caches_reused=%d calls_planned=%d "
                                + "calls_realized=%d omitted_by_limit=%d failures=%d failure_categories=%s failed_games=%s omissions=%s%n",
                        summary.dryRun() ? "dry-run" : "execute",
                        summary.eligible().getOrDefault(AnalysisDepth.FULL, 0),
                        summary.eligible().getOrDefault(AnalysisDepth.BASIC, 0), summary.cachesReused(),
                        summary.callsPlanned(), summary.callsRealized(), summary.omittedByLimit(),
                        summary.failures().size(), summary.failureCategories(), summary.failures(), summary.omissionReasons());
                if (!summary.failures().isEmpty()) return 1;
            }
            return 0;
        } catch (RuntimeException failure) {
            System.err.println("Editorial batch failed: " + com.nflsideline.coreapi.llm.GenerationFailure.classify(failure));
            return 1;
        }
    }
}
