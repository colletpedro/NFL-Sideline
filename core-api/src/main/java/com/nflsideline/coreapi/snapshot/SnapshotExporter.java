package com.nflsideline.coreapi.snapshot;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import com.nflsideline.coreapi.editorial.ApprovedAnalysisSelector;
import com.nflsideline.coreapi.editorial.EditorialManifest;
import com.nflsideline.coreapi.editorial.EditorialManifestLoader;
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
import java.util.Map;

@Service
@Profile("snapshot")
public class SnapshotExporter {

    private final GameRepository gameRepository;
    private final TeamWeekMetricsRepository metricsRepository;
    private final AnalysisCacheRepository analysisRepository;
    private final SnapshotAssembler assembler;
    private final AtomicSnapshotWriter writer;
    private final EditorialManifestLoader manifestLoader;
    private final ApprovedAnalysisSelector analysisSelector;
    private final Clock clock;

    @Autowired
    public SnapshotExporter(GameRepository gameRepository,
                            TeamWeekMetricsRepository metricsRepository,
                            AnalysisCacheRepository analysisRepository,
                            SnapshotAssembler assembler,
                            AtomicSnapshotWriter writer,
                            EditorialManifestLoader manifestLoader,
                            ApprovedAnalysisSelector analysisSelector) {
        this(gameRepository, metricsRepository, analysisRepository, assembler, writer,
                manifestLoader, analysisSelector, Clock.systemUTC());
    }

    SnapshotExporter(GameRepository gameRepository,
                     TeamWeekMetricsRepository metricsRepository,
                     AnalysisCacheRepository analysisRepository,
                     SnapshotAssembler assembler,
                     AtomicSnapshotWriter writer,
                     EditorialManifestLoader manifestLoader,
                     ApprovedAnalysisSelector analysisSelector,
                     Clock clock) {
        this.gameRepository = gameRepository;
        this.metricsRepository = metricsRepository;
        this.analysisRepository = analysisRepository;
        this.assembler = assembler;
        this.writer = writer;
        this.manifestLoader = manifestLoader;
        this.analysisSelector = analysisSelector;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public ExportResult export(SnapshotOptions options) throws IOException {
        OffsetDateTime generatedAt = OffsetDateTime.now(clock).withOffsetSameInstant(ZoneOffset.UTC);
        SortedMap<Integer, SnapshotContract.SeasonSnapshot> snapshots = new TreeMap<>();
        List<SeasonCounts> counts = new ArrayList<>();
        EditorialManifestLoader.LoadResult manifest = manifestLoader.load();
        if (!manifest.validRoot()) {
            throw new InvalidEditorialManifestException();
        }
        for (int season : options.seasons()) {
            List<Game> games = gameRepository.findAllBySeasonWithDetails(season);
            if (games.isEmpty() && !options.allowEmpty()) {
                throw new EmptySeasonException();
            }
            List<TeamWeekMetrics> metrics = metricsRepository.findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(season);
            List<EditorialManifest.Selection> approvals = manifest.selections().stream()
                    .filter(selection -> games.stream().anyMatch(game -> game.getGameId().equals(selection.gameId())))
                    .toList();
            List<Long> cacheIds = approvals.stream().map(EditorialManifest.Selection::analysisCacheId).toList();
            List<AnalysisCache> caches = cacheIds.isEmpty()
                    ? List.of()
                    : analysisRepository.findAllByIdIn(cacheIds);
            ApprovedAnalysisSelector.SelectionResult selected = analysisSelector.select(
                    games, options.asOfDate(), approvals, caches,
                    previouslyPublished(options.outputDirectory(), season));
            SnapshotAssembler.AssemblyResult assembly = assembler.assemble(
                    season, generatedAt, games, metrics, selected.analyses());
            snapshots.put(season, assembly.snapshot());
            counts.add(new SeasonCounts(season, games.size(), assembly.snapshot().teams().size(),
                    assembly.metrics(), assembly.validAnalyses(), assembly.missingAnalyses(),
                    assembly.rejectedAnalyses() + selected.problems().size() + manifest.problems().size()));
        }
        SnapshotContract.Manifest snapshotManifest = new SnapshotContract.Manifest(
                SnapshotContract.SCHEMA_VERSION, generatedAt,
                options.seasons().getLast(), options.seasons());
        AtomicSnapshotWriter.WriteResult writeResult = writer.write(options.outputDirectory(), snapshotManifest, snapshots);
        return new ExportResult(List.copyOf(counts), writeResult.changed(), writeResult.outputDirectory());
    }

    private Map<String, ApprovedAnalysisSelector.PublishedAnalysis> previouslyPublished(
            java.nio.file.Path outputDirectory, int season) {
        java.nio.file.Path snapshot = outputDirectory.resolve("seasons").resolve(season + ".json");
        if (!java.nio.file.Files.isRegularFile(snapshot)) {
            return Map.of();
        }
        try {
            JsonNode analyses = new ObjectMapper().findAndRegisterModules().readTree(snapshot.toFile())
                    .path("analysesByGame");
            if (!analyses.isObject()) return Map.of();
            Map<String, ApprovedAnalysisSelector.PublishedAnalysis> result = new java.util.HashMap<>();
            analyses.fields().forEachRemaining(entry -> {
                JsonNode value = entry.getValue();
                try {
                    if (!value.path("fatorChave").isTextual() || !value.path("vantagemTatica").isTextual()
                            || !value.path("alertaVermelho").isTextual() || !value.path("veredito").isTextual()
                            || value.path("fatorChave").asText().isBlank()
                            || value.path("vantagemTatica").asText().isBlank()
                            || value.path("alertaVermelho").asText().isBlank()
                            || value.path("veredito").asText().isBlank()) {
                        return;
                    }
                    result.put(entry.getKey(), new ApprovedAnalysisSelector.PublishedAnalysis(
                            OffsetDateTime.parse(value.path("createdAt").asText()),
                            value.path("fatorChave").asText(), value.path("vantagemTatica").asText(),
                            value.path("alertaVermelho").asText(), value.path("veredito").asText()));
                } catch (RuntimeException ignored) {
                    // A malformed previous entry cannot serve as grandfathering evidence.
                }
            });
            return Map.copyOf(result);
        } catch (IOException failure) {
            return Map.of();
        }
    }

    public record SeasonCounts(int season, int games, int teams, int metrics,
                               int validAnalyses, int missingAnalyses, int rejectedAnalyses) {
    }

    static final class EmptySeasonException extends IllegalStateException {
        EmptySeasonException() { super("Requested season has no games"); }
    }

    static final class InvalidEditorialManifestException extends IllegalStateException {
        InvalidEditorialManifestException() { super("Editorial manifest is unavailable or invalid"); }
    }

    public record ExportResult(List<SeasonCounts> seasons, boolean changed,
                               java.nio.file.Path outputDirectory) {
    }
}
