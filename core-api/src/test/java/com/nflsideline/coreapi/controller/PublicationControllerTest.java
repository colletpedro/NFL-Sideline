package com.nflsideline.coreapi.controller;

import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.service.NflSeason;
import org.junit.jupiter.api.Test;
import java.time.Clock;
import java.time.OffsetDateTime;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class PublicationControllerTest {
    @Test
    void localContextUsesSharedSeasonAndActualUpdateInUtc() {
        var repository = mock(GameRepository.class);
        int season = NflSeason.current(Clock.systemUTC());
        when(repository.latestUpdatedAt(season)).thenReturn(OffsetDateTime.parse("2026-09-13T01:00:00-03:00"));
        var context = new PublicationController(repository).publication();
        assertThat(context.defaultSeason()).isEqualTo(season);
        assertThat(context.generatedAt().toString()).isEqualTo("2026-09-13T04:00Z");
        verify(repository).latestUpdatedAt(season);
        verifyNoMoreInteractions(repository);
    }

    @Test
    void missingDataDoesNotInventAnUpdateTime() {
        var context = new PublicationController(mock(GameRepository.class)).publication();
        assertThat(context.generatedAt()).isNull();
    }
}
