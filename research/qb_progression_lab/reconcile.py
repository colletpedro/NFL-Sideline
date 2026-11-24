"""Raw SQL keys/EPA + independent DES predicate + presentation/HTTP reconciliation."""
import argparse,sqlite3,urllib.request,sys
from pathlib import Path
from package import *

def reconcile(store=STORE,url='http://127.0.0.1:18127',out=None):
 pointer=read(Path(store)/'current.json');root=Path(store)/'packages'/pointer['packageId'];index=check_package(root);d=pd.read_parquet(root/'plays.parquet');old=pd.read_parquet(SCI/'package-release/plays.parquet');source=Path(read(SCI/'package-release/index.json')['sourceManifest']).parent;verify(source)
 raw_rows=[]
 for year in range(2022,2027):
  cur=year==2026;pb=pd.read_parquet(source/('current/pbp.parquet' if cur else f'raw/pbp_{year}.parquet'));ft=pd.read_parquet(source/('current/ftn.parquet' if cur else f'raw/ftn_{year}.parquet')).rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
  with sqlite3.connect(':memory:') as db:
   cols=KEY+['season_type','qb_dropback','play_deleted','qb_spike','qb_kneel','two_point_attempt','play_type','epa','sack','qb_scramble','pass_attempt','rush_attempt','aborted_play','complete_pass','interception'];pb[cols].to_sql('p',db,index=False);ft[KEY+['read_thrown','is_throw_away','is_qb_out_of_pocket']].to_sql('f',db,index=False)
   raw=pd.read_sql_query("""SELECT p.game_id,p.play_id,p.epa,
    CASE WHEN play_type='pass' AND pass_attempt=1 AND rush_attempt=0 AND sack=0 AND qb_scramble=0 AND aborted_play=0 AND is_throw_away=0 AND (is_qb_out_of_pocket IN(0,1) OR is_qb_out_of_pocket IS NULL) AND UPPER(TRIM(read_thrown))='DES' THEN 1 ELSE 0 END expected_des
    FROM p LEFT JOIN f USING(game_id,play_id) WHERE season_type='REG' AND qb_dropback=1 AND play_deleted=0 AND qb_spike=0 AND qb_kneel=0 AND two_point_attempt=0 AND play_type IN('pass','run') ORDER BY p.game_id,p.play_id""",db)
   selected=d[d.season.eq(year)].sort_values(KEY).reset_index(drop=True);pd.testing.assert_frame_equal(raw[KEY],selected[KEY],check_dtype=False);np.testing.assert_allclose(raw.epa,selected.epa,rtol=0,atol=0,equal_nan=True);assert raw.expected_des.eq(1).tolist()==selected.category.eq('designed').tolist();raw_rows.append(dict(season=year,rows=len(raw),des=int(raw.expected_des.sum()),sumEpa=float(raw.epa.sum())))
 for cats in [['progression']]+list(GROUPS.values()):assert old.loc[old.category.isin(cats),KEY+['epa','player_id']].equals(d.loc[d.category.isin(cats),KEY+['epa','player_id']])
 def get(path):
  with urllib.request.urlopen(urllib.request.Request(url+path,headers={'X-Risk-Lab':'1'})) as r:return __import__('json').loads(r.read())
 http=get('/__progression/index.json');assert http['packageId']==index['packageId'];http.pop('checkedAt',None);assert http==index
 details=0
 for player in index['players']:
  assert get(f"/__progression/packages/{index['packageId']}/players/{player['id']}.json")==read(root/f"players/{player['id']}.json");details+=1
 report=dict(passed=True,raw=raw_rows,principalAndSensitivitiesExact=True,httpIndexAndAllDetailsExact=True,httpDetails=details,packageId=index['packageId'])
 if out:write(out,report)
 return report
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--store',default=str(STORE));a.add_argument('--url',default='http://127.0.0.1:18127');a.add_argument('--out',required=True);v=a.parse_args();print(reconcile(v.store,v.url,v.out))
