"""Independent raw Parquet ledger. No adapter/writer/loader imports or database.

Exact arithmetic uses rational numbers, independently of the adapter accumulator.
"""
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path

FLAGS = ('qb_kneel', 'qb_spike', 'play_deleted', 'special_teams_play', 'two_point_attempt')
REASONS = ('kneel', 'spike', 'deleted', 'special_teams', 'two_point_conversion')
FIELDS = ('game_id','play_id','drive','season','season_type','week','posteam','defteam','play_type',*FLAGS,'epa')
COUNTS = ('eligible_n','epa_n','success_n','epa_missing_n','epa_nonfinite_n')
VERSIONS = dict(adapter='1.0.0', artifact='metrics-offline-v1', definition='1.0.0', population='classified-scrimmage-v1')


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def ident(value):
    return 'sha256:'+hashlib.sha256(encoded(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decimal(value, *, finite=True):
    if isinstance(value, bool):
        raise ValueError('boolean numeric')
    d = Decimal(str(value))
    if finite and not d.is_finite():
        raise ValueError('nonfinite identity')
    return d


def numeric(value):
    d = decimal(value, finite=False)
    if not d.is_finite():
        return str(d)
    return '0' if d == 0 else format(d, 'f').rstrip('0').rstrip('.') if '.' in format(d,'f') else format(d,'f')


def integer(value, minimum=0):
    d = decimal(value)
    if d != int(d) or d < minimum:
        raise ValueError('invalid integer')
    return int(d)


def phase(value):
    if value == 'REG':
        return 'REG','REG'
    if value in ('POST','WC','DIV','CON','SB'):
        return 'POST',None if value == 'POST' else value
    raise ValueError('invalid phase')


def text(value, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value,str) or not value or value.strip()!=value:
        raise ValueError('invalid text')
    return value


def parquet(path):
    import polars as pl
    return pl.read_parquet(path)


def ledger(calendar_paths, pbp_paths):
    games, cal_duplicates, unique, raw = {}, Counter(), {}, Counter()
    calendar_raw = 0
    for path in calendar_paths:
        for r in parquet(path).to_dicts():
            calendar_raw += 1
            p,rd = phase(r['game_type'])
            g = dict(game_id=text(r['game_id']),season=integer(r['season'],1999),week=integer(r['week'],1),phase=p,round=rd,
                     home_team=text(r['home_team']),away_team=text(r['away_team']))
            if g['home_team']==g['away_team']:
                raise ValueError('same calendar team')
            if g['game_id'] in games:
                if games[g['game_id']]!=g:
                    raise ValueError('calendar conflict')
                cal_duplicates[g['game_id']] += 1
            games[g['game_id']] = g
    for path in pbp_paths:
        frame=parquet(path)
        if not set(FIELDS)<=set(frame.columns):
            raise ValueError('missing PBP schema')
        for r in frame.select(FIELDS).to_dicts():
            gid=text(r['game_id']); g=games[gid]; p,rd=phase(r['season_type'])
            play=dict(game_id=gid,play_id=numeric(r['play_id']),drive=None if r['drive'] is None else numeric(r['drive']),
                      season=integer(r['season'],1999),week=integer(r['week'],1),phase=p,round=rd)
            decimal(r['play_id'])
            if r['drive'] is not None:decimal(r['drive'])
            if any(play[k]!=g[k] for k in ('season','week','phase')) or (rd and g['round'] and rd!=g['round']):
                raise ValueError('calendar join conflict')
            for k in ('posteam','defteam','play_type'):play[k]=text(r[k],nullable=True)
            teams={g['home_team'],g['away_team']}
            if any(play[k] is not None and play[k] not in teams for k in ('posteam','defteam')):
                raise ValueError('participant conflict')
            if play['posteam'] is not None and play['posteam']==play['defteam']:raise ValueError('same play team')
            if play['play_type'] in ('pass','run') and {play['posteam'],play['defteam']}!=teams:raise ValueError('missing candidate team')
            for k in FLAGS:
                v=None if r[k] is None else integer(r[k])
                if v not in (None,0,1):raise ValueError('flag conflict')
                play[k]=v
            play['epa']=None if r['epa'] is None else numeric(r['epa'])
            key=(gid,play['play_id']); raw[gid]+=1
            if key in unique and unique[key]!=play:raise ValueError('PBP replica conflict')
            unique[key]=play
    by_game=defaultdict(list)
    for row in sorted(unique.values(),key=lambda r:(r['game_id'],Decimal(r['play_id']))):by_game[row['game_id']].append(row)
    audits,stats={},{}
    for gid,g in sorted(games.items()):
        rows=by_game[gid]; reasons=Counter(); outside_null=0
        groups={(t,r,f):dict.fromkeys(COUNTS,0)|{'epa_sum':Fraction(0)} for t in (g['home_team'],g['away_team'])
                for r in ('off','def') for f in ('general','classified_pass','classified_rush')}
        for row in rows:
            reason='outside_pass_run' if row['play_type'] not in ('pass','run') else next((reason for flag,reason in zip(FLAGS,REASONS) if row[flag]==1),None)
            if reason is None and any(row[f] is None for f in FLAGS):reason='unknown_filter_flags'
            if reason:
                reasons[reason]+=1
                outside_null+=int(reason=='outside_pass_run' and (row['posteam'] is None or row['defteam'] is None))
                continue
            for team,role in ((row['posteam'],'off'),(row['defteam'],'def')):
                for f in ('general','classified_pass' if row['play_type']=='pass' else 'classified_rush'):
                    s=groups[team,role,f];s['eligible_n']+=1
                    if row['epa'] is None:s['epa_missing_n']+=1
                    elif not Decimal(row['epa']).is_finite():s['epa_nonfinite_n']+=1
                    else:
                        s['epa_n']+=1;s['success_n']+=int(Decimal(row['epa'])>0);s['epa_sum']+=Fraction(Decimal(row['epa']))
        for (team,role,f),s in groups.items():
            assert s['eligible_n']==s['epa_n']+s['epa_missing_n']+s['epa_nonfinite_n']
            if f=='general':assert all(s[k]==groups[team,role,'classified_pass'][k]+groups[team,role,'classified_rush'][k] for k in (*COUNTS,'epa_sum'))
            opponent=g['away_team'] if team==g['home_team'] else g['home_team']
            assert s==groups[opponent,'def' if role=='off' else 'off',f]
            if rows:stats[gid,team,role,f]=s
        audits[gid]=dict(**g,raw_n=raw[gid],unique_n=len(rows),duplicate_rows_ignored=raw[gid]-len(rows),
            calendar_duplicate_rows_ignored=cal_duplicates[gid],exclusions=dict(reasons),excluded_n=sum(reasons.values()),
            eligible_content_n=len(rows)-sum(reasons.values()) if rows else None,unknown_filter_flags_n=reasons['unknown_filter_flags'],
            outside_pass_run_null_teams_n=outside_null,pbp_content_id=ident(rows))
    return dict(games=games,audits=audits,statistics=stats,calendar_raw_n=calendar_raw)


def compare(led, audits, statistics, manifest):
    assert set(led['games'])=={a['game_id'] for a in audits}
    sets={kind:ident(sorted('sha256:'+d['sha256'] for d in manifest['inputs'] if d['kind']==kind)) for kind in ('calendar','pbp')}
    for a in audits:
        expected=led['audits'][a['game_id']]
        for key,value in expected.items():assert a[key]==value,(a['game_id'],key,a[key],value)
        assert a['completeness']=='UNKNOWN' and a['expected_unique_rows'] is None
        assert all(a['provenance'][k] is None for k in ('available_at','ingested_at','event_upper_bound'))
        assert a['calendar_revision_id']==sets['calendar'] and a['pbp_revision_id']==sets['pbp']
        revision=ident(dict(game=led['games'][a['game_id']],calendar_revision=sets['calendar'],pbp_revision=sets['pbp'],
                            content_id=expected['pbp_content_id'],provenance={},versions=VERSIONS))
        assert a['coverage_revision_id']==revision
    actual={}
    for s in statistics:
        key=tuple(s[k] for k in ('game_id','team','role','foundation'))
        assert key not in actual
        actual[key]={k:s[k] for k in COUNTS}|{'epa_sum':Fraction(Decimal(s['epa_sum'])) if s['epa_sum'] is not None else Fraction(0)}
        assert (s['epa_sum'] is None)==(s['epa_n']==0)
        assert s['scope']=='AUDITABLE_SUBSET' and s['completeness']=='UNKNOWN'
    assert actual==led['statistics'],'independent sufficient statistics differ'
    return sets


def summary(led):
    audits=list(led['audits'].values());off=[s for (g,t,r,f),s in led['statistics'].items() if r=='off' and f=='general']
    return dict(calendar_games_n=len(audits),calendar_raw_n=led['calendar_raw_n'],observed_games_n=sum(a['unique_n']>0 for a in audits),
        calendar_without_pbp=sorted(a['game_id'] for a in audits if not a['unique_n']),pbp_raw_n=sum(a['raw_n'] for a in audits),
        pbp_unique_n=sum(a['unique_n'] for a in audits),duplicate_rows_ignored=sum(a['duplicate_rows_ignored'] for a in audits),
        excluded_n=sum(a['excluded_n'] for a in audits),eligible_content_n=sum(s['eligible_n'] for s in off),
        exclusions=dict(sum((Counter(a['exclusions']) for a in audits),Counter())),statistics_records_n=len(led['statistics']),
        finite_epa_n=sum(s['epa_n'] for s in off),missing_epa_n=sum(s['epa_missing_n'] for s in off),
        nonfinite_epa_n=sum(s['epa_nonfinite_n'] for s in off),exact_epa_sum=str(sum((s['epa_sum'] for s in off),Fraction(0))),
        unknown_filter_flags_n=sum(a['unknown_filter_flags_n'] for a in audits))
