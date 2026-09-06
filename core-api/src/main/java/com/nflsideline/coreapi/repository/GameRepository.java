package com.nflsideline.coreapi.repository;

import com.nflsideline.coreapi.domain.Game;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface GameRepository extends JpaRepository<Game, String> {

    @Query("SELECT g FROM Game g JOIN FETCH g.homeTeam JOIN FETCH g.awayTeam LEFT JOIN FETCH g.marketImplied WHERE g.season = :season AND g.week = :week")
    List<Game> findBySeasonAndWeekWithDetails(@Param("season") Integer season, @Param("week") Integer week);

    @Query("SELECT g FROM Game g JOIN FETCH g.homeTeam JOIN FETCH g.awayTeam LEFT JOIN FETCH g.marketImplied WHERE g.season = :season ORDER BY g.week ASC, g.gameday ASC")
    List<Game> findAllBySeasonWithDetails(@Param("season") int season);

    @Query("SELECT g FROM Game g JOIN FETCH g.homeTeam JOIN FETCH g.awayTeam LEFT JOIN FETCH g.marketImplied WHERE g.id = :id")
    Optional<Game> findByIdWithDetails(@Param("id") String id);

    List<Game> findBySeasonAndWeek(Integer season, Integer week);

    List<Game> findBySeasonOrderByWeekAsc(Integer season);
}
