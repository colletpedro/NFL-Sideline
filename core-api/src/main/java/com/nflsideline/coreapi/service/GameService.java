package com.nflsideline.coreapi.service;

import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.MarketImplied;
import com.nflsideline.coreapi.domain.Team;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.repository.MarketImpliedRepository;
import com.nflsideline.coreapi.repository.TeamWeekMetricsRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class GameService {

    private final GameRepository gameRepository;
    private final MarketImpliedRepository marketImpliedRepository;
    private final TeamWeekMetricsRepository metricsRepository;

    public GameService(GameRepository gameRepository,
                       MarketImpliedRepository marketImpliedRepository,
                       TeamWeekMetricsRepository metricsRepository) {
        this.gameRepository = gameRepository;
        this.marketImpliedRepository = marketImpliedRepository;
        this.metricsRepository = metricsRepository;
    }

    /**
     * Jogos de uma temporada, opcionalmente filtrados por semana.
     */
    public List<Game> findGames(Integer season, Integer week) {
        if (week == null) {
            return gameRepository.findBySeasonOrderByWeekAsc(season);
        }
        return gameRepository.findBySeasonAndWeek(season, week);
    }

    /**
     * Detalhe completo de um confronto: jogo, dados de mercado
     * ({@link MarketImplied}) e as métricas semanais de ambos os times
     * (contrato da spec §8 — "detalhe do jogo com métricas de ambos os times").
     */
    public Optional<GameDetail> findGameDetail(String gameId) {
        return gameRepository.findById(gameId)
                .map(game -> new GameDetail(
                        game,
                        marketImpliedRepository.findById(gameId).orElse(null),
                        weeklyMetrics(game, game.getHomeTeam()),
                        weeklyMetrics(game, game.getAwayTeam())));
    }

    /**
     * Série semanal (ordem crescente de semana) das métricas de um time na
     * temporada do jogo. Times ausentes (FK nula) retornam lista vazia.
     */
    private List<TeamWeekMetrics> weeklyMetrics(Game game, Team team) {
        if (team == null) {
            return List.of();
        }
        return metricsRepository
                .findByIdSeasonAndIdTeamAbbrOrderByIdWeekAsc(game.getSeason(), team.getTeamAbbr());
    }

    public record GameDetail(Game game, MarketImplied market,
                             List<TeamWeekMetrics> homeMetrics,
                             List<TeamWeekMetrics> awayMetrics) {
    }
}
