package com.nflsideline.coreapi.editorial;

import com.nflsideline.coreapi.domain.TeamWeekMetrics;
import java.math.BigDecimal;
import java.util.function.Function;

/** Explicit semantics of weekly observations. No metric here is a strength grade. */
public enum MetricCatalog {
    OFF_EPA_PLAY("EPA ofensivo por jogada", Unit.EPA, Direction.HIGHER, TeamWeekMetrics::getOffEpaPlay, TeamWeekMetrics::getPlaysOffense),
    OFF_EPA_PASS("EPA ofensivo por passe", Unit.EPA, Direction.HIGHER, TeamWeekMetrics::getOffEpaPass, null),
    OFF_EPA_RUSH("EPA ofensivo por corrida", Unit.EPA, Direction.HIGHER, TeamWeekMetrics::getOffEpaRush, null),
    DEF_EPA_PLAY("EPA permitido por jogada", Unit.EPA, Direction.LOWER, TeamWeekMetrics::getDefEpaPlay, TeamWeekMetrics::getPlaysDefense),
    DEF_EPA_PASS("EPA permitido por passe", Unit.EPA, Direction.LOWER, TeamWeekMetrics::getDefEpaPass, null),
    DEF_EPA_RUSH("EPA permitido por corrida", Unit.EPA, Direction.LOWER, TeamWeekMetrics::getDefEpaRush, null),
    OFF_SUCCESS_RATE("taxa de sucesso ofensiva", Unit.RATE, Direction.NONE, TeamWeekMetrics::getOffSuccessRate, TeamWeekMetrics::getPlaysOffense),
    DEF_SUCCESS_RATE("taxa de sucesso permitida pela defesa", Unit.RATE, Direction.NONE, TeamWeekMetrics::getDefSuccessRate, TeamWeekMetrics::getPlaysDefense),
    EARLY_DOWN_EPA("EPA em early downs", Unit.EPA, Direction.NONE, TeamWeekMetrics::getEarlyDownEpa, null),
    DROPBACK_RATE("frequência de dropback", Unit.RATE, Direction.NONE, TeamWeekMetrics::getDropbackRate, TeamWeekMetrics::getPlaysOffense),
    EXPLOSIVE_PLAY_RATE("taxa de jogadas explosivas", Unit.RATE, Direction.NONE, TeamWeekMetrics::getExplosivePlayRate, TeamWeekMetrics::getPlaysOffense);

    public enum Unit { EPA, RATE }
    public enum Direction { HIGHER, LOWER, NONE }
    private final String label;
    private final Unit unit;
    private final Direction direction;
    private final Function<TeamWeekMetrics, BigDecimal> getter;
    private final Function<TeamWeekMetrics, Integer> volumeGetter;

    MetricCatalog(String label, Unit unit, Direction direction,
                  Function<TeamWeekMetrics, BigDecimal> getter, Function<TeamWeekMetrics, Integer> volumeGetter) {
        this.label = label; this.unit = unit; this.direction = direction;
        this.getter = getter; this.volumeGetter = volumeGetter;
    }
    public String label() { return label; }
    public String definition() {
        return switch (this) {
            case OFF_EPA_PLAY -> "EPA ofensivo observado por jogada no recorte semanal";
            case OFF_EPA_PASS -> "EPA ofensivo observado por jogada de passe no recorte semanal";
            case OFF_EPA_RUSH -> "EPA ofensivo observado por jogada de corrida no recorte semanal";
            case DEF_EPA_PLAY -> "EPA permitido pela defesa por jogada no recorte semanal";
            case DEF_EPA_PASS -> "EPA permitido pela defesa por jogada de passe no recorte semanal";
            case DEF_EPA_RUSH -> "EPA permitido pela defesa por jogada de corrida no recorte semanal";
            case OFF_SUCCESS_RATE -> "fração de jogadas ofensivas com sucesso no recorte semanal";
            case DEF_SUCCESS_RATE -> "fração de jogadas do ataque adversário com EPA positivo no recorte semanal";
            case EARLY_DOWN_EPA -> "EPA observado em early downs no recorte semanal";
            case DROPBACK_RATE -> "fração de jogadas ofensivas com dropback no recorte semanal; estilo, sem direção de qualidade";
            case EXPLOSIVE_PLAY_RATE -> "fração de jogadas explosivas no recorte semanal";
        };
    }
    public Unit unit() { return unit; }
    public Direction direction() { return direction; }
    public BigDecimal value(TeamWeekMetrics row) { return getter.apply(row); }
    public Integer volume(TeamWeekMetrics row) { return volumeGetter == null ? null : volumeGetter.apply(row); }
    public boolean isOffenseEpa() { return name().startsWith("OFF_EPA_"); }
    public boolean isDefenseEpa() { return name().startsWith("DEF_EPA_"); }
    public boolean permitsDirectionalSupport() { return direction != Direction.NONE; }
    public boolean hasTotalPlayDenominator() {
        return this == OFF_EPA_PLAY || this == DEF_EPA_PLAY || this == OFF_SUCCESS_RATE
                || this == DEF_SUCCESS_RATE || this == DROPBACK_RATE || this == EXPLOSIVE_PLAY_RATE;
    }
    public MetricCatalog defensiveCounterpart() {
        return switch (this) {
            case OFF_EPA_PLAY -> DEF_EPA_PLAY;
            case OFF_EPA_PASS -> DEF_EPA_PASS;
            case OFF_EPA_RUSH -> DEF_EPA_RUSH;
            default -> null;
        };
    }
}
