package com.nflsideline.coreapi.snapshot;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import com.nflsideline.coreapi.editorial.ApprovedAnalysisSelector;
import com.nflsideline.coreapi.editorial.EditorialManifestLoader;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.nio.file.Files;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.LocalDate;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class SnapshotExporterTest {

    @TempDir
    Path temporaryDirectory;

    @Test
    void performsThreeBatchQueriesIndependentOfGameCount() throws Exception {
        GameRepository games = mock(GameRepository.class);
        TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
        AnalysisCacheRepository analyses = mock(AnalysisCacheRepository.class);
        AtomicSnapshotWriter writer = mock(AtomicSnapshotWriter.class);
        Path output = temporaryDirectory.resolve("data");
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(List.of(
                SnapshotFixtures.game("g1", 1, "AAA", "BBB"),
                SnapshotFixtures.game("g2", 1, "CCC", "DDD"),
                SnapshotFixtures.game("g3", 2, "AAA", "CCC")));
        when(metrics.findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(2026)).thenReturn(List.of());
        when(writer.write(any(), any(), anyMap())).thenReturn(new AtomicSnapshotWriter.WriteResult(true, output));
        SnapshotExporter exporter = exporter(games, metrics, analyses, writer);

        SnapshotExporter.ExportResult result = exporter.export(options(output, false));

        assertThat(result.seasons().getFirst().games()).isEqualTo(3);
        verify(games).findAllBySeasonWithDetails(2026);
        verify(metrics).findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(2026);
        verify(analyses, never()).findAllByIdIn(any());
    }

    @Test
    void emptySeasonFailsUnlessAllowEmptyIsExplicit() throws Exception {
        GameRepository games = mock(GameRepository.class);
        TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
        AnalysisCacheRepository analyses = mock(AnalysisCacheRepository.class);
        AtomicSnapshotWriter writer = mock(AtomicSnapshotWriter.class);
        Path output = temporaryDirectory.resolve("data");
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(List.of());
        SnapshotExporter exporter = exporter(games, metrics, analyses, writer);

        assertThatThrownBy(() -> exporter.export(options(output, false)))
                .isInstanceOf(IllegalStateException.class);
        verify(writer, never()).write(any(), any(), anyMap());

        when(metrics.findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(2026)).thenReturn(List.of());
        when(writer.write(any(), any(), anyMap())).thenReturn(new AtomicSnapshotWriter.WriteResult(true, output));
        assertThat(exporter.export(options(output, true)).seasons().getFirst().games())
                .isZero();
        verify(analyses, never()).findAllByIdIn(any());
    }

    @Test
    void missingOrInvalidRootManifestFailsClosedWithoutQueriesWriterOrOutputChanges() throws Exception {
        for (String problem : List.of("manifest_missing", "manifest_invalid")) {
            GameRepository games = mock(GameRepository.class);
            TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
            AnalysisCacheRepository analyses = mock(AnalysisCacheRepository.class);
            AtomicSnapshotWriter writer = mock(AtomicSnapshotWriter.class);
            EditorialManifestLoader loader = mock(EditorialManifestLoader.class);
            when(loader.load()).thenReturn(EditorialManifestLoader.LoadResult.rootFailure(problem));
            Path output = temporaryDirectory.resolve(problem).resolve("data");
            Files.createDirectories(output);
            Path sentinel = output.resolve("sentinel.txt");
            Files.writeString(sentinel, "unchanged");
            SnapshotExporter exporter = new SnapshotExporter(games, metrics, analyses,
                    new SnapshotAssembler(new ObjectMapper().findAndRegisterModules()), writer, loader,
                    new ApprovedAnalysisSelector(),
                    Clock.fixed(Instant.parse("2026-09-10T12:00:00Z"), ZoneOffset.UTC));

            assertThatThrownBy(() -> exporter.export(options(output, false)))
                    .isInstanceOf(SnapshotExporter.InvalidEditorialManifestException.class);
            assertThat(Files.readString(sentinel)).isEqualTo("unchanged");
            verify(games, never()).findAllBySeasonWithDetails(anyInt());
            verify(writer, never()).write(any(), any(), anyMap());
        }
    }

    @Test
    void selectionUsesExplicitAsOfInsteadOfGeneratedAtDate() throws Exception {
        GameRepository games = mock(GameRepository.class);
        TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
        AnalysisCacheRepository analyses = mock(AnalysisCacheRepository.class);
        AtomicSnapshotWriter writer = mock(AtomicSnapshotWriter.class);
        EditorialManifestLoader loader = mock(EditorialManifestLoader.class);
        ApprovedAnalysisSelector selector = mock(ApprovedAnalysisSelector.class);
        Path output = temporaryDirectory.resolve("explicit-as-of");
        when(loader.load()).thenReturn(new EditorialManifestLoader.LoadResult(true, List.of(), List.of()));
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(List.of(
                SnapshotFixtures.game("g1", 1, "AAA", "BBB")));
        when(metrics.findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(2026)).thenReturn(List.of());
        when(selector.select(anyList(), eq(LocalDate.parse("2026-09-15")), anyList(), anyList(), anyMap()))
                .thenReturn(new ApprovedAnalysisSelector.SelectionResult(List.of(), List.of()));
        when(writer.write(any(), any(), anyMap())).thenReturn(new AtomicSnapshotWriter.WriteResult(true, output));
        SnapshotExporter exporter = new SnapshotExporter(games, metrics, analyses,
                new SnapshotAssembler(new ObjectMapper().findAndRegisterModules()), writer, loader, selector,
                Clock.fixed(Instant.parse("2026-09-10T12:00:00Z"), ZoneOffset.UTC));

        exporter.export(options(output, false));

        verify(selector).select(anyList(), eq(LocalDate.parse("2026-09-15")),
                anyList(), anyList(), anyMap());
    }

    @Test
    void invalidIndividualSelectionIsReportedButCalendarIsStillWritten() throws Exception {
        GameRepository games = mock(GameRepository.class);
        TeamWeekMetricsRepository metrics = mock(TeamWeekMetricsRepository.class);
        AnalysisCacheRepository analyses = mock(AnalysisCacheRepository.class);
        AtomicSnapshotWriter writer = mock(AtomicSnapshotWriter.class);
        EditorialManifestLoader loader = mock(EditorialManifestLoader.class);
        Path output = temporaryDirectory.resolve("individual-invalid");
        when(loader.load()).thenReturn(new EditorialManifestLoader.LoadResult(
                true, List.of(), List.of("invalid_selection")));
        when(games.findAllBySeasonWithDetails(2026)).thenReturn(List.of(
                SnapshotFixtures.game("g1", 1, "AAA", "BBB")));
        when(metrics.findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(2026)).thenReturn(List.of());
        when(writer.write(any(), any(), anyMap())).thenReturn(new AtomicSnapshotWriter.WriteResult(true, output));

        var result = new SnapshotExporter(games, metrics, analyses,
                new SnapshotAssembler(new ObjectMapper().findAndRegisterModules()), writer, loader,
                new ApprovedAnalysisSelector(),
                Clock.fixed(Instant.parse("2026-09-10T12:00:00Z"), ZoneOffset.UTC))
                .export(options(output, false));

        assertThat(result.seasons().getFirst().games()).isOne();
        assertThat(result.seasons().getFirst().rejectedAnalyses()).isOne();
        verify(writer).write(any(), any(), anyMap());
    }

    private SnapshotExporter exporter(GameRepository games, TeamWeekMetricsRepository metrics,
                                      AnalysisCacheRepository analyses, AtomicSnapshotWriter writer) {
        ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();
        EditorialManifestLoader loader = mock(EditorialManifestLoader.class);
        when(loader.load()).thenReturn(new EditorialManifestLoader.LoadResult(true, List.of(), List.of()));
        return new SnapshotExporter(games, metrics, analyses, new SnapshotAssembler(mapper), writer,
                loader, new ApprovedAnalysisSelector(),
                Clock.fixed(Instant.parse("2026-09-10T12:00:00Z"), ZoneOffset.UTC));
    }

    private SnapshotOptions options(Path output, boolean allowEmpty) {
        return new SnapshotOptions(List.of(2026), output, allowEmpty, LocalDate.parse("2026-09-15"));
    }
}
