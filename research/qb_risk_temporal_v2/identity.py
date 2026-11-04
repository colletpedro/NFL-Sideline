"""Presentation classification only: GSIS + exact weekly/team context."""
from pathlib import Path
import pandas as pd
from common import known_only

def classify_positions(passes,roster):
 needed=['gsis_id','season','week','team','game_type','position']
 if any(c not in roster for c in needed):raise ValueError('Weekly roster schema missing temporal identity columns')
 r=roster[roster.game_type.eq('REG')&roster.season.eq(2026)&roster.week.between(1,7)].copy()
 # Normalize only documented franchise abbreviation aliases, never name-based identity.
 r['team']=r.team.replace({'LAR':'LA','JAC':'JAX','WSH':'WAS'})
 groups=r.groupby(['gsis_id','season','week','team'],dropna=False).position.agg(lambda a:tuple(sorted(set(a.dropna().astype(str))))).to_dict()
 rows=[]
 for key,g in passes.groupby(['passer_player_id','season','week','posteam'],sort=True):
  positions=groups.get(tuple(key),())
  category='unknown_or_conflicting' if len(positions)!=1 else ('QB_identified' if positions[0]=='QB' else 'other_position')
  rows.append(dict(passer_player_id=key[0],season=int(key[1]),week=int(key[2]),team=key[3],positions=' / '.join(positions),position_class=category,passes=len(g)))
 return pd.DataFrame(rows)

def presentation(d,roster,out,pred):
 known_only(d);p=d[d.season.eq(2026)].copy();identity=classify_positions(p,roster);identity.to_csv(Path(out)/'position_by_week.csv',index=False);rows=[]
 for ident,g in p.groupby('passer_player_id',sort=True):
  r=identity[identity.passer_player_id.eq(ident)];classes=sorted(r.position_class.unique());positions=sorted(set(' / '.join(r.positions.dropna()).split(' / '))-{''})
  category=classes[0] if len(classes)==1 and len(positions)<=1 else 'unknown_or_conflicting'
  probs=pred.loc[g.index,'M0'].to_numpy()
  rows.append(dict(passer_player_id=ident,names=' / '.join(sorted(g.passer_player_name.unique())),teams=' / '.join(sorted(g.posteam.unique())),position_class=category,positions=' / '.join(positions),passes=len(g),games=g.game_id.nunique(),observed=int(g.is_interception_worthy.sum()),expected_M0=float(probs.sum()),interval_status='omitted_for_all_passers_model_and_small_sample_uncertainty',zero_events=bool(g.is_interception_worthy.sum()==0)))
 result=pd.DataFrame(rows).sort_values(['names','passer_player_id']);result.to_csv(Path(out)/'passer_presentation.csv',index=False);return result
