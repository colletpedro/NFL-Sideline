"""Independent raw SQLite audit. Does not import production classifier/aggregator."""
import argparse,sqlite3
from common import *

def reconcile(s,package,out):
 s=Path(s);package=Path(package);verify(s);year_current=read(s/'sources.json')['currentSeason'];receipts=[];expected=pd.read_parquet(package/'plays.parquet')
 for year in range(2022,year_current+1):
  if year>2025 and year!=year_current:continue
  cur=year==year_current
  p=pd.read_parquet(s/('current/pbp.parquet' if cur else f'raw/pbp_{year}.parquet'),columns=PBP)
  f=pd.read_parquet(s/('current/ftn.parquet' if cur else f'raw/ftn_{year}.parquet')).rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
  r=pd.read_parquet(s/f'rosters/{year}.parquet')
  with sqlite3.connect(':memory:') as db:
   p.to_sql('p',db,index=False);f[KEY+FTN].to_sql('f',db,index=False);r[['season','week','team','gsis_id','position','full_name','game_type']].to_sql('r',db,index=False)
   db.execute('CREATE INDEX fk ON f(game_id,play_id)');db.execute('CREATE INDEX rk ON r(season,week,team,gsis_id)')
   game_filter=''
   if cur:
    sc=pd.read_csv(s/'current/schedule.csv');sc.to_sql('sc',db,index=False)
    game_filter="""AND p.game_id IN (SELECT sc.game_id FROM sc JOIN p e ON e.game_id=sc.game_id AND e.desc='END GAME' WHERE sc.season=? AND sc.game_type='REG' AND sc.home_score IS NOT NULL AND e.total_home_score=sc.home_score AND e.total_away_score=sc.away_score GROUP BY sc.game_id HAVING COUNT(*)=1)"""
   sql=f"""CREATE TABLE a AS WITH ro AS (
     SELECT season,week,CASE team WHEN 'LAR' THEN 'LA' WHEN 'JAC' THEN 'JAX' WHEN 'WSH' THEN 'WAS' ELSE team END team,gsis_id,
       CASE WHEN COUNT(DISTINCT position)=1 THEN MIN(position) END position,
       CASE WHEN COUNT(DISTINCT full_name)=1 THEN MIN(full_name) END name
       FROM r WHERE game_type='REG' GROUP BY 1,2,3,4),
    joined AS (SELECT p.*,f.read_thrown,f.is_throw_away,f.is_qb_out_of_pocket,f.play_id IS NOT NULL AS charted,
      UPPER(TRIM(f.read_thrown)) code,
      CASE WHEN p.qb_scramble=1 AND p.sack=0 AND p.pass_attempt=0 AND p.rush_attempt=1 AND p.play_type='run' THEN 1 ELSE 0 END scramble_event,
      CASE WHEN p.qb_scramble=1 AND p.sack=0 AND p.pass_attempt=0 AND p.rush_attempt=1 AND p.play_type='run' THEN p.rusher_player_id ELSE p.passer_player_id END provisional_id
    FROM p LEFT JOIN f USING(game_id,play_id)
    WHERE p.season_type='REG' AND p.qb_dropback=1 AND p.play_deleted=0 AND p.qb_spike=0 AND p.qb_kneel=0 AND p.two_point_attempt=0 AND p.play_type IN ('pass','run') {game_filter}),
    joined_roster AS (SELECT j.*,ro.position AS roster_position,ro.name AS roster_name FROM joined j LEFT JOIN ro ON j.season=ro.season AND j.week=ro.week AND j.posteam=ro.team AND j.provisional_id=ro.gsis_id),
    ident AS (SELECT *,CASE WHEN scramble_event=1 AND (passer_player_id IS NOT NULL AND passer_player_id!=rusher_player_id) THEN NULL WHEN provisional_id GLOB '00-[0-9][0-9][0-9][0-9][0-9][0-9][0-9]' AND LENGTH(provisional_id)=10 THEN provisional_id ELSE NULL END player_id FROM joined_roster)
    SELECT *,CASE
      WHEN sack IS NULL OR qb_scramble IS NULL OR pass_attempt IS NULL OR rush_attempt IS NULL OR aborted_play IS NULL OR sack NOT IN(0,1) OR qb_scramble NOT IN(0,1) OR pass_attempt NOT IN(0,1) OR rush_attempt NOT IN(0,1) OR aborted_play NOT IN(0,1) THEN 'indeterminate'
      WHEN NOT ((sack=1 AND qb_scramble=0 AND pass_attempt=1 AND rush_attempt=0 AND play_type='pass') OR (sack=0 AND qb_scramble=1 AND pass_attempt=0 AND rush_attempt=1 AND play_type='run') OR (sack=0 AND qb_scramble=0 AND pass_attempt=1 AND rush_attempt=0 AND play_type='pass')) THEN 'indeterminate'
      WHEN aborted_play=1 OR is_throw_away NOT IN(0,1) OR is_qb_out_of_pocket NOT IN(0,1) THEN 'indeterminate'
      WHEN is_throw_away=1 AND (sack=1 OR qb_scramble=1 OR complete_pass=1 OR interception=1) THEN 'indeterminate'
      WHEN sack=1 THEN 'sack'
      WHEN qb_scramble=1 THEN CASE WHEN player_id IS NOT NULL AND roster_position='QB' AND roster_name IS NOT NULL THEN 'scramble' ELSE 'indeterminate' END
      WHEN charted=0 OR is_throw_away IS NULL THEN 'indeterminate'
      WHEN is_throw_away=1 THEN 'throwaway'
      WHEN code='SD' THEN 'scramble_drill'
      WHEN code IN('0','1','2','CHK') AND NOT(season=2022 AND code='0') THEN 'progression'
      ELSE 'indeterminate' END category_sql FROM ident"""
   db.execute(sql,(year,) if cur else ())
   raw=pd.read_sql_query('SELECT game_id,play_id,player_id,category_sql,epa FROM a ORDER BY game_id,play_id',db)
   exp=expected[expected.season.eq(year)].sort_values(KEY).reset_index(drop=True)
   pd.testing.assert_frame_equal(raw[KEY],exp[KEY],check_dtype=False)
   assert raw.category_sql.tolist()==exp.category.tolist(),'Classification mismatch'
   assert raw.player_id.fillna('<MISSING>').tolist()==exp.player_id.fillna('<MISSING>').tolist(),'Identity mismatch'
   np.testing.assert_allclose(raw.epa,exp.epa,rtol=0,atol=0,equal_nan=True)
   sums=pd.read_sql_query('SELECT player_id,category_sql AS category,COUNT(*) n,COUNT(epa) n_epa,SUM(epa) sum_epa,AVG(epa) mean_epa FROM a GROUP BY player_id,category_sql ORDER BY player_id,category_sql',db)
   independent_total=float(db.execute('SELECT SUM(epa) FROM a').fetchone()[0]);matched=0
   if year>=2023:
    target=pd.read_csv(package/'categories.csv');target=target[target.season.eq(year)]
    for rec in sums.to_dict('records'):
     row=target[(target.player_id.eq(rec['player_id']) if rec['player_id'] is not None else target.player_id.isna())&target.category.eq(rec['category'])].iloc[0]
     assert row.n==rec['n'] and row.n_epa==rec['n_epa']
     np.testing.assert_allclose([row.sum_epa,row.mean_epa],[rec['sum_epa'],rec['mean_epa']],rtol=0,atol=1e-10,equal_nan=True);matched+=1
   receipts.append(dict(season=year,passed=True,rows=len(raw),sum_epa=independent_total,matched_nonempty_aggregates=matched,missing_epa=int(raw.epa.isna().sum()),method='Independent SQLite raw WHERE + LEFT JOIN roster + CASE event precedence + key/GSIS/class comparison + raw SQL counts/sums/means',sum_tolerance_absolute=1e-10,keys_categories_identity_exact=True))
 write(out,receipts);return receipts

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--sources',required=True);a.add_argument('--package',required=True);a.add_argument('--out',required=True);v=a.parse_args();print(reconcile(v.sources,v.package,v.out))
