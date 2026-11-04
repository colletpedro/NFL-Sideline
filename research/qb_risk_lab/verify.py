"""Independent raw SQL reconciliation, deterministic reproduction, durable receipt."""
from pathlib import Path
import argparse,collections,json,sqlite3,sys,math
import pandas as pd
sys.path.insert(0,str(Path(__file__).parent))
import pipeline as p

def verify(store,sources,output):
 store=Path(store);src=Path(sources);active,index,details=p.read_active(store)
 manifest=json.loads((src/'sources.json').read_text())
 for row in manifest['files']:
  assert p.sha(src/row['path'])==row['sha256']
 pb=pd.read_parquet(src/'pbp.parquet');ft=pd.read_parquet(src/'ftn.parquet').rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
 games=[g['gameId'] for g in index['coverage']['included']]
 with sqlite3.connect(':memory:') as con:
  cols=['game_id','play_id','season','season_type','week','play_type','pass_attempt','play_deleted','sack','qb_scramble','qb_spike','two_point_attempt','passer_player_id','interception']
  pb[cols].to_sql('p',con,index=False);ft[['game_id','play_id','is_interception_worthy']].to_sql('f',con,index=False)
  pd.DataFrame({'game_id':games}).to_sql('included',con,index=False)
  rows=con.execute('''SELECT p.game_id,p.play_id,p.passer_player_id,f.is_interception_worthy,p.interception,p.week FROM p JOIN included USING(game_id) LEFT JOIN f ON p.game_id=f.game_id AND p.play_id=f.play_id WHERE p.season=2026 AND p.season_type='REG' AND p.play_type='pass' AND p.pass_attempt=1 AND p.play_deleted=0 AND p.sack=0 AND p.qb_scramble=0 AND p.qb_spike=0 AND p.two_point_attempt=0 ORDER BY p.game_id,p.play_id''').fetchall()
 plays=sorted([x for d in details.values() for x in d['plays']],key=lambda x:(x['gameId'],x['playId']))
 assert rows==[(x['gameId'],x['playId'],x['passerId'],int(x['worthy']),int(x['interception']),x['week']) for x in plays]
 assert math.isclose(sum(x['probability'] for x in plays),index['summary']['expected'],abs_tol=1e-10)
 for player in index['players']:
  agg=p.aggregate(details[player['id']]['plays'])
  assert all(math.isclose(agg[k],player[k],abs_tol=1e-9) for k in agg)
 rebuilt,ds,funnel=p.build_frames(pb,ft,pd.read_csv(src/'schedule.csv'),pd.read_parquet(src/'roster.parquet'),p.load_model())
 expected=collections.Counter((x['worthy'],x['interception']) for x in plays)
 byweek=[dict(week=w,**p.aggregate([x for x in plays if x['week']==w])) for w in index['coverage']['weeks']]
 # Compare preserved package content, excluding acquisition/version wrappers.
 bare={k:v for k,v in index.items() if k not in ['packageId','acquiredAt']}
 assert p.encoded(bare)==p.encoded(rebuilt)
 for ident,value in ds.items():assert p.encoded(value)==p.encoded({k:v for k,v in details[ident].items() if k!='packageId'})
 receipt=dict(status='PASS',package=active,modelSha256=p.sha(p.MODEL),summary=index['summary'],byWeek=byweek,positionClasses=dict(collections.Counter(x['positionClass'] for x in index['players'])),cross={f'{int(k[0])}{int(k[1])}':v for k,v in expected.items()},sources=manifest,raw=dict(pbpRows=len(pb),ftnRows=len(ft)),checks=['Independent SQLite raw WHERE + LEFT JOIN, all keys/GSIS/labels/INT/weeks exact','All player sums and global expected agree within1e-9','Frozen JSON inference rebuild: byte-equivalent semantic JSON','No model fitting; frozen SHA exact'],funnel=funnel)
 p.write(output,receipt);print(json.dumps({k:v for k,v in receipt.items() if k not in ['sources','funnel']},indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--store',required=True);a.add_argument('--sources',required=True);a.add_argument('--output',required=True);v=a.parse_args();verify(v.store,v.sources,v.output)
