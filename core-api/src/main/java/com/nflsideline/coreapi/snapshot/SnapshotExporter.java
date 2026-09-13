package com.nflsideline.coreapi.snapshot;

import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Profile;

import java.io.IOException;
import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.SortedMap;
import java.util.TreeMap;

@Service
@Profile("snapshot")
public class SnapshotExporter {

    private final GameRepository gameRepository;
    private final TeamWeekMetricsRepository metricsRepository;
    private final AnalysisCacheRepository analysisRepository;
    private final SnapshotAssembler assembler;
    private final AtomicSnapshotWriter writer;
    private final Clock clock;

    @Autowired
    public SnapshotExporter(GameRepository gameRepository,
                            TeamWeekMetricsRepository metricsRepository,
                            AnalysisCacheRepository analysisRepository,
                            SnapshotAssembler assembler,
                            AtomicSnapshotWriter writer) {
        this(gameRepository, metricsRepository, analysisRepository, assembler, writer, Clock.systemUTC());
    }

    SnapshotExporter(GameRepository gameRepository,
                     TeamWeekMetricsRepository metricsRepository,
                     AnalysisCacheRepository analysisRepository,
                     SnapshotAssembler assembler,
                     AtomicSnapshotWriter writer,
                     Clock clock) {
        this.gameRepository = gameRepository;
        this.metricsRepository = metricsRepository;
        this.analysisRepository = analysisRepository;
        this.assembler = assembler;
        this.writer = writer;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public ExportResult export(SnapshotOptions options) throws IOException {
        OffsetDateTime generatedAt = OffsetDateTime.now(clock).withOffsetSameInstant(ZoneOffset.UTC);
        SortedMap<Integer, SnapshotContract.SeasonSnapshot> snapshots = new TreeMap<>();
        List<SeasonCounts> counts = new ArrayList<>();
        for (int season : options.seasons()) {
            List<Game> games = gameRepository.findAllBySeasonWithDetails(season);
            if (games.isEmpty() && !options.allowEmpty()) {
                throw new EmptySeasonException();
            }
            List<TeamWeekMetrics> metrics = metricsRepository.findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(season);
            List<String> gameIds = games.stream().map(Game::getGameId).toList();
            List<AnalysisCache> analyses = gameIds.isEmpty()
                    ? List.of()
                    : analysisRepository.findMatchupsForGameIds(gameIds);
            SnapshotAssembler.AssemblyResult assembly = assembler.assemble(
                    season, generatedAt, games, metrics, analyses);
            snapshots.put(season, assembly.snapshot());
            counts.add(new SeasonCounts(season, games.size(), assembly.snapshot().teams().size(),
                    assembly.metrics(), assembly.validAnalyses(), assembly.missingAnalyses(),
                    assembly.rejectedAnalyses()));
        }
        SnapshotContract.Manifest manifest = new SnapshotContract.Manifest(
                SnapshotContract.SCHEMA_VERSION, generatedAt,
                options.seasons().getLast(), options.seasons());
        AtomicSnapshotWriter.WriteResult writeResult = writer.write(options.outputDirectory(), manifest, snapshots);
        return new ExportResult(List.copyOf(counts), writeResult.changed(), writeResult.outputDirectory());
    }

    public record SeasonCounts(int season, int games, int teams, int metrics,
                               int validAnalyses, int missingAnalyses, int rejectedAnalyses) {
    }

    static final class EmptySeasonException extends IllegalStateException {
        EmptySeasonException() { super("Requested season has no games"); }
    }

    public record ExportResult(List<SeasonCounts> seasons, boolean changed,
                               java.nio.file.Path outputDirectory) {
    }
}
