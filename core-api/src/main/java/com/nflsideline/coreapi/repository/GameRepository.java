package com.nflsideline.coreapi.repository;

import com.nflsideline.coreapi.domain.Game;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface GameRepository extends JpaRepository<Game, String> {

    List<Game> findBySeasonAndWeek(Integer season, Integer week);

    List<Game> findBySeasonOrderByWeekAsc(Integer season);
}
