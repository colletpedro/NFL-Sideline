"""Exact ISO instants and explicit Eastern calendar conversion."""
from datetime import datetime, timezone
from fractions import Fraction
import re
from zoneinfo import ZoneInfo

ISO = re.compile(r'^(\d{4}-\d\d-\d\d)T(\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)$')


def instant(value):
    """Fractional epoch seconds; never truncate sub-microsecond evidence."""
    if not isinstance(value, str) or not (match := ISO.fullmatch(value)):
        raise ValueError('Instant requires ISO date, seconds and timezone')
    day, clock, fraction, offset = match.groups()
    if offset != 'Z' and (int(offset[1:3]) > 23 or int(offset[4:]) > 59):
        raise ValueError('Invalid timezone offset')
    base = datetime.fromisoformat(day + 'T' + clock + ('+00:00' if offset == 'Z' else offset))
    delta = base.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return Fraction(delta.days * 86400 + delta.seconds) + (Fraction(fraction) if fraction else 0)


def utc_seconds(value):
    parsed = instant(value)
    if parsed.denominator != 1 or '.' in value:
        raise ValueError('Cutoff must have whole-second precision')
    return datetime.fromtimestamp(int(parsed), timezone.utc).isoformat().replace('+00:00', 'Z')


def cutoff(request):
    if ('asOfInstant' in request) == ('asOfDate' in request):
        raise ValueError('Exactly one explicit asOfInstant/asOfDate is required')
    if 'asOfDate' in request:
        day = request['asOfDate']
        if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d\d-\d\d', day):
            raise ValueError('Invalid asOfDate')
        value = utc_seconds(day + 'T00:00:00Z')
        return value, {'asOfDate': day, 'mappedAsOfInstant': value}
    return utc_seconds(request['asOfInstant']), None


def eastern_kickoff(gameday, gametime):
    if gametime is None:
        return None
    if not isinstance(gametime, str) or not re.fullmatch(r'\d\d:\d\d(:\d\d)?', gametime):
        raise ValueError('Invalid calendar gametime')
    naive = datetime.fromisoformat(gameday + 'T' + gametime)
    zone = ZoneInfo('America/New_York')
    candidates = set()
    for fold in (0, 1):
        local = naive.replace(tzinfo=zone, fold=fold)
        utc = local.astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) == naive:
            candidates.add(utc)
    if len(candidates) != 1:
        raise ValueError('Ambiguous or nonexistent America/New_York kickoff')
    return candidates.pop().isoformat().replace('+00:00', 'Z')
