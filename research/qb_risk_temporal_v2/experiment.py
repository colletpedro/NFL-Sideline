"""Fixed retrospective candidates; no reserved-window data enter this module."""
from pathlib import Path
import json,shutil,importlib.metadata,platform
import numpy as np
import pandas as pd
from scipy.special import expit,logit
from common import *
from calibration_stats import scores,intercept_shift,diagnostic_calibration,stratified_paired
from drift import run_drift
from identity import presentation

def predict(artifact,d):
 if artifact['kind']=='constant':return np.full(len(d),artifact['probability'])
 p=predict_json(artifact['structure'],d)
 return expit(logit(p)+artifact.get('offset',0.))

def context_artifact(train,cal,train_years,cal_year):
 pipe=fit(train,'context',protocol()['C'],design());m=export_model(pipe,'context',protocol()['C'],train_years)
 np.testing.assert_allclose(predict_json(m,train),pipe.predict_proba(features(train,'context'))[:,1],atol=1e-13,rtol=1e-12)
 h=sha_text(m);delta=0. if cal_year is None else intercept_shift(cal.is_interception_worthy,predict_json(m,cal))
 if sha_text(m)!=h:raise ValueError('Structure changed during intercept-only calibration')
 return dict(kind='context',structure=m,offset=delta,calibration_year=cal_year,structure_sha256=h,calibration_n=len(cal),calibration_positive=int(cal.is_interception_worthy.sum()) if len(cal) else 0)

def sha_text(obj):
 import hashlib
 return hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()

def candidate_blocks(year):
 return ([2022] if year==2024 else [year-3,year-2],year-1)

def select(retro,pred):
 # Hard guard: 2026 and reserved rows can never contribute to selection.
 known_only(pred);z=pred[pred.season.isin(protocol()['selection_years'])].copy()
 if set(z.season.unique())!={2024,2025}:raise ValueError('Selection requires exactly both full historical evaluation seasons')
 result={};eligible=[];pooled={}
 for name in ['M2','M3']:
  per_year=[r for r in retro if r['candidate']==name and r['year'] in [2024,2025]]
  ok=len(per_year)==2 and all(r['model']['log_loss']<r['M1']['log_loss'] and r['model']['brier']<=r['M1']['brier'] and r['model']['pr_auc_average_precision']>r['M1']['pr_auc_average_precision'] for r in per_year)
  ci=stratified_paired(z,z[name],z.M1,protocol()['bootstrap_replicates'],protocol()['seed']);ok=ok and ci['ll']['high']<0
  score=scores(z.is_interception_worthy,z[name]);result[name]=dict(eligible=bool(ok),pooled=score,difference_vs_M1=ci,per_year_conditions_pass=bool(all(r['model']['log_loss']<r['M1']['log_loss'] and r['model']['brier']<=r['M1']['brier'] and r['model']['pr_auc_average_precision']>r['M1']['pr_auc_average_precision'] for r in per_year)))
  if ok:eligible.append(name);pooled[name]=score['log_loss']
 chosen=None
 if eligible:
  best=min(pooled.values());chosen='M2' if 'M2' in eligible and pooled['M2']<=best+1e-10 else min(eligible,key=lambda m:pooled[m])
 return dict(selected_contextual_candidate=chosen,reference_if_none='M1',selection_years=[2024,2025],results=result,decision='candidate_for_reserved_evaluation_only' if chosen else 'no_contextual_promotion')

def run(store,out,reference_dir=None):
 store=Path(store);out=destination(out);cfg=protocol()
 # Verify the copied inputs; raw bytes beyond W8 do not exist in this snapshot.
 verify_sources(store/'inputs/v1')
 for x in json.loads((store/'additional-sources.json').read_text())['files']:
  if sha(store/x['path'])!=x['sha256']:raise ValueError('Supplemental input changed')
 reference=Path(reference_dir) if reference_dir is not None else store/'reference-v1';check=json.loads((store/'reference-v1-check.json').read_text())
 if not check['passed']:raise ValueError('V1 reproduction not reconciled')
 d=known_only(load_dataset(reference/'build'));run_drift(d,store/'inputs/v1/sources.json',reference/'build/audit.json',out/'drift')
 models=out/'models';models.mkdir();allpred=[];splits=[];results=[];group_rows=[];calib={};fullpred=pd.DataFrame(index=d.index)
 for year in cfg['known_evaluation_years']:
  previous=year-1;tr,_,ev=blocks(d,[previous],None,year)
  # M0: exact preserved predictions, not a newly fit approximation.
  f=reference/('development/development_context_2024.parquet' if year==2024 else 'evaluation/test_predictions_context.parquet' if year==2025 else 'application/application_predictions_context.parquet')
  old=pd.read_parquet(f);j=ev[['game_id','play_id','is_interception_worthy']].merge(old[['game_id','play_id','is_interception_worthy','probability']],on=['game_id','play_id'],suffixes=('_d','_v1'),validate='one_to_one')
  if len(j)!=len(ev) or not j.is_interception_worthy_d.eq(j.is_interception_worthy_v1).all():raise ValueError('Preserved M0 keys/labels differ')
  m1=dict(kind='constant',probability=float(tr.is_interception_worthy.mean()),train_years=[previous]);m2=context_artifact(tr,d.iloc[:0], [previous],None)
  years,cal_year=candidate_blocks(year);train,ca,_=blocks(d,years,cal_year,year);m3=context_artifact(train,ca,years,cal_year)
  arts={'M1':m1,'M2':m2,'M3':m3}
  pred=ev[['game_id','play_id','season','season_type','week','passer_player_id','is_interception_worthy']].copy();pred['M0']=j.probability.to_numpy()
  for name,art in arts.items():pred[name]=predict(art,ev);dump(models/f'{name}_{year}.json',art)
  allpred.append(pred)
  if year==2026:fullpred.loc[ev.index,'M0']=pred.M0.to_numpy()
  for name in cfg['candidates']:
   p=pred[name].to_numpy();m=scores(ev.is_interception_worthy,p);base=scores(ev.is_interception_worthy,pred.M1.to_numpy());diff=paired_game_bootstrap(ev,p,pred.M1.to_numpy(),cfg['bootstrap_replicates'],cfg['seed'])
   diagnostic=diagnostic_calibration(ev,p,cfg['bootstrap_replicates'],cfg['seed']);record=dict(year=year,candidate=name,model=m,M1=base,difference_vs_M1=diff,calibration_diagnostic=diagnostic,period_status='known_retrospective_diagnostic')
   if name=='M3':
    raw=scores(ev.is_interception_worthy,predict_json(m3['structure'],ev));record['same_structure_before_offset_diagnostic']=raw
    if abs(raw['roc_auc']-m['roc_auc'])>1e-12 or abs(raw['pr_auc_average_precision']-m['pr_auc_average_precision'])>1e-12:raise ValueError('Intercept shift changed order-dependent discrimination')
   results.append(record)
   calib[f'{year}_{name}']=calibration(ev.is_interception_worthy,p,design()['calibration_edges'])
   for g in groups(ev,p,pred.M1.to_numpy()):group_rows.append(dict(year=year,candidate=name,**g))
   # Explicit temporal roles per key; models have no dependencies on evaluation labels.
   ty=list(range(2022,year)) if name=='M0' else [previous] if name in ['M1','M2'] else years
   cy=cal_year if name=='M3' else None
   part=d[['game_id','play_id','season','week']].copy();part['evaluation_year']=year;part['candidate']=name;part['role']=np.select([part.season.isin(ty),part.season.eq(cy),part.season.eq(year)],['structure_train' if name!='M1' else 'constant_train','calibration','evaluation_known'],default='unused');splits.append(part)
  print('Retrospective year complete',year,flush=True)
 predictions=pd.concat(allpred).sort_values(['season','game_id','play_id']).reset_index(drop=True);predictions.to_parquet(out/'predictions.parquet',index=False);pd.concat(splits).to_parquet(out/'splits.parquet',index=False)
 dump(out/'metrics.json',results);dump(out/'calibration_bins.json',calib);pd.DataFrame(group_rows).to_csv(out/'groups.csv',index=False)
 decision=select(results,predictions);dump(out/'selection.json',decision)
 # Freeze references and at most one promoted contextual candidate; preserve all candidates for audit.
 frozen=out/'frozen';frozen.mkdir();m0=json.loads((reference/'application/model_context_2022_2025.json').read_text());dump(frozen/'M0.json',dict(kind='context',structure=m0,offset=0.,calibration_year=None))
 shutil.copyfile(models/'M1_2026.json',frozen/'M1.json')
 if decision['selected_contextual_candidate']:
  chosen=decision['selected_contextual_candidate'];shutil.copyfile(models/f'{chosen}_2026.json',frozen/f'{chosen}.json')
 schedule=pd.read_csv(store/'inputs/v1/raw/schedules.csv');window=schedule[schedule.season.eq(2026)&schedule.game_type.eq('REG')&schedule.week.between(9,13)]
 window.to_csv(frozen/'reserved_schedule.csv',index=False)
 root=HERE.parents[1];contracts={p.name:sha(p) for p in [HERE/'protocol.json',root/'docs/plans/qb-risk-temporal-calibration-v2/EXPERIMENT-PROTOCOL.md',root/'docs/plans/qb-risk-temporal-calibration-v2/RESERVED-EVALUATION.md']}
 dump(frozen/'freeze.json',dict(version=2,selected=decision['selected_contextual_candidate'],references=['M0','M1'],reserved=cfg['reserved'],contracts=contracts,code_hashes={str(p.relative_to(root)):sha(p) for p in [HERE/n for n in ['common.py','experiment.py','calibration_stats.py','reserved.py']]+[V1_CODE/'model.py',V1_CODE/'dataset.py']},dataset_sha256=sha(reference/'build/dataset.parquet'),files={p.name:sha(p) for p in sorted(frozen.iterdir()) if p.is_file()},status='awaiting_mature_reserved_window; no independent confirmation yet'))
 roster=pd.read_parquet(store/'inputs/roster_weekly_2026.parquet');presentation(d,roster,out,fullpred)
 dump(out/'environment.json',dict(python=platform.python_version(),packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','pyarrow','matplotlib']},code_hashes={p.name:sha(p) for p in sorted(HERE.glob('*.py'))}))
 print('Decision',decision['decision'],decision['selected_contextual_candidate'],flush=True)
 return decision
