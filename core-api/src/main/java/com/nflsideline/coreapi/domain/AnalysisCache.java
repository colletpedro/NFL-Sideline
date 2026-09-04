package com.nflsideline.coreapi.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "analysis_cache")
public class AnalysisCache {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "game_id")
    private String gameId;

    @Column(name = "analysis_type", nullable = false)
    private String analysisType;

    @Column(name = "prompt_hash", nullable = false)
    private String promptHash;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "context_json", nullable = false)
    private String contextJson;

    @Column(name = "response_text", nullable = false)
    private String responseText;

    @Column(name = "model_name", nullable = false)
    private String modelName;

    @Column(name = "created_at", insertable = false, updatable = false)
    private OffsetDateTime createdAt;
}
