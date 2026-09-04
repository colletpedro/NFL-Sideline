package com.nflsideline.coreapi.repository;

import com.nflsideline.coreapi.domain.Team;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TeamRepository extends JpaRepository<Team, String> {
}
