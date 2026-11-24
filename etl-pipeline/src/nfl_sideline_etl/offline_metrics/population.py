"""classified-scrimmage-v1; disjoint exclusion reasons, in contract order."""
from .validation import FLAGS

REASONS = dict(zip(FLAGS, ("kneel", "spike", "deleted", "special_teams", "two_point_conversion")))


def exclusion_reason(play):
    if play["play_type"] not in ("pass", "run"):
        return "outside_pass_run"
    for flag in FLAGS:
        if play[flag] == 1:
            return REASONS[flag]
    if any(play[flag] is None for flag in FLAGS):
        return "unknown_filter_flags"
    return None
