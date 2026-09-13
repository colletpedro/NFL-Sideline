package com.nflsideline.coreapi.snapshot;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
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
        when(analyses.findMatchupsForGameIds(any())).thenReturn(List.of());
        when(writer.write(any(), any(), anyMap())).thenReturn(new AtomicSnapshotWriter.WriteResult(true, output));
        SnapshotExporter exporter = exporter(games, metrics, analyses, writer);

        SnapshotExporter.ExportResult result = exporter.export(new SnapshotOptions(List.of(2026), output, false));

        assertThat(result.seasons().getFirst().games()).isEqualTo(3);
        verify(games).findAllBySeasonWithDetails(2026);
        verify(metrics).findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(2026);
        verify(analyses).findMatchupsForGameIds(any());
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

        assertThatThrownBy(() -> exporter.export(new SnapshotOptions(List.of(2026), output, false)))
                .isInstanceOf(IllegalStateException.class);
        verify(writer, never()).write(any(), any(), anyMap());

        when(metrics.findAllByIdSeasonOrderByIdTeamAbbrAscIdWeekAsc(2026)).thenReturn(List.of());
        when(writer.write(any(), any(), anyMap())).thenReturn(new AtomicSnapshotWriter.WriteResult(true, output));
        assertThat(exporter.export(new SnapshotOptions(List.of(2026), output, true)).seasons().getFirst().games())
                .isZero();
        verify(analyses, never()).findMatchupsForGameIds(any());
    }

    private SnapshotExporter exporter(GameRepository games, TeamWeekMetricsRepository metrics,
                                      AnalysisCacheRepository analyses, AtomicSnapshotWriter writer) {
        ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();
        return new SnapshotExporter(games, metrics, analyses, new SnapshotAssembler(mapper), writer,
                Clock.fixed(Instant.parse("2026-09-10T12:00:00Z"), ZoneOffset.UTC));
    }
}
