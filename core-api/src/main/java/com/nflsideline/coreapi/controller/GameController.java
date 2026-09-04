package com.nflsideline.coreapi.controller;

import com.nflsideline.coreapi.domain.Game;
import com.nflsideline.coreapi.service.GameService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
@CrossOrigin
public class GameController {

    private final GameService gameService;

    public GameController(GameService gameService) {
        this.gameService = gameService;
    }

    @GetMapping("/games")
    public List<Game> listGames(
            @RequestParam Integer season,
            @RequestParam(required = false) Integer week) {
        return gameService.findGames(season, week);
    }

    @GetMapping("/games/{gameId}")
    public ResponseEntity<GameService.GameDetail> getGame(@PathVariable String gameId) {
        return gameService.findGameDetail(gameId)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
