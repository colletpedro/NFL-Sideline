"""Preserved eligibility; independent raw SQL reconciliation of the NEW target."""
import sqlite3
import pandas as pd
from common import *

CONTEXT = RAW
KEEP = KEY + ['season','season_type','week','game_date','passer_player_id','passer_player_name',
    'posteam','defteam','interception','is_interception_worthy','desc','penalty','penalty_type',
    'aborted_play','complete_pass','incomplete_pass'] + CONTEXT

def renamed(ft): return ft.rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})

def join(p, f):
    unique(p,KEY,'PBP'); unique(f,KEY,'FTN')
    if not f.is_interception_worthy.dropna().isin([True,False,0,1]).all(): raise ValueError('Nonbinary FTN label')
    shared=p[KEY+['season','week']].merge(f[KEY+['season','week']],on=KEY,validate='one_to_one',suffixes=('_p','_f'))
    if not (shared.season_p.eq(shared.season_f)&shared.week_p.eq(shared.week_f)).all(): raise ValueError('FTN/PBP temporal metadata mismatch')
    d=p.loc[eligible(p)].merge(f[KEY+['is_interception_worthy']],on=KEY,how='left',validate='one_to_one',indicator=True)
    if not d.interception.dropna().isin([0,1]).all(): raise ValueError('Nonbinary PBP interception')
    return d

def validate_rows(d):
    if d[['is_interception_worthy','interception','passer_player_id']].isna().any().any(): raise ValueError('Missing label, target, or GSIS; never impute')
    if not d.passer_player_id.str.fullmatch(r'00-\d{7}').all(): raise ValueError('Invalid GSIS')
    for c,lo,hi in [('down',1,4),('qtr',1,5),('ydstogo',0,100),('yardline_100',0,100),('quarter_seconds_remaining',0,900),('score_differential',-100,100)]:
        if not pd.to_numeric(d[c],errors='coerce').dropna().between(lo,hi).all(): raise ValueError(f'Context range {c}')
    if not (d.score_differential.eq(d.posteam_score-d.defteam_score)).all(): raise ValueError('Pre-play score mismatch')
    if not (d.posteam.ne(d.defteam)&d.posteam.notna()&d.defteam.notna()).all(): raise ValueError('Team identity mismatch')
    return d

def current_frames(p,f,s):
    """Closed game gate follows lab, without running M3 or touching its package."""
    if not p.season.eq(2026).all() or not f.season.eq(2026).all(): raise ValueError('Current season mismatch')
    all_d=join(p,f)
    sc=s[s.season.eq(2026)&s.game_type.eq('REG')].sort_values(['week','game_id'])
    if len(sc)!=272 or sc.game_id.duplicated().any(): raise ValueError('REG calendar universe/identity changed')
    scores=sc[['home_score','away_score','result']]
    if not scores.notna().sum(axis=1).isin([0,3]).all(): raise ValueError('Partial schedule score trio')
    completed=sc[scores.notna().all(axis=1)]
    if not completed.result.eq(completed.home_score-completed.away_score).all(): raise ValueError('Schedule result inconsistent')
    if not set(p[p.season_type.eq('REG')].game_id).issubset(set(sc.game_id)): raise ValueError('PBP outside schedule')
    selected=[]; included=[]; gaps=[]; future=[]
    for g in sc.itertuples():
        meta=dict(game_id=g.game_id,week=int(g.week),date=str(g.gameday),home=g.home_team,away=g.away_team)
        if pd.isna(g.home_score): future.append(meta); continue
        raw=p[p.game_id.eq(g.game_id)]; d=all_d[all_d.game_id.eq(g.game_id)].copy()
        reason=None
        if raw.empty: reason='PBP absent'
        elif not raw.week.eq(g.week).all() or not (raw.home_team.eq(g.home_team)&raw.away_team.eq(g.away_team)&raw.game_date.astype(str).eq(str(g.gameday))).all(): raise ValueError('Calendar/PBP identity conflict')
        else:
            end=raw[raw.desc.eq('END GAME')]
            if len(end)!=1 or end[['total_home_score','total_away_score']].isna().any().any(): reason='PBP end marker absent'
            elif not (end.total_home_score.eq(g.home_score)&end.total_away_score.eq(g.away_score)).all(): raise ValueError('PBP final score inconsistent')
            elif d.empty: reason='No eligible attempts'
            elif d.is_interception_worthy.isna().any(): reason='FTN absent/incomplete'
            elif d.interception.isna().any(): reason='PBP interception target absent'
            elif d.passer_player_id.isna().any(): reason='GSIS absent'
            elif d[CONTEXT].isna().any().any(): reason='Pre-play context incomplete (same game gate as lab)'
        if reason: gaps.append(dict(**meta,reason=reason,eligible_passes=len(d),missing_ftn=int(d.is_interception_worthy.isna().sum()),missing_target=int(d.interception.isna().sum()))); continue
        validate_rows(d)
        if not (d.posteam.isin([g.home_team,g.away_team])&d.defteam.isin([g.home_team,g.away_team])).all(): raise ValueError('Pass team/calendar conflict')
        selected.append(d); included.append(dict(**meta,passes=len(d)))
    if not selected: raise ValueError('No usable current games')
    return pd.concat(selected,ignore_index=True),dict(completed_games=len(completed),included_games=len(included),
        included=included,pending_games=gaps,scheduled_games=future,weeks=sorted({g['week'] for g in included}),
        completed_through=str(completed.gameday.max()),pbp_weeks=sorted(p.week.unique().astype(int).tolist()),ftn_weeks=sorted(f.week.unique().astype(int).tolist()))

def independent(p,f,d):
    """Independent WHERE and LEFT JOIN from RAW inputs, not the derived cross table."""
    cols=KEY+['season','week','season_type','play_type','pass_attempt','play_deleted','sack','qb_scramble','qb_spike','two_point_attempt','passer_player_id','interception']
    with sqlite3.connect(':memory:') as con:
        p[cols].to_sql('p',con,index=False); f[KEY+['is_interception_worthy']].to_sql('f',con,index=False)
        pd.DataFrame({'game_id':sorted(d.game_id.unique())}).to_sql('included',con,index=False)
        q='''SELECT p.game_id,p.play_id,p.season,p.week,p.passer_player_id,
          f.is_interception_worthy AS iw,p.interception AS target
          FROM p JOIN included USING(game_id) LEFT JOIN f USING(game_id,play_id)
          WHERE p.season_type='REG' AND p.play_type='pass' AND p.pass_attempt=1
          AND p.play_deleted=0 AND p.sack=0 AND p.qb_scramble=0 AND p.qb_spike=0 AND p.two_point_attempt=0'''
        con.execute('CREATE TABLE audited AS '+q)
        con.execute('CREATE INDEX audit_game ON audited(season,week,game_id,iw,target)')
        actual=con.execute('SELECT * FROM audited ORDER BY game_id,play_id').fetchall()
        compare=d.sort_values(KEY)[KEY+['season','week','passer_player_id','is_interception_worthy','interception']]
        assert actual==list(compare.itertuples(index=False,name=None)), 'Independent population/key/GSIS/FTN/INT mismatch'
        tables={}
        for name,cols in [('season',['season']),('week',['season','week']),('game',['season','week','game_id'])]:
            keys=','.join(cols)
            sql=f'''WITH groups AS (SELECT DISTINCT {keys} FROM audited),
              flags(iw,target) AS (VALUES (1,1),(1,0),(0,1),(0,0))
              SELECT {','.join('g.'+c for c in cols)},flags.iw,flags.target,
              (SELECT COUNT(*) FROM audited a WHERE {' AND '.join('a.'+c+'=g.'+c for c in cols)} AND a.iw=flags.iw AND a.target=flags.target) AS n,
              (SELECT COUNT(*) FROM audited a WHERE {' AND '.join('a.'+c+'=g.'+c for c in cols)}) AS denominator,
              (SELECT COUNT(*) FROM audited a WHERE {' AND '.join('a.'+c+'=g.'+c for c in cols)} AND a.iw=flags.iw) AS group_denominator
              FROM groups g CROSS JOIN flags ORDER BY {','.join('g.'+c for c in cols)},flags.iw DESC,flags.target DESC'''
            t=pd.read_sql_query(sql,con)
            for row in t.itertuples(index=False):
                part=d
                for col in cols: part=part[part[col].eq(getattr(row,col))]
                assert row.n==int((part.is_interception_worthy.eq(row.iw)&part.interception.eq(row.target)).sum())
                assert row.denominator==len(part) and row.group_denominator==int(part.is_interception_worthy.eq(row.iw).sum())
            tables[name]=t
    return tables,dict(passed=True,rows=len(d),method='Independent SQLite raw WHERE + LEFT JOIN + four-cell counts and denominators per season/week/game; all keys, GSIS, FTN, INT exact')

def audit_raw(p,f,d,year):
    mask=pd.Series(True,index=p.index); funnel=[dict(stage='raw',remaining=len(p),excluded=0)]
    for name,rule in FILTERS:
        if name=='window_W1_W7_for_2026':continue
        after=mask&rule(p).fillna(False);funnel.append(dict(stage=name,remaining=int(after.sum()),excluded=int((mask&~after).sum())));mask=after
    eligible_raw=p[mask]
    merged=p.merge(f[KEY+['is_interception_worthy']],on=KEY,how='left',validate='one_to_one')
    return dict(season=year,raw_rows=len(p),raw_ftn_rows=len(f),eligible_before_coverage=len(eligible_raw),included=len(d),funnel=funnel,
        null_filter_flags={c:int(p[c].isna().sum()) for c in ['play_deleted','pass_attempt','sack','qb_scramble','qb_spike','two_point_attempt']},
        raw_eligible_missing_target=int(eligible_raw.interception.isna().sum()),
        raw_eligible_target_counts={str(k):int(v) for k,v in eligible_raw.interception.value_counts(dropna=False).items()},
        eligible_penalty=int(d.penalty.eq(1).sum()),eligible_penalty_int=int((d.penalty.eq(1)&d.interception.eq(1)).sum()),
        eligible_overtime=int(d.qtr.gt(4).sum()),eligible_overtime_int=int(d[d.qtr.gt(4)].interception.sum()),
        excluded_no_play_worthy=int((merged.play_type.eq('no_play')&merged.is_interception_worthy.eq(True)).sum()),
        excluded_two_point_int=int(p[p.two_point_attempt.eq(1)].interception.eq(1).sum()),
        excluded_deleted_int=int(p[p.play_deleted.ne(0)].interception.eq(1).sum()),
        ftn_without_pbp=int(len(f.merge(p[KEY],on=KEY,how='left',indicator=True).query('_merge=="left_only"'))),
        target_missing_included=int(d.interception.isna().sum()),gsis_missing_included=int(d.passer_player_id.isna().sum()),
        binary_target=True,duplicate_keys=0)

def identities(d,rosters):
    r=pd.concat(rosters,ignore_index=True); r=r[r.game_type.eq('REG')].copy()
    r['team']=r.team.replace({'LAR':'LA','JAC':'JAX','WSH':'WAS'})
    m={}
    for k,g in r.groupby(['gsis_id','season','week','team']):
        positions=sorted(g.position.dropna().unique());names=sorted(g.full_name.dropna().unique())
        m[k]=(positions[0] if len(positions)==1 else None,names[0] if len(names)==1 else None)
    out=d.copy(); positions=[];names=[];classes=[]
    for row in d.itertuples():
        pos,name=m.get((row.passer_player_id,row.season,row.week,row.posteam),(None,None))
        positions.append(pos);names.append(name or row.passer_player_name)
        classes.append('qb' if pos=='QB' else 'other' if pos else 'unknown_or_conflicting')
    out['position']=positions;out['audited_name']=names;out['position_class']=classes
    return out

def revision(store,new):
    p=pd.read_parquet(store/'previous-lab/pbp.parquet');f=renamed(pd.read_parquet(store/'previous-lab/ftn.parquet'))
    old=join(p,f).set_index(KEY);new=new.set_index(KEY)
    shared=old.index.intersection(new.index);changed=[]
    fields=['is_interception_worthy','interception','passer_player_id']+CONTEXT
    for key in shared:
        different=[c for c in fields if not (old.at[key,c]==new.at[key,c] or (pd.isna(old.at[key,c]) and pd.isna(new.at[key,c])))]
        if different:changed.append(dict(game_id=key[0],play_id=int(key[1]),fields=different,before={c:old.at[key,c] for c in different},after={c:new.at[key,c] for c in different}))
    return dict(previous='Approved lab source copy; comparison of eligible overlap, not a complete provider revision history',
        added=[f'{a}:{int(b)}' for a,b in new.index.difference(old.index)],removed=[f'{a}:{int(b)}' for a,b in old.index.difference(new.index)],
        changed=changed,shared=len(shared),ftn_label_changes=sum('is_interception_worthy' in x['fields'] for x in changed),
        pinned_historical_2022_2025_unchanged=True)

def build(store,out):
    store=Path(store); verify_manifest(store); out=new_dir(out); (out/'audit').mkdir()
    frames=[];audits=[];cross={k:[] for k in ['season','week','game']};coverage=None;sql=[]
    historical=pd.read_parquet(store/'lineage/historical-dataset.parquet')
    for year in range(2022,2027):
        base=store/'current' if year==2026 else store/'raw'
        p=pd.read_parquet(base/('pbp.parquet' if year==2026 else f'pbp_{year}.parquet'))
        f=renamed(pd.read_parquet(base/('ftn.parquet' if year==2026 else f'ftn_{year}.parquet')))
        if not p.season.eq(year).all() or not f.season.eq(year).all():raise ValueError('Season mismatch')
        if year==2026:
            d,coverage=current_frames(p,f,pd.read_csv(store/'current/schedule.csv'))
            write(out/'revision.json',revision(store,d))
        else:
            d=validate_rows(join(p,f));original=historical[historical.season.eq(year)].sort_values(KEY)
            cols=KEY+['passer_player_id','is_interception_worthy','interception']+CONTEXT
            pd.testing.assert_frame_equal(d.sort_values(KEY)[cols].reset_index(drop=True),original[cols].reset_index(drop=True),check_dtype=False)
        t,receipt=independent(p,f,d);sql.append(dict(season=year,**receipt))
        for k,v in t.items():cross[k].append(v)
        audits.append(audit_raw(p,f,d,year));d['is_interception_worthy']=d.is_interception_worthy.astype(int);d['interception']=d.interception.astype(int)
        frames.append(d[KEEP])
        p.loc[p.two_point_attempt.eq(1)|p.play_type.eq('no_play')|p.play_deleted.ne(0),KEY+['season','week','play_type','two_point_attempt','play_deleted','interception','penalty','desc']].to_parquet(out/f'audit/excluded_{year}.parquet',index=False)
    d=pd.concat(frames,ignore_index=True).sort_values(KEY).reset_index(drop=True)
    d=identities(d,[pd.read_parquet(store/f'rosters/{y}.parquet') for y in range(2022,2027)])
    unique(d,KEY,'Final population');d.to_parquet(out/'dataset.parquet',index=False)
    for k,ts in cross.items():pd.concat(ts,ignore_index=True).to_csv(out/f'audit/cross_by_{k}.csv',index=False)
    d.groupby(['season','passer_player_id','passer_player_name','audited_name','position','position_class','posteam'],dropna=False).size().rename('passes').reset_index().to_csv(out/'audit/identity.csv',index=False)
    write(out/'audit/raw.json',audits);write(out/'audit/independent.json',sql);write(out/'coverage.json',coverage)
    split=d[KEY+['season','week','game_date']].copy()
    for year in [2023,2024,2025,2026]:split[f'evaluation_{year}']=np.select([split.season.lt(year),split.season.eq(year)],['train','evaluation'],default='unused')
    split.to_csv(out/'splits.csv',index=False)
    write(out/'manifest.json',dict(rows=len(d),dataset_sha256=sha(out/'dataset.parquet'),sources_sha256=sha(store/'sources.json'),
        historical_population_exact=True,independent_reconciliation=True,coverage=coverage))
    print(d.groupby('season').interception.agg(['size','sum','mean']).to_string(),flush=True)
    return d
