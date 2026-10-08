"""Raw structural validation and reconciliation, before population filters."""
from decimal import Decimal, InvalidOperation

from ..seasons import normalize_seasons

FLAGS = ("qb_kneel", "qb_spike", "play_deleted", "special_teams_play", "two_point_attempt")
PBP_FIELDS = ("game_id", "play_id", "drive", "season", "season_type", "week", "posteam", "defteam", "play_type", *FLAGS, "epa")
CALENDAR_FIELDS = ("game_id", "season", "game_type", "week", "home_team", "away_team")


def decimal_text(value):
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def number(value, field, *, nonfinite=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f"Invalid numeric {field}")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric {field}") from exc
    if not result.is_finite() and not nonfinite:
        raise ValueError(f"Nonfinite {field}")
    return result


def integer(value, field, *, minimum=0):
    result = number(value, field)
    if result != result.to_integral_value() or result < minimum:
        raise ValueError(f"Invalid integer {field}")
    return int(result)


def text(value, field, *, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"Invalid text {field}")
    return value


def phase_round(value):
    if value == "REG":
        return "REG", "REG"
    if value in ("POST", "WC", "DIV", "CON", "SB"):
        return "POST", None if value == "POST" else value
    raise ValueError(f"Unsupported phase {value!r}")


def require_fields(columns, fields):
    missing = sorted(set(fields) - set(columns))
    if missing:
        raise ValueError(f"Missing schema columns: {', '.join(missing)}")


def calendar_index(rows):
    games, duplicates = {}, {}
    for row in rows:
        require_fields(row, CALENDAR_FIELDS)
        game_id = text(row["game_id"], "game_id")
        phase, round_ = phase_round(row["game_type"])
        game = dict(game_id=game_id, season=integer(row["season"], "season", minimum=1999),
                    week=integer(row["week"], "week", minimum=1), phase=phase, round=round_,
                    home_team=text(row["home_team"], "home_team"), away_team=text(row["away_team"], "away_team"))
        if game["home_team"] == game["away_team"]:
            raise ValueError(f"Repeated calendar participant: {game_id}")
        if game_id in games:
            if games[game_id] != game:
                raise ValueError(f"Conflicting calendar identity: {game_id}")
            duplicates[game_id] = duplicates.get(game_id, 0) + 1
        games[game_id] = game
    if games:
        normalize_seasons(sorted({g["season"] for g in games.values()}))
    return games, duplicates


def normalize_play(row, games):
    require_fields(row, PBP_FIELDS)
    game_id = text(row["game_id"], "game_id")
    if game_id not in games:
        raise ValueError(f"PBP game absent from calendar: {game_id}")
    play = {"game_id": game_id, "play_id": decimal_text(number(row["play_id"], "play_id")),
            "drive": None if row["drive"] is None else decimal_text(number(row["drive"], "drive")),
            "season": integer(row["season"], "season", minimum=1999),
            "week": integer(row["week"], "week", minimum=1)}
    play["phase"], play["round"] = phase_round(row["season_type"])
    game = games[game_id]
    if any(play[k] != game[k] for k in ("season", "week", "phase")):
        raise ValueError(f"Calendar/PBP season, week or phase conflict: {game_id}")
    if play["round"] is not None and game["round"] is not None and play["round"] != game["round"]:
        raise ValueError(f"Calendar/PBP round conflict: {game_id}")
    for key in ("posteam", "defteam", "play_type"):
        play[key] = text(row[key], key, nullable=True)
    # Present structural values are validated even outside the population.
    participants = {game["home_team"], game["away_team"]}
    for key in ("posteam", "defteam"):
        if play[key] is not None and play[key] not in participants:
            raise ValueError(f"Wrong participant {key}: {game_id}")
    if play["posteam"] is not None and play["posteam"] == play["defteam"]:
        raise ValueError(f"Repeated play participant: {game_id}")
    if play["play_type"] in ("pass", "run") and {play["posteam"], play["defteam"]} != participants:
        raise ValueError(f"Missing or wrong candidate participants: {game_id}")
    for flag in FLAGS:
        value = row[flag]
        if value is None:
            play[flag] = None
        else:
            value = integer(value, flag)
            if value not in (0, 1):
                raise ValueError(f"Invalid binary flag {flag}: {game_id}")
            play[flag] = value
    value = row["epa"]
    if value is None:
        play["epa"] = None
    else:
        epa = number(value, "epa", nonfinite=True)
        play["epa"] = decimal_text(epa) if epa.is_finite() else str(epa)
    return play


def reconcile_raw(rows, games):
    """Dedup the entire normalized contractual projection, including excluded rows.

    No first/last conflict resolution; partitions are one revision, not alternatives.
    """
    unique, raw_n, duplicate_n = {}, {}, {}
    for row in rows:
        play = normalize_play(row, games)
        game_id = play["game_id"]
        raw_n[game_id] = raw_n.get(game_id, 0) + 1
        key = game_id, play["play_id"]
        if key in unique:
            if unique[key] != play:
                raise ValueError(f"Conflicting PBP replica (including drive): {key}")
            duplicate_n[game_id] = duplicate_n.get(game_id, 0) + 1
        unique[key] = play
    return sorted(unique.values(), key=lambda p: (p["game_id"], Decimal(p["play_id"]))), raw_n, duplicate_n
