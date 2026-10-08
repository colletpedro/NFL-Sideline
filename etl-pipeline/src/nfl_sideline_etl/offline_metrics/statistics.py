"""Exact, order-independent decimal sums; no rounded rates as input."""
from dataclasses import dataclass
from decimal import Decimal

from .validation import decimal_text

FOUNDATIONS = ("general", "classified_pass", "classified_rush")
COUNTS = ("eligible_n", "epa_n", "success_n", "epa_missing_n", "epa_nonfinite_n")


def exact_sum(values):
    values = list(values)
    if not values:
        return Decimal(0)
    exponent = min(v.as_tuple().exponent for v in values)
    coefficient = 0
    for value in values:
        sign, digits, exp = value.as_tuple()
        n = int(''.join(map(str, digits)))
        coefficient += (-n if sign else n) * 10 ** (exp - exponent)
    digits = tuple(map(int, str(abs(coefficient))))
    return Decimal((int(coefficient < 0), digits, exponent))


@dataclass
class Sums:
    eligible_n: int = 0
    epa_n: int = 0
    success_n: int = 0
    epa_missing_n: int = 0
    epa_nonfinite_n: int = 0
    epa_sum: Decimal = Decimal(0)

    def add(self, value):
        self.eligible_n += 1
        if value is None:
            self.epa_missing_n += 1
            return
        epa = Decimal(value)
        if not epa.is_finite():
            self.epa_nonfinite_n += 1
            return
        self.epa_n += 1
        self.success_n += int(epa > 0)
        self.epa_sum = exact_sum((self.epa_sum, epa))

    def merge(self, other):
        """Only after global dedup; disjoint unique play sets are required."""
        return Sums(**{key: getattr(self, key) + getattr(other, key) for key in COUNTS},
                    epa_sum=exact_sum((self.epa_sum, other.epa_sum)))

    def serialize(self):
        if self.eligible_n != self.epa_n + self.epa_missing_n + self.epa_nonfinite_n:
            raise ValueError("EPA partition invariant failed")
        if not 0 <= self.success_n <= self.epa_n:
            raise ValueError("Success invariant failed")
        return {**{key: getattr(self, key) for key in COUNTS},
                "epa_sum": decimal_text(self.epa_sum) if self.epa_n else None}


def accumulate(game, eligible):
    groups = {(team, role, f): Sums() for team in (game["home_team"], game["away_team"])
              for role in ("off", "def") for f in FOUNDATIONS}
    for play in eligible:
        foundation = "classified_pass" if play["play_type"] == "pass" else "classified_rush"
        for role, team in (("off", play["posteam"]), ("def", play["defteam"])):
            for f in ("general", foundation):
                groups[team, role, f].add(play["epa"])
    for team, role, f in groups:
        if f == "general":
            merged = groups[team, role, "classified_pass"].merge(groups[team, role, "classified_rush"])
            if groups[team, role, f].serialize() != merged.serialize():
                raise ValueError("general != pass + rush")
        opponent = game["away_team"] if team == game["home_team"] else game["home_team"]
        counterpart = "def" if role == "off" else "off"
        if groups[team, role, f].serialize() != groups[opponent, counterpart, f].serialize():
            raise ValueError("off != opponent def")
    return [{"team": team, "role": role, "foundation": f, **sums.serialize()}
            for (team, role, f), sums in sorted(groups.items())]
