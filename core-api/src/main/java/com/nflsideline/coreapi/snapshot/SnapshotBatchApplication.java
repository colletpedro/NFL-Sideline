package com.nflsideline.coreapi.snapshot;

import com.nflsideline.coreapi.CoreApiApplication;
import org.springframework.boot.Banner;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import com.zaxxer.hikari.HikariDataSource;

import javax.sql.DataSource;

import java.time.Clock;
import java.util.Map;

public final class SnapshotBatchApplication {

    private SnapshotBatchApplication() {
    }

    public static int run(String[] args) {
        String stage = "options";
        try {
            SnapshotOptions options = SnapshotOptions.parse(args, Clock.systemUTC());
            stage = "startup";
            SpringApplicationBuilder builder = new SpringApplicationBuilder(CoreApiApplication.class)
                    .profiles("snapshot")
                    .web(WebApplicationType.NONE)
                    .bannerMode(Banner.Mode.OFF)
                    .logStartupInfo(false)
                    .properties(Map.of(
                            "spring.main.web-application-type", "none",
                            "spring.jpa.open-in-view", "false",
                            "logging.level.root", "OFF"));
            try (ConfigurableApplicationContext context = builder.run(
                    "--spring.datasource.hikari.read-only=true",
                    "--spring.jpa.properties.hibernate.jdbc.time_zone=UTC")) {
                assertReadOnlyDataSource(context.getBean(DataSource.class));
                stage = "export";
                SnapshotExporter.ExportResult result = context.getBean(SnapshotExporter.class).export(options);
                for (SnapshotExporter.SeasonCounts counts : result.seasons()) {
                    System.out.printf(
                            "season=%d games=%d teams=%d metrics=%d analyses_valid=%d analyses_missing=%d analyses_rejected=%d%n",
                            counts.season(), counts.games(), counts.teams(), counts.metrics(),
                            counts.validAnalyses(), counts.missingAnalyses(), counts.rejectedAnalyses());
                }
                System.out.printf("snapshot=%s changed=%s%n", result.outputDirectory(), result.changed());
            }
            return 0;
        } catch (Exception failure) {
            System.err.println(failureSummary(stage, failure));
            return 1;
        }
    }

    static String failureSummary(String stage, Exception failure) {
        String hint = switch (stage) {
            case "options" -> "INVALID_OPTIONS: check --season, --output and --allow-empty";
            case "startup" -> "STARTUP_FAILED: check PostgreSQL configuration, connectivity and read-only datasource";
            default -> "EXPORT_FAILED: check requested seasons and database availability";
        };
        Throwable cause = failure;
        for (int depth = 0; cause != null && depth < 20; depth++, cause = cause.getCause()) {
            if (cause instanceof java.sql.SQLException) {
                hint = "DATABASE_READ_FAILED: check connectivity, SELECT permissions and schema compatibility";
                break;
            }
            if (cause instanceof java.io.IOException) {
                hint = "OUTPUT_WRITE_FAILED: check output directory permissions and available disk space";
                break;
            }
            if (cause instanceof SnapshotExporter.EmptySeasonException) {
                hint = "EMPTY_SEASON: no games found; check season or explicitly use --allow-empty";
                break;
            }
        }
        // Only fixed diagnostics: never exception messages, URLs, SQL or payloads.
        return "Snapshot export failed: " + hint;
    }

    private static void assertReadOnlyDataSource(DataSource dataSource) {
        if (!(dataSource instanceof HikariDataSource hikariDataSource) || !hikariDataSource.isReadOnly()) {
            throw new IllegalStateException("Snapshot datasource must be read-only");
        }
    }
}
