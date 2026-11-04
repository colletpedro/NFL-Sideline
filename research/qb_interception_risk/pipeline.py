"""Bounded offline research CLI. Acquisition is a separate explicit command."""
from pathlib import Path
import argparse,json,platform,importlib.metadata,hashlib
import numpy as np
import pandas as pd
from acquire import sha
from dataset import build,dump,verify_sources
from model import fit,features,export_model,predict_json
from evaluation import metrics,calibration,paired_game_bootstrap,groups,qb_aggregate

HERE=Path(__file__).resolve().parent

def load_dataset(build_dir):
 b=Path(build_dir); manifest=json.loads((b/'build_manifest.json').read_text())
 if manifest['gate']!='PASS' or sha(b/'dataset.parquet')!=manifest['dataset_sha256']: raise ValueError('Dataset hash/audit gate failed')
 return pd.read_parquet(b/'dataset.parquet')
def destination(out):
 out=Path(out)
 if out.exists(): raise FileExistsError(f'Never overwrite a run: {out}')
 out.mkdir(parents=True); return out

def temporal(d,train_years,test_year):
 if max(train_years)>=test_year: raise ValueError('Train reaches evaluation year')
 train=d[d.season.isin(train_years)].copy(); test=d[d.season.eq(test_year)].copy()
 if train.empty or test.empty: raise ValueError('Empty temporal split')
 if set(train.game_id)&set(test.game_id): raise ValueError('Game split leakage')
 if not (train.game_date.max()<test.game_date.min()): raise ValueError('Non chronological dates')
 return train,test

def develop(build_dir,out):
 out=destination(out); d=load_dataset(build_dir); design=json.loads((HERE/'design.json').read_text()); history=[]; chosen={}
 for variant in design['variants']:
  scores=[]
  for C in design['C_grid']:
   loss=0.; n=0
   for fold in design['folds']:
    train,val=temporal(d,fold['train'],fold['validation']); model=fit(train,variant,C,design)
    p=model.predict_proba(features(val,variant))[:,1]; p0=np.full(len(val),train.is_interception_worthy.mean())
    m=metrics(val.is_interception_worthy,p); m0=metrics(val.is_interception_worthy,p0)
    history.append(dict(variant=variant,C=C,train_years=fold['train'],validation=fold['validation'],model=m,constant=m0))
    loss+=m['log_loss']*len(val); n+=len(val)
   scores.append((loss/n,C))
  chosen[variant]=min(scores)[1]
  for fold in design['folds']:
   train,val=temporal(d,fold['train'],fold['validation']); pipe=fit(train,variant,chosen[variant],design); p=pipe.predict_proba(features(val,variant))[:,1]
   pred=val[['game_id','play_id','season','is_interception_worthy']].copy(); pred['probability']=p; pred['constant_probability']=train.is_interception_worthy.mean(); pred.to_parquet(out/f'development_{variant}_{fold["validation"]}.parquet',index=False)
  train=d[d.season.isin(design['final_train'])]; pipe=fit(train,variant,chosen[variant],design); artifact=export_model(pipe,variant,chosen[variant],design['final_train'])
  # JSON implementation must match sklearn before any final test access.
  np.testing.assert_allclose(predict_json(artifact,train),pipe.predict_proba(features(train,variant))[:,1],atol=1e-13,rtol=1e-12)
  dump(out/f'model_{variant}_2022_2024.json',artifact)
 dump(out/'development_metrics.json',history)
 freeze=dict(version=1,design=design,chosen_C=chosen,dataset_sha256=sha(Path(build_dir)/'dataset.parquet'),design_sha256=sha(HERE/'design.json'),contract_sha256=sha(HERE.parents[1]/'docs/plans/qb-interception-risk-baseline-v1/RESEARCH-CONTRACT.md'),models={v:sha(out/f'model_{v}_2022_2024.json') for v in design['variants']},constant_prevalence=float(d[d.season.isin(design['final_train'])].is_interception_worthy.mean()),notice='Created before first final temporal evaluation. No adjustment to 2025 performance permitted.')
 dump(out/'frozen_config.json',freeze)
 dump(out/'environment.json',dict(python=platform.python_version(),platform=platform.platform(),packages={v:importlib.metadata.version(v) for v in ['numpy','pandas','pyarrow','scikit-learn','scipy','matplotlib']},code_hashes={p.name:sha(p) for p in sorted(HERE.glob('*.py'))}))
 print('Frozen C and config SHA:',chosen,sha(out/'frozen_config.json'),flush=True)

def frozen(build_dir,dev_dir):
 dev=Path(dev_dir); f=json.loads((dev/'frozen_config.json').read_text()); d=load_dataset(build_dir)
 if sha(Path(build_dir)/'dataset.parquet')!=f['dataset_sha256']: raise ValueError('Freeze dataset mismatch')
 if sha(HERE/'design.json')!=f['design_sha256']: raise ValueError('Design changed after freeze')
 for v,h in f['models'].items():
  if sha(dev/f'model_{v}_2022_2024.json')!=h: raise ValueError('Frozen model changed')
 return d,f

def evaluate(build_dir,dev_dir,out):
 out=destination(out); d,f=frozen(build_dir,dev_dir); des=f['design']; train,test=temporal(d,des['final_train'],des['final_test']); p0=np.full(len(test),f['constant_prevalence']); result={}
 for v in des['variants']:
  m=json.loads((Path(dev_dir)/f'model_{v}_2022_2024.json').read_text()); p=predict_json(m,test)
  pred=test[['game_id','play_id','season','week','passer_player_id','is_interception_worthy']].copy(); pred['probability']=p; pred['constant_probability']=p0; pred.to_parquet(out/f'test_predictions_{v}.parquet',index=False)
  result[v]=dict(model=metrics(test.is_interception_worthy,p),constant=metrics(test.is_interception_worthy,p0),paired_game_bootstrap=paired_game_bootstrap(test,p,p0,des['bootstrap_replicates'],des['seed']))
  dump(out/f'calibration_{v}.json',calibration(test.is_interception_worthy,p,des['calibration_edges'])); dump(out/f'groups_{v}.json',groups(test,p,p0))
  pd.DataFrame({'feature':m['feature_names'],'coefficient_per_standardized_unit_or_category':m['coefficients']}).to_csv(out/f'coefficients_{v}.csv',index=False)
 dump(out/'metrics.json',result); dump(out/'evaluation_receipt.json',dict(frozen_config_sha256=sha(Path(dev_dir)/'frozen_config.json'),protocol='2025 single final temporal evaluation; later identical reruns are reproduction only',test_year=2025))
 print(json.dumps(result,indent=2),flush=True)

def apply(build_dir,dev_dir,out):
 out=destination(out); d,f=frozen(build_dir,dev_dir); des=f['design']; train,test=temporal(d,des['application_train'],des['application']['season'])
 if not test.week.between(*des['application']['weeks']).all(): raise ValueError('Application crosses W1-7')
 for v in des['variants']:
  pipe=fit(train,v,f['chosen_C'][v],des); m=export_model(pipe,v,f['chosen_C'][v],des['application_train']); dump(out/f'model_{v}_2022_2025.json',m); p=predict_json(m,test)
  np.testing.assert_allclose(p,pipe.predict_proba(features(test,v))[:,1],atol=1e-13,rtol=1e-12)
  pred=test[['game_id','play_id','season','week','passer_player_id','passer_player_name','posteam','is_interception_worthy','interception']].copy(); pred['probability']=p; pred.to_parquet(out/f'application_predictions_{v}.parquet',index=False)
  q=qb_aggregate(test,p,des['bootstrap_replicates'],des['seed']); q.to_csv(out/f'qb_{v}.csv',index=False)
  dump(out/f'application_diagnostics_{v}.json',dict(metrics_descriptive_only=metrics(test.is_interception_worthy,p),calibration=calibration(test.is_interception_worthy,p,des['calibration_edges'])))
 a=pd.read_csv(out/'qb_context.csv'); b=pd.read_csv(out/'qb_depth.csv'); compare=a.merge(b,on='passer_player_id',suffixes=('_context','_depth'),validate='one_to_one'); compare['adjustment_change_per100']=compare.difference_per100_depth-compare.difference_per100_context; compare.to_csv(out/'qb_sensitivity.csv',index=False)
 dump(out/'application_receipt.json',dict(frozen_config_sha256=sha(Path(dev_dir)/'frozen_config.json'),passes=len(test),games=test.game_id.nunique(),passers=test.passer_player_id.nunique(),expected_sum=float(a.expected.sum()),observed=int(test.is_interception_worthy.sum()),weeks=sorted(test.week.unique().tolist())))
 print('Application:',len(test),'passes',test.game_id.nunique(),'games',test.passer_player_id.nunique(),'passer IDs',flush=True)

def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
 for c in ['build','develop','evaluate','apply','reproduce']:
  a=sub.add_parser(c); a.add_argument('--out',required=True,type=Path)
  if c in ['build','reproduce']: a.add_argument('--store',required=True,type=Path)
  else: a.add_argument('--build',required=True,type=Path)
  if c in ['evaluate','apply','reproduce']: a.add_argument('--development',required=True,type=Path)
 args=p.parse_args()
 if args.command=='build': build(args.store,args.out)
 elif args.command=='develop': develop(args.build,args.out)
 elif args.command=='evaluate': evaluate(args.build,args.development,args.out)
 elif args.command=='apply': apply(args.build,args.development,args.out)
 else:
  # Replay frozen choices/models; no re-selection after seeing the final test.
  root=destination(args.out); build(args.store,root/'build'); evaluate(root/'build',args.development,root/'evaluation'); apply(root/'build',args.development,root/'application')
if __name__=='__main__': main()
