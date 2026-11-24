"""Separate stages: build, develop/freeze, evaluate, refit, fixed-model apply."""
import argparse, platform, subprocess
import pandas as pd
from common import *
from risk_model import blocks, fit_reference, fit_context, predict
from evaluate import performance, calibration, comparisons, aggregate

def dataset(build):
    build=Path(build);m=read(build/'manifest.json')
    if sha(build/'dataset.parquet')!=m['dataset_sha256']: raise ValueError('Dataset hash changed')
    return pd.read_parquet(build/'dataset.parquet')

def environment(out):
    write(Path(out)/'environment.json',dict(python=sys.version,platform=platform.platform(),
        dependencies=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines(),
        code_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(HERE.glob('*.py'))},
        note='Environment inventory excluded from scientific byte equality; predictions/parameters never excluded'))

def fit_set(train,C,year):
    return {**{k:fit_reference(train,k,year) for k in ['B0','B1','B2']},'C':fit_context(train,C,year)}

def predict_set(models,d):return {k:predict(v,d) for k,v in models.items()}

def save_eval(d,pred,out,year):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    performance(d,pred).to_csv(out/'metrics.csv',index=False)
    calibration(d,pred).to_csv(out/'calibration.csv',index=False)
    write(out/'paired_bootstrap.json',comparisons(d,pred))
    p=d.copy()
    for k,v in pred.items():p['p_interception_'+k]=v
    p.to_parquet(out/'pass_predictions.parquet',index=False)
    for k,v in pred.items():aggregate(d,v,f'XINT-FTN-{k}-v1-evaluation{year}').to_csv(out/f'players_{k}.csv',index=False)

def develop(build,out):
    out=new_dir(out);d=dataset(build);cfg=config();all_eval=[];c_predictions={str(c):[] for c in cfg['C_grid']};refs={k:[] for k in ['B0','B1','B2']}
    (out/'models').mkdir()
    for year in cfg['development_years']:
        train,ev=blocks(d[d.season.le(2024)],year);all_eval.append(ev)
        for k in refs:
            m=fit_reference(train,k,year);write(out/f'models/{k}_{year}.json',m);refs[k].append(predict(m,ev))
        for c in cfg['C_grid']:
            m=fit_context(train,c,year);write(out/f'models/C_{c}_{year}.json',m);c_predictions[str(c)].append(predict(m,ev))
    ev=pd.concat(all_eval,ignore_index=True);pred={k:np.concatenate(v) for k,v in refs.items()}
    scores=[]
    for c in cfg['C_grid']:
        ps=np.concatenate(c_predictions[str(c)])
        rows=performance(ev,{'C':ps});score=float(rows.query('group=="all"').log_loss.iloc[0]);scores.append((score,c))
    _,chosen_c=min(scores);pred['C']=np.concatenate(c_predictions[str(chosen_c)])
    pm=performance(ev,pred);bs=comparisons(ev,pred)
    context_calibration=all(.8<=float(pm[(pm.model=='C')&(pm.group==g)].observed_expected_ratio.iloc[0])<=1.25 for g in ['ftn_1','ftn_0'])
    useful=context_calibration and all(bs['all']['C-'+k]['log_loss']['high']<0 and bs['all']['C-'+k]['brier']['delta']<=.0001 for k in ['B1','B2'])
    reference=min(['B1','B2'],key=lambda k:(float(pm[(pm.model==k)&(pm.group=='all')].log_loss.iloc[0]),k))
    selected='C' if useful else reference
    selection=dict(selected=selected,chosen_C=chosen_c,context_useful=useful,context_calibration_gate=context_calibration,
        C_grid_scores=[dict(C=c,pooled_log_loss=s) for s,c in scores],decision_data_years=[2023,2024],
        rule=cfg['selection'],paired=bs['all'],no_2025_or_2026_selection=True)
    write(out/'selection.json',selection);save_eval(ev,pred,out/'development',2024)
    for year,ev2 in ev.groupby('season'):
        idx=ev.season.eq(year).to_numpy();performance(ev2,{k:v[idx] for k,v in pred.items()}).to_csv(out/f'metrics_{year}.csv',index=False)
    train=d[d.season.between(2022,2024)];models=fit_set(train,chosen_c,2025)
    for k,m in models.items():write(out/f'evaluation_models/{k}.json',m)
    freeze=dict(format='xint-research-freeze-v1',config=cfg,config_sha256=sha(HERE/'config.json'),
        contract_sha256=sha(DOC/'RESEARCH-CONTRACT.md'),selection=selection,
        evaluation_model_hashes={k:sha(out/f'evaluation_models/{k}.json') for k in models},
        code_sha256={p.name:sha(p) for p in [HERE/'common.py',HERE/'data.py',HERE/'risk_model.py',HERE/'evaluate.py',HERE/'run.py']},
        retrospective_temporal=True,target='interception',not_M3=True)
    write(out/'freeze.json',freeze);environment(out)
    print(json.dumps(dict(selected=selected,C=chosen_c,context_useful=useful,dev_metrics=pm.to_dict('records')),indent=2),flush=True)

def verified_freeze(development):
    dev=Path(development);f=read(dev/'freeze.json')
    if sha(HERE/'config.json')!=f['config_sha256'] or sha(DOC/'RESEARCH-CONTRACT.md')!=f['contract_sha256']:raise ValueError('Frozen contract/config changed')
    for name,digest in f['code_sha256'].items():
        actual=sha(HERE/name)
        if actual!=digest:
            # Exact, recorded output-only repair; model/feature/evaluation code remains frozen.
            amendment=read(DOC/'evidence/output-fix.json')
            if not (name=='run.py' and amendment['before']==digest and amendment['after']==actual
                    and amendment['original_freeze_sha256']==sha(dev/'freeze.json')):
                raise ValueError(f'Frozen implementation changed: {name}')
    for k,digest in f['evaluation_model_hashes'].items():
        if sha(dev/f'evaluation_models/{k}.json')!=digest:raise ValueError('Frozen model changed')
    return f

def evaluate(build,development,out):
    out=new_dir(out);d=dataset(build);f=verified_freeze(development);_,ev=blocks(d,2025)
    models={k:read(Path(development)/f'evaluation_models/{k}.json') for k in f['evaluation_model_hashes']}
    if any(max(m['train_years'])>=2025 for m in models.values()):raise ValueError('Evaluation model temporal leakage')
    save_eval(ev,predict_set(models,ev),out,2025)
    write(out/'receipt.json',dict(freeze_sha256=sha(Path(development)/'freeze.json'),evaluation_year=2025,
        selected=f['selection']['selected'],no_test_correction=True,description='Retrospective temporal out-of-fit evaluation; previously examined season'))
    environment(out);print(pd.read_csv(out/'metrics.csv').to_string(index=False),flush=True)

def refit(build,development,out):
    out=new_dir(out);d=dataset(build);f=verified_freeze(development);train=d[d.season.between(2022,2025)]
    selected=f['selection']['selected'];c=f['selection']['chosen_C']
    m=fit_context(train,c,2026) if selected=='C' else fit_reference(train,selected,2026)
    m['model_id']=f'XINT-FTN-{selected}-v1-fit2022-2025' if selected!='B2' else 'XINT-FTN-B2-v1-fit2025'
    write(out/'model.json',m)
    write(out/'fixed.json',dict(model_id=m['model_id'],model_sha256=sha(out/'model.json'),
        development_freeze_sha256=sha(Path(development)/'freeze.json'),selected=selected,target='interception',
        risk_input='is_interception_worthy',fit_years=m['train_years'],update_policy='Apply only. Never fit during data update.',
        code_sha256={p.name:sha(p) for p in [HERE/'common.py',HERE/'risk_model.py']},
        interpretation='Retrospective conditional probability. FTN charting may know the outcome; not pre-snap prediction or responsibility.'))
    environment(out);print('Fixed',m['model_id'],sha(out/'model.json'),flush=True)

def load_fixed(final):
    final=Path(final);fixed=read(final/'fixed.json')
    if sha(final/'model.json')!=fixed['model_sha256']:raise ValueError('Fixed model hash mismatch')
    for name,digest in fixed['code_sha256'].items():
        if sha(HERE/name)!=digest:raise ValueError('Fixed inference implementation changed')
    return fixed,read(final/'model.json')

def package(d,ps,final,out,coverage,source_manifest):
    out=new_dir(out);fixed,m=load_fixed(final);model_id=fixed['model_id']
    q=aggregate(d,ps,model_id);q.to_csv(out/'players.csv',index=False)
    z=d.copy();z['model_id']=model_id;z['p_interception_given_ftn']=ps
    z.to_parquet(out/'pass_predictions.parquet',index=False)
    performance(d,{fixed['selected']:ps}).to_csv(out/'metrics.csv',index=False)
    calibration(d,{fixed['selected']:ps}).to_csv(out/'calibration.csv',index=False)
    write(out/'coverage.json',coverage);write(out/'sources.json',source_manifest)
    write(out/'model.json',m);write(out/'fixed.json',fixed)
    players=json.loads(q.to_json(orient='records',double_precision=15))
    # Recompute the canonical JSON total from JSON contributions for exact consumer equality.
    for row in players:
        row['expected_interceptions']=row['expected_from_ftn_1']+row['expected_from_ftn_0']
        row['observed_minus_expected']=row['observed_interceptions']-row['expected_interceptions']
        row['difference_per_100_passes']=100*row['observed_minus_expected']/row['eligible_passes']
    write(out/'consumer/index.json',dict(schemaVersion=1,packageKind='expected-observed-interceptions-research',
        model=fixed,season=2026,coverage=coverage,players=players,
        summary=dict(passes=len(d),games=d.game_id.nunique(),observed_interceptions=int(d.interception.sum()),
            expected_interceptions=float(q.expected_from_ftn_1.sum())+float(q.expected_from_ftn_0.sum()),
            expected_from_ftn_1=float(q.expected_from_ftn_1.sum()),expected_from_ftn_0=float(q.expected_from_ftn_0.sum())),
        attribution='FTN Data via nflverse · CC BY-SA 4.0; transformed; no endorsement',
        interpretation='Retrospective, conditional on FTN charting possibly informed by outcome. Residual is not luck, blame, decision quality, or M3 interception-worthy expectation.',
        smallSupportPolicy='All players retained; small_support below 100 eligible passes; non-QB separately identified. No player skill intervals.'))
    for gsis,g in z.groupby('passer_player_id',sort=True):
        play_rows=json.loads(g.to_json(orient='records',double_precision=15))
        write(out/f'consumer/players/{gsis}.json',dict(model_id=model_id,gsis_id=gsis,plays=play_rows))
    cases(q,z,out);environment(out)
    write(out/'integrity.json',dict(files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ['integrity.json','environment.json']}))
    print(q[['name','position_class','eligible_passes','observed_interceptions','expected_interceptions','observed_minus_expected']].to_string(index=False),flush=True)

def cases(q,z,out):
    (out/'cases').mkdir(exist_ok=True)
    support=q[(q.position_class=='qb')&q.eligible_passes.ge(100)].copy();small=q.sort_values(['eligible_passes','gsis_id'])
    if support.empty:raise ValueError('No supported QBs for contracted examples')
    near=support.assign(abs_residual=support.observed_minus_expected.abs()).sort_values(['abs_residual','gsis_id']).iloc[0]
    above=support.sort_values(['observed_minus_expected','gsis_id'],ascending=[False,True]).iloc[0]
    below=support.sort_values(['observed_minus_expected','gsis_id']).iloc[0]
    nonworthy=support[support.observed_in_ftn_0.gt(0)].sort_values(['observed_in_ftn_0','gsis_id'],ascending=[False,True])
    chosen={'near_identity':near,'above_identity':above,'below_identity':below,'low_support':small.iloc[0]}
    if len(nonworthy):chosen['interception_in_ftn_0']=nonworthy.iloc[0]
    rows=[]
    for tag,row in chosen.items():
        g=z[z.passer_player_id.eq(row.gsis_id)];g.to_csv(out/f'cases/{tag}_all_plays.csv',index=False)
        g[g.interception.eq(1)|g.is_interception_worthy.eq(1)].to_csv(out/f'cases/{tag}_events_and_ftn.csv',index=False)
        rows.append(dict(case=tag,**row.to_dict(),evidence_all_plays=f'cases/{tag}_all_plays.csv',evidence_not_just_events=True))
    write(out/'cases.json',dict(rule='Precontracted deterministic descriptive examples; extremes are selected, not a random sample or video validation.',cases=rows))

def apply(build,store,final,out):
    d=dataset(build);d=d[d.season.eq(2026)].copy();fixed,m=load_fixed(final)
    if max(m['train_years'])>=2026:raise ValueError('Application model chronology')
    package(d,predict(m,d),final,out,read(Path(build)/'coverage.json'),verify_manifest(store))

def main():
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['build','develop','evaluate','refit','apply']);
    a.add_argument('--store',default=str(STORE));a.add_argument('--build');a.add_argument('--development');a.add_argument('--final');a.add_argument('--out',required=True);v=a.parse_args();offline()
    if v.stage=='build':
        from data import build
        build(v.store,v.out)
    elif v.stage=='develop':develop(v.build,v.out)
    elif v.stage=='evaluate':evaluate(v.build,v.development,v.out)
    elif v.stage=='refit':refit(v.build,v.development,v.out)
    else:apply(v.build,v.store,v.final,v.out)

if __name__=='__main__':main()
