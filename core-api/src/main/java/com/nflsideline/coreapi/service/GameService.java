package com.nflsideline.coreapi.service;

import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.domain.MarketImplied;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.repository.MarketImpliedRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class GameService {

    private final GameRepository gameRepository;
    private final MarketImpliedRepository marketImpliedRepository;

    public GameService(GameRepository gameRepository, MarketImpliedRepository marketImpliedRepository) {
        this.gameRepository = gameRepository;
        this.marketImpliedRepository = marketImpliedRepository;
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
     * Detalhe completo de um confronto com seus dados de mercado
     * ({@link MarketImplied}), quando existirem.
     */
    public Optional<GameDetail> findGameDetail(String gameId) {
        return gameRepository.findById(gameId)
                .map(game -> new GameDetail(
                        game,
                        marketImpliedRepository.findById(gameId).orElse(null)));
    }

    public record GameDetail(Game game, MarketImplied market) {
    }
}
