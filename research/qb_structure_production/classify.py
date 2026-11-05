"""Pure, exclusive rules. No EPA, outcome magnitude, text or player name in rules."""
import re
from common import *

def binary(v):return None if pd.isna(v) else int(v) if v in (0,1) else 'invalid'
def normalized(v):return None if pd.isna(v) else str(v).strip().upper()
def valid_id(v):return isinstance(v,str) and re.fullmatch(r'00-\d{7}',v) is not None

def classify(r):
 # r contains already audited roster metadata. Missing charting is never False.
 s=binary(r.get('sack'));q=binary(r.get('qb_scramble'));p=binary(r.get('pass_attempt'));u=binary(r.get('rush_attempt'))
 t=binary(r.get('is_throw_away'));o=binary(r.get('is_qb_out_of_pocket'));ab=binary(r.get('aborted_play'))
 read_code=normalized(r.get('read_thrown'));ptype=r.get('play_type')
 out=dict(category='indeterminate',rule='unresolved',reason=None,read_normalized=read_code,event_type='conflict')
 def finish(cat,rule,reason=None):out.update(category=cat,rule=rule,reason=reason);return out
 if any(x not in (0,1) for x in (s,q,p,u)) or ab not in (0,1):return finish('indeterminate','invalid_event_flags','missing_or_invalid_event_flag')
 if (s,q,p,u,ptype)==(1,0,1,0,'pass'):out['event_type']='sack'
 elif (s,q,p,u,ptype)==(0,1,0,1,'run'):out['event_type']='scramble'
 elif (s,q,p,u,ptype)==(0,0,1,0,'pass'):out['event_type']='pass'
 else:return finish('indeterminate','event_conflict','contradictory_event_flags')
 if ab==1:return finish('indeterminate','aborted','aborted_dropback')
 if t=='invalid' or o=='invalid':return finish('indeterminate','charting_conflict','invalid_binary_charting')
 if t==1 and out['event_type']!='pass':return finish('indeterminate','event_charting_conflict','throwaway_without_throw')
 if t==1 and (binary(r.get('complete_pass'))==1 or binary(r.get('interception'))==1):return finish('indeterminate','throwaway_outcome_conflict','throwaway_complete_or_intercepted')
 if s==1:return finish('sack','01_sack')
 if q==1:
  passer=r.get('passer_player_id');rusher=r.get('rusher_player_id')
  if r.get('identity_status')=='resolved' and r.get('position')!='QB':
   return finish('indeterminate','scramble_non_qb','scramble_non_qb_position')
  if not valid_id(rusher) or r.get('identity_status')!='resolved' or (pd.notna(passer) and passer!=rusher):
   return finish('indeterminate','scramble_identity_conflict','scramble_rusher_not_verified')
  return finish('scramble','02_scramble_verified_rusher')
 if r.get('charting_present')!=True or t is None:return finish('indeterminate','missing_charting','charting_or_throwaway_flag_missing')
 if t==1:return finish('throwaway','03_throwaway_preserve_read')
 if read_code=='SD':return finish('scramble_drill','04_SD_throw')
 if read_code in ['0','1','2','CHK']:
  if int(r['season'])==2022 and read_code=='0':return finish('indeterminate','historical_code_conflict','unexpected_2022_primary_code')
  return finish('progression','05_registered_read')
 if read_code=='DES':return finish('indeterminate','06_designed_without_progression','designed_no_progression')
 return finish('indeterminate','06_unresolved_read','missing_read' if read_code is None else 'unknown_read_code')

def identity(d,roster):
 roster=roster[roster.game_type.eq('REG')].copy();roster['team']=roster.team.replace({'LAR':'LA','JAC':'JAX','WSH':'WAS'})
 lookup={}
 for k,g in roster.groupby(['season','week','team','gsis_id']):
  pos=sorted(g.position.dropna().unique());name=sorted(g.full_name.dropna().unique())
  lookup[k]=(pos[0] if len(pos)==1 else None,name[0] if len(name)==1 else None)
 rows=[]
 for r in d.to_dict('records'):
  is_scramble=r['qb_scramble']==1 and r['sack']==0 and r['pass_attempt']==0 and r['rush_attempt']==1 and r['play_type']=='run'
  pid=r['rusher_player_id'] if is_scramble else r['passer_player_id']
  pos,name=lookup.get((r['season'],r['week'],r['posteam'],pid),(None,None))
  status='resolved' if valid_id(pid) and pos and name else 'unknown_or_conflicting'
  if is_scramble and (pd.notna(r['passer_player_id']) and r['passer_player_id']!=pid):status='unknown_or_conflicting';pid=None
  if not valid_id(pid):pid=None;status='unknown_or_conflicting'
  rows.append(dict(player_id=pid,identity_source='rusher_verified_scramble' if is_scramble and status=='resolved' else 'unresolved_scramble' if is_scramble else 'passer',identity_status=status,position=pos,audited_name=name or (r['rusher_player_name'] if is_scramble else r['passer_player_name']),position_class='qb' if status=='resolved' and pos=='QB' else 'other' if status=='resolved' else 'unknown_or_conflicting'))
 return pd.concat([d.reset_index(drop=True),pd.DataFrame(rows)],axis=1)
