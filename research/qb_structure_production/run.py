"""Validate -> classify -> aggregate -> immutable package. Offline by construction."""
import argparse,sys,platform
from common import *
from classify import identity,classify,normalized

def closed_games(p,s,year):
 s=s[s.season.eq(year)&s.game_type.eq('REG')].copy();unique_s=s.game_id.notna().all() and not s.game_id.duplicated().any()
 if not unique_s:raise ValueError('Calendar duplicate/missing identity')
 scores=s[['home_score','away_score','result']]
 if not scores.notna().sum(axis=1).isin([0,3]).all():raise ValueError('Partial score trio')
 if not s[s.result.notna()].result.eq(s.home_score-s.away_score).loc[s.result.notna()].all():raise ValueError('Inconsistent schedule score')
 if not set(p[p.season_type.eq('REG')].game_id).issubset(set(s.game_id)):raise ValueError('PBP outside schedule')
 included=[];gaps=[];future=[]
 for g in s.sort_values(['week','game_id']).itertuples():
  meta=dict(game_id=g.game_id,week=int(g.week),date=str(g.gameday))
  if pd.isna(g.home_score):future.append(meta);continue
  raw=p[p.game_id.eq(g.game_id)]
  if raw.empty:gaps.append(dict(**meta,reason='pbp_missing'));continue
  if not (raw.week.eq(g.week)&raw.home_team.eq(g.home_team)&raw.away_team.eq(g.away_team)&raw.game_date.astype(str).eq(str(g.gameday))).all():raise ValueError('PBP calendar conflict')
  end=raw[raw.desc.eq('END GAME')]
  if len(end)!=1:gaps.append(dict(**meta,reason='end_marker_missing_or_ambiguous'));continue
  if not (end.total_home_score.eq(g.home_score)&end.total_away_score.eq(g.away_score)).all():raise ValueError('Final score conflict')
  included.append(meta)
 return {x['game_id'] for x in included},dict(season=year,included=included,pending=gaps,future=future,completed_games=int(s.home_score.notna().sum()))

def load(s,out):
 m=verify(s);frames=[];audit=[];cover=[];rosters=[]
 for year in range(2022,int(m['currentSeason'])+1):
  # Historical period is fixed 2022-2025; one current season, never overlapping caches.
  if year>2025 and year!=m['currentSeason']:continue
  cur=year==m['currentSeason'];pp=s/('current/pbp.parquet' if cur else f'raw/pbp_{year}.parquet');fp=s/('current/ftn.parquet' if cur else f'raw/ftn_{year}.parquet')
  p=pd.read_parquet(pp,columns=PBP);f=pd.read_parquet(fp).rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
  unique(p,'PBP');unique(f,'FTN')
  if not p.season.eq(year).all() or not f.season.eq(year).all():raise ValueError('Season mismatch')
  temporal=p[KEY+['season','week']].merge(f[KEY+['season','week']],on=KEY,suffixes=('_p','_f'),validate='one_to_one')
  if not (temporal.season_p.eq(temporal.season_f)&temporal.week_p.eq(temporal.week_f)).all():raise ValueError('FTN/PBP temporal conflict')
  mask=pd.Series(True,index=p.index);funnel=[]
  rules=[('REG',p.season_type.eq('REG')),('dropback',p.qb_dropback.eq(1)),('not_deleted',p.play_deleted.eq(0)),('not_spike',p.qb_spike.eq(0)),('not_kneel',p.qb_kneel.eq(0)),('not_two_point',p.two_point_attempt.eq(0)),('valid_play_type',p.play_type.isin(['pass','run']))]
  for name,rule in rules:
   nxt=mask&rule.fillna(False);funnel.append(dict(stage=name,n=int(nxt.sum()),excluded=int((mask&~nxt).sum())));mask=nxt
  d=p[eligible(p)].copy()
  if cur:
   games,cov=closed_games(p,pd.read_csv(s/'current/schedule.csv'),year);d=d[d.game_id.isin(games)];cover.append(cov)
  else:cover.append(dict(season=year,included=[dict(game_id=g) for g in sorted(d.game_id.unique())],pending=[],future=[]))
  j=d.merge(f[KEY+FTN],on=KEY,how='left',validate='one_to_one',indicator=True)
  j['charting_present']=j['_merge'].eq('both');j=j.drop(columns='_merge')
  audit.append(dict(season=year,raw_pbp=len(p),raw_ftn=len(f),funnel=funnel,eligible=len(j),missing_ftn=int((~j.charting_present).sum()),missing_epa=int((~np.isfinite(j.epa)).sum()),penalties=int(j.penalty.eq(1).sum()),overtime=int(j.qtr.gt(4).sum()),aborted=int(j.aborted_play.eq(1).sum()),passer_missing_scrambles=int((j.qb_scramble.eq(1)&j.passer_player_id.isna()).sum()),ftn_without_pbp=int((~f.set_index(KEY).index.isin(p.set_index(KEY).index)).sum()),null_flags={c:int(p[c].isna().sum()) for c in ['qb_dropback','play_deleted','qb_spike','qb_kneel','two_point_attempt','aborted_play']},raw_read_codes={str(k):int(v) for k,v in f.read_thrown.value_counts(dropna=False).items()}))
  exc=p[~eligible(p)].copy();exc['failed_rules']=['|'.join(name for name,r in rules if not bool(r.fillna(False).loc[i])) for i in exc.index];exc.to_parquet(out/f'audit/excluded_{year}.parquet',index=False)
  # Full-source cross: explicitly distinguish no-dropback and excluded rows.
  full=p.merge(f[KEY+FTN],on=KEY,how='left',validate='one_to_one');full['read_raw_display']=full.read_thrown.fillna('<MISSING>');full['eligible']=eligible(full)
  full.groupby(['season','eligible','play_type','pass_attempt','qb_scramble','sack','read_raw_display','is_throw_away','is_qb_out_of_pocket'],dropna=False).agg(n=('play_id','size'),epa_n=('epa','count'),epa_sum=('epa','sum')).reset_index().to_csv(out/f'audit/raw_cross_{year}.csv',index=False)
  frames.append(j);rosters.append(pd.read_parquet(s/f'rosters/{year}.parquet'))
 d=identity(pd.concat(frames,ignore_index=True),pd.concat(rosters,ignore_index=True))
 labels=pd.DataFrame([classify(r) for r in d.to_dict('records')]);d=pd.concat([d,labels],axis=1)
 d['epa_valid']=np.isfinite(d.epa);d['epa']=d.epa.where(d.epa_valid)
 evidence=['sack','qb_scramble','pass_attempt','rush_attempt','aborted_play','read_thrown','is_throw_away','is_qb_out_of_pocket','charting_present','identity_source','identity_status']
 d['evidence_used']=[json.dumps(clean({c:r[c] for c in evidence}),sort_keys=True) for r in d.to_dict('records')]
 d=d.sort_values(KEY).reset_index(drop=True);unique(d,'classified')
 write(out/'audit/raw.json',audit);write(out/'coverage.json',cover)
 d.groupby(['season','read_thrown','read_normalized','event_type','category','is_throw_away','is_qb_out_of_pocket'],dropna=False).agg(n=('play_id','size'),n_epa=('epa','count'),sum_epa=('epa','sum')).reset_index().to_csv(out/'audit/classified_cross.csv',index=False)
 d.groupby(['season','category','reason'],dropna=False).size().rename('n').reset_index().to_csv(out/'audit/reasons.csv',index=False)
 d.groupby(['season','category','is_screen_pass','is_rpo','is_play_action','is_trick_play','is_qb_sneak'],dropna=False).size().rename('n').reset_index().to_csv(out/'audit/designed_flags.csv',index=False)
 d.groupby(['season','player_id','identity_source','identity_status','position','audited_name','posteam'],dropna=False).size().rename('n').reset_index().to_csv(out/'audit/identity.csv',index=False)
 return d

def aggregate(d):
 rows=[];comparisons=[]
 for (year,pid),g in d.groupby(['season','player_id'],dropna=False,sort=True):
  meta=dict(season=year,player_id=pid,audited_name='|'.join(sorted(g.audited_name.dropna().unique())),position_class='|'.join(sorted(g.position_class.unique())),teams='|'.join(sorted(g.posteam.dropna().unique())),dropbacks=len(g),dropback_games=g.game_id.nunique(),indeterminate_n=int(g.category.eq('indeterminate').sum()),missing_ftn=int((~g.charting_present).sum()),identity_unresolved=int(g.identity_status.ne('resolved').sum()))
  classifiable=int(g.category.ne('indeterminate').sum())
  for cat in CATS:
   part=g[g.category.eq(cat)];t=stats(part)
   rows.append(dict(**meta,category=cat,**t,pct_all=100*len(part)/len(g),pct_classifiable=100*len(part)/classifiable if cat!='indeterminate' and classifiable else None,classifiable_n=classifiable))
  a=stats(g[g.category.eq('progression')])
  for version,cats in GROUPS.items():
   b=stats(g[g.category.isin(cats)]);n_games=g[g.category.isin(['progression']+cats)].game_id.nunique()
   delta=a['mean_epa']-b['mean_epa'] if a['mean_epa'] is not None and b['mean_epa'] is not None else None
   comparisons.append(dict(**meta,definition=version,a_n=a['n'],a_n_epa=a['n_epa'],a_sum=a['sum_epa'],a_mean=a['mean_epa'],b_n=b['n'],b_n_epa=b['n_epa'],b_sum=b['sum_epa'],b_mean=b['mean_epa'],difference=delta,b_pct_all=100*b['n']/len(g),b_pct_classifiable=100*b['n']/classifiable if classifiable else None,status='unavailable_no_opportunities' if not a['n'] or not b['n'] else 'unavailable_epa' if delta is None else support(a['n_epa'],b['n_epa'],n_games),comparison_games=n_games))
 return pd.DataFrame(rows),pd.DataFrame(comparisons)

def contextual(d):
 d=d[d.category.isin(['progression','scramble_drill','scramble'])].copy();d['group']=np.where(d.category.eq('progression'),'A','B');rows=[];summary=[]
 bins={'down':([0,1,2,3,4],['1','2','3','4']),'ydstogo':([-np.inf,3,7,10,np.inf],['0–3','4–7','8–10','11+']),'yardline_100':([-np.inf,20,50,np.inf],['red_zone_0–20','21–50','51+']),'qtr':([0,1,2,3,4,np.inf],['Q1','Q2','Q3','Q4','OT']),'quarter_seconds_remaining':([-np.inf,120,600,np.inf],['0–120','121–600','601+']),'score_differential':([-np.inf,-9,-1,0,8,np.inf],['≤−9','−8..−1','0','1..8','≥9'])}
 for (year,group),g in d.groupby(['season','group']):
  for c,(cuts,labels) in bins.items():
   b=pd.cut(g[c],cuts,labels=labels,include_lowest=True).astype(object).fillna('<MISSING>')
   for label in labels+['<MISSING>']:
    n=int(b.eq(label).sum());rows.append(dict(season=year,group=group,field=c,bin=label,n=n,denominator=len(g),pct=100*n/len(g)))
   summary.append(dict(season=year,group=group,field=c,n=len(g),valid=int(g[c].notna().sum()),mean=g[c].mean(),median=g[c].median()))
 return pd.DataFrame(rows),pd.DataFrame(summary)

def diagnostics(d,comp):
 rows=[];ext=[]
 for (year,pid,cat),g in d.groupby(['season','player_id','category'],dropna=False):
  g=g[g.epa.notna()].sort_values(['epa','game_id','play_id']);e=g.assign(abs_epa=g.epa.abs()).sort_values(['abs_epa','game_id','play_id'],ascending=[False,True,True]).head(5)
  t=stats(g);total=t['sum_epa'];absolute=g.epa.abs().sum();trim=g.drop(index=e.index)
  rows.append(dict(season=year,player_id=pid,category=cat,n=len(g),sum_epa=total,top5_abs_sum=e.epa.abs().sum(),total_abs_sum=absolute,top5_abs_share=e.epa.abs().sum()/absolute if absolute else None,top5_signed_sum=e.epa.sum(),mean_full=t['mean_epa'],mean_without_top5=trim.epa.mean() if len(trim) else None,sum_share_signed=e.epa.sum()/total if total else None))
  ext.extend(e.to_dict('records'))
 return pd.DataFrame(rows),pd.DataFrame(ext)

def stability(comp,cat):
 rows=[]
 m=comp[(comp.definition=='main')&comp.position_class.eq('qb')&comp.status.eq('legible')]
 for year in sorted(m.season.unique()):
  if year+1 not in m.season.unique():continue
  j=m[m.season.eq(year)].merge(m[m.season.eq(year+1)],on='player_id',suffixes=('_t','_next'))
  for field in ['a_mean','b_mean','difference','b_pct_all']:
   rows.append(dict(season=year,next_season=year+1,field=field,n_pairs=len(j),pearson=j[field+'_t'].corr(j[field+'_next']) if len(j)>2 else None,spearman=j[field+'_t'].corr(j[field+'_next'],method='spearman') if len(j)>2 else None))
  for category in CATS:
   c=cat[cat.category.eq(category)];z=j[['player_id']].merge(c[c.season.eq(year)],on='player_id').merge(c[c.season.eq(year+1)],on='player_id',suffixes=('_t','_next'))
   for field in (['pct_all','sum_epa'] if category=='sack' else ['pct_all']):
    rows.append(dict(season=year,next_season=year+1,field=category+'_'+field,n_pairs=len(z),pearson=z[field+'_t'].corr(z[field+'_next']) if len(z)>2 else None,spearman=z[field+'_t'].corr(z[field+'_next'],method='spearman') if len(z)>2 else None))
 return pd.DataFrame(rows)

def group_extremes(d,comp):
 rows=[]
 for (year,pid),g in d.groupby(['season','player_id'],dropna=False):
  values={}
  for label,cats in [('A',['progression']),('B',GROUPS['main'])]:
   p=g[g.category.isin(cats)&g.epa.notna()].copy();p['abs_epa']=p.epa.abs()
   top=p.sort_values(['abs_epa','game_id','play_id'],ascending=[False,True,True]).head(5);rem=p.drop(top.index)
   values[label]=dict(n=len(p),mean=p.epa.mean(),sum=p.epa.sum(),top5_signed=top.epa.sum(),top5_abs_share=top.epa.abs().sum()/p.epa.abs().sum() if p.epa.abs().sum() else None,mean_without_top5=rem.epa.mean() if len(rem) else None)
  row=dict(season=year,player_id=pid)
  for label,v in values.items():row.update({label+'_'+k:x for k,x in v.items()})
  row['difference_full']=row['A_mean']-row['B_mean'];row['difference_without_top5_each']=row['A_mean_without_top5']-row['B_mean_without_top5'] if row['A_mean_without_top5'] is not None and row['B_mean_without_top5'] is not None else None
  rows.append(row)
 return pd.DataFrame(rows)

def select_examples(d,c,league,out):
 cur=c.season.max();m=c[(c.season.eq(cur))&c.definition.eq('main')&c.position_class.eq('qb')];ok=m[m.status.eq('legible')];a_level=league[(league.season.eq(cur))&league.category.eq('progression')].mean_epa.iloc[0]
 expanded=c[c.season.eq(cur)&c.definition.eq('S2')][['player_id','difference']].rename(columns={'difference':'s2_difference'})
 sens=ok.merge(expanded,on='player_id');sens['sensitivity']=(sens.s2_difference-sens.difference).abs()
 near=ok.assign(distance=ok.difference.abs());low=m[(m.a_n_epa>=100)&(m.b_n_epa>0)&(m.b_n_epa<25)]
 criteria=[('high_A_gap',ok[ok.a_mean>a_level],['difference','player_id'],[False,True]),('high_B',ok,['b_mean','player_id'],[False,True]),('near_zero',near,['distance','player_id'],[True,True]),('sack_sensitive',sens,['sensitivity','player_id'],[False,True]),('low_support',low,['b_n_epa','player_id'],[True,True])]
 cases=[]
 for name,frame,keys,ascending in criteria:
  if frame.empty:cases.append(dict(criterion=name,status='unavailable'));continue
  chosen=frame.sort_values(keys,ascending=ascending).iloc[0];pid=chosen.player_id;plays=d[d.season.eq(cur)&d.player_id.eq(pid)].copy();plays.to_csv(out/f'examples/{name}_all_plays.csv',index=False)
  plays.assign(abs_epa=plays.epa.abs()).sort_values(['abs_epa','game_id','play_id'],ascending=[False,True,True]).head(12).to_csv(out/f'examples/{name}_extremes.csv',index=False)
  cases.append(dict(criterion=name,status='available',selection=chosen.to_dict(),all_plays=f'examples/{name}_all_plays.csv',extremes=f'examples/{name}_extremes.csv'))
 write(out/'examples/index.json',cases)

def revisions(previous,out,d):
 if not previous:return dict(status='initial_frozen_copy',changed=[],added=None,removed=None)
 old=pd.read_parquet(Path(previous)/'plays.parquet').set_index(KEY);n=d.set_index(KEY);changes=[]
 columns=[c for c in d.columns if c not in KEY]
 for k in old.index.intersection(n.index):
  cols=[c for c in columns if c not in old.columns or not ((pd.isna(old.at[k,c]) and pd.isna(n.at[k,c])) or old.at[k,c]==n.at[k,c])]
  if cols:changes.append(dict(game_id=k[0],play_id=k[1],fields=cols,before={c:old.at[k,c] for c in cols if c in old.columns},after={c:n.at[k,c] for c in cols}))
 return dict(status='compared',previous_manifest=sha(Path(previous)/'manifest.json'),added=[list(k) for k in n.index.difference(old.index)],removed=[list(k) for k in old.index.difference(n.index)],changed=changes)

def fixed_spec():
 root=Path(__file__).parent
 contract=root.parents[1]/'docs/plans/qb-structure-production-v1/RESEARCH-CONTRACT.md'
 return dict(metricVersion=VERSION,classificationVersion=VERSION,groups=GROUPS,categories=CATS,main_start=2023,current_season=2026,code={name:sha(root/name) for name in ['common.py','classify.py','run.py']},contractSha256=sha(contract))


def build(s,out,previous=None):
 s=Path(s);verify(s);out=new(out)
 for sub in ['audit','players','examples']:(out/sub).mkdir()
 write(out/'fixed.json',fixed_spec())
 (out/'classification-contract.md').write_bytes((Path(__file__).parents[2]/'docs/plans/qb-structure-production-v1/RESEARCH-CONTRACT.md').read_bytes())
 d=load(s,out);d.to_parquet(out/'plays.parquet',index=False);historical=d[d.season.eq(2022)];historical.to_parquet(out/'audit/plays_2022.parquet',index=False)
 main=d[d.season.ge(2023)].copy();cat,comp=aggregate(main);cat.to_csv(out/'categories.csv',index=False);comp.to_csv(out/'comparisons.csv',index=False)
 league=[]
 for year,g in main[main.position_class.eq('qb')].groupby('season'):
  for category in CATS:league.append(dict(season=year,category=category,**stats(g[g.category.eq(category)]),pct_all=100*g.category.eq(category).mean()))
 league=pd.DataFrame(league);league.to_csv(out/'league.csv',index=False)
 cb,cs=contextual(main[main.position_class.eq('qb')]);cb.to_csv(out/'context_bins.csv',index=False);cs.to_csv(out/'context_summary.csv',index=False)
 diag,ext=diagnostics(main,comp);diag.to_csv(out/'extreme_diagnostics.csv',index=False);ext.to_parquet(out/'extreme_plays.parquet',index=False)
 stability(comp,cat).to_csv(out/'stability.csv',index=False)
 group_extremes(main,comp).to_csv(out/'group_extremes.csv',index=False)
 for pid,g in main[main.player_id.notna()].groupby('player_id'):
  write(out/f'players/{pid}.json',dict(schemaVersion=1,metricVersion=VERSION,player_id=pid,categories=cat[cat.player_id.eq(pid)].to_dict('records'),comparisons=comp[comp.player_id.eq(pid)].to_dict('records'),plays=g.to_dict('records')))
 select_examples(main,comp,league,out)
 write(out/'revision.json',revisions(previous,out,d));write(out/'environment.json',dict(python=sys.version,platform=platform.platform(),pandas=pd.__version__,numpy=np.__version__))
 index=dict(schemaVersion=1,metricVersion=VERSION,classificationVersion=VERSION,status='experimental_review_before_integration',sourceManifestSha256=sha(s/'sources.json'),sourceManifest=str(s/'sources.json'),periods=sorted(main.season.unique().tolist()),coverage='coverage.json',elementaryPlays='plays.parquet',historicalAudit2022='audit/plays_2022.parquet',categories='categories.csv',sensitivities='comparisons.csv',league='league.csv',details='players/{gsis_id}.json',fixed='fixed.json',classificationContract='classification-contract.md',figures='figures/index.json',examples='examples/index.json',context='context_bins.csv',mainPopulation=len(main),audit2022Population=len(historical),players=sorted(main.player_id.dropna().unique().tolist()),statuses=['available','legible','low_support','unavailable_no_opportunities','unavailable_epa','unknown_or_conflicting'],attribution='FTN Data via nflverse, CC BY-SA 4.0; transformed charting. PBP/roster nflverse. No endorsement.',limits=['observational_situational_not_causal','DES_not_registered_progression','not_complete_inside_outside_structure_partition','play_EPA_not_isolated_QB_contribution'])
 write(out/'index.json',index)
 write(out/'manifest.json',dict(schemaVersion=1,metricVersion=VERSION,sourceManifestSha256=sha(s/'sources.json'),files=[dict(path=str(p.relative_to(out)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.rglob('*')) if p.is_file()]))
 print(main.groupby('season').category.value_counts().to_string());return out

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--sources',required=True);a.add_argument('--out',required=True);a.add_argument('--previous');v=a.parse_args();build(v.sources,v.out,v.previous)
