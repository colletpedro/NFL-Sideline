package com.nflsideline.coreapi.repository;

import com.nflsideline.coreapi.domain.MarketImplied;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MarketImpliedRepository extends JpaRepository<MarketImplied, String> {
}
