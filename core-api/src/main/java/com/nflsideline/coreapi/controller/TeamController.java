package com.nflsideline.coreapi.controller;

import com.nflsideline.coreapi.domain.Team;
import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import com.nflsideline.coreapi.service.TeamService;
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
public class TeamController {

    private final TeamService teamService;

    public TeamController(TeamService teamService) {
        this.teamService = teamService;
    }

    @GetMapping("/teams")
    public List<Team> listTeams() {
        return teamService.findAll();
    }

    @GetMapping("/teams/{abbr}/metrics")
    public ResponseEntity<List<TeamWeekMetrics>> getTeamMetrics(
            @PathVariable String abbr,
            @RequestParam Integer season,
            @RequestParam(defaultValue = "season") String window) {
        if (!teamService.existsByAbbr(abbr)) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(teamService.findTeamMetrics(abbr, season, window));
    }
}
