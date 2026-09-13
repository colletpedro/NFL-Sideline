package com.nflsideline.coreapi.snapshot;

import com.nflsideline.coreapi.CoreApiApplication;
import com.nflsideline.coreapi.llm.GeminiClient;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.repository.IngestionRunsRepository;
import com.nflsideline.coreapi.repository.MarketImpliedRepository;
import com.nflsideline.coreapi.repository.TeamRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import com.nflsideline.coreapi.service.AnalysisService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class SnapshotBatchModeTest {

    @Test
    void snapshotProfileStartsWithoutGeminiOrWebAnalysisBeans() {
        new ApplicationContextRunner()
                .withInitializer(context -> context.getEnvironment().setActiveProfiles("snapshot"))
                .withPropertyValues("spring.autoconfigure.exclude="
                        + "org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration,"
                        + "org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration,"
                        + "org.springframework.boot.autoconfigure.data.jpa.JpaRepositoriesAutoConfiguration")
                .withUserConfiguration(CoreApiApplication.class)
                .withBean(GameRepository.class, () -> mock(GameRepository.class))
                .withBean(TeamWeekMetricsRepository.class, () -> mock(TeamWeekMetricsRepository.class))
                .withBean(AnalysisCacheRepository.class, () -> mock(AnalysisCacheRepository.class))
                .withBean(MarketImpliedRepository.class, () -> mock(MarketImpliedRepository.class))
                .withBean(TeamRepository.class, () -> mock(TeamRepository.class))
                .withBean(IngestionRunsRepository.class, () -> mock(IngestionRunsRepository.class))
                .run(context -> {
                    assertThat(context).hasNotFailed();
                    assertThat(context).doesNotHaveBean(GeminiClient.class);
                    assertThat(context).doesNotHaveBean(AnalysisService.class);
                    assertThat(context).hasSingleBean(SnapshotExporter.class);
                });
    }
}
