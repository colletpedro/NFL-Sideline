"""Supplementary raw-field census; no projector imports, no acquisition."""
from collections import Counter
import json
from pathlib import Path
import sys
import polars as pl
raw=pl.read_parquet(sys.argv[1]);third=raw.filter(pl.col('down')==3);rows=third.to_dicts()
flags=['third_down_converted','third_down_failed','play_deleted','aborted_play','qb_kneel','qb_spike','first_down_penalty','sack','qb_scramble','qb_dropback','pass_attempt','rush_attempt']
groups=Counter((r['play_type'],r['third_down_converted'],r['third_down_failed'],r['first_down_penalty']) for r in rows)
result=dict(rawRows=raw.height,thirdCandidates=third.height,fields={c:dict(nulls=third[c].null_count(),values=[dict(value=v,count=n) for v,n in Counter(third[c].to_list()).items()]) for c in flags},thirdTypes=dict(Counter(third['play_type'].to_list())),conversionFlagGroups=[dict(playType=k[0],converted=k[1],failed=k[2],penaltyFirstDown=k[3],rows=n) for k,n in sorted(groups.items())],positiveThirdFlagsOutsideDown3=raw.filter(((pl.col('third_down_converted')==1)|(pl.col('third_down_failed')==1))&(pl.col('down').is_null()|(pl.col('down')!=3))).height,duplicateGamePlayIds=raw.group_by('game_id','play_id').len().filter(pl.col('len')>1).height,flagsRetainedOnNullifiedScrambles=[dict(gameId=r['game_id'],playId=r['play_id']) for r in rows if r['play_type']=='no_play' and r['qb_scramble']==1],distanceMissing=third['ydstogo'].null_count())
Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='fields' and k!='conversionFlagGroups'},indent=2))
