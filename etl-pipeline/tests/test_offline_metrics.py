"""Offline adapter tests do not use ignored Parquets or acquisition."""
import copy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys

import polars as pl
import pytest

from nfl_sideline_etl.offline_metrics import artifact
from nfl_sideline_etl.offline_metrics.__main__ import main
from nfl_sideline_etl.offline_metrics.inputs import read_inputs, read_source
from nfl_sideline_etl.offline_metrics.population import exclusion_reason
from nfl_sideline_etl.offline_metrics.statistics import COUNTS, Sums, accumulate, exact_sum
from nfl_sideline_etl.offline_metrics.validation import (
    CALENDAR_FIELDS, PBP_FIELDS, calendar_index, normalize_play, reconcile_raw,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / 'fixtures/offline_metrics'


@pytest.fixture
def source():
    calendars, plays, inputs = read_inputs([FIXTURE/'calendar.json'], [FIXTURE/'pbp.json'])
    return calendars, plays, inputs


def run(source, metadata=None):
    return artifact.calculate(*source, metadata)


def sums(result, game='synthetic-1', team='A', role='off', foundation='general'):
    return next(s for s in result['statistics.json'] if (s['game_id'],s['team'],s['role'],s['foundation']) == (game,team,role,foundation))


def fields(row):
    return {k: row[k] for k in (*COUNTS,'epa_sum')}


def audited(result, game='synthetic-1'):
    return next(a for a in result['game-audit.json'] if a['game_id']==game)


def test_hand_ledgers_and_roles(source):
    result = run(source)
    ledger = json.loads((FIXTURE/'ledger.json').read_text())
    for game, foundations in ledger.items():
        for f, expected in foundations.items():
            assert fields(sums(result,game,foundation=f)) == expected
            assert fields(sums(result,game,team='B',role='def',foundation=f)) == expected
    assert audited(result)['outside_pass_run_null_teams_n'] == 2
    assert audited(result)['raw_n'] == 10
    assert audited(result)['unique_n'] == 9
    assert audited(result)['duplicate_rows_ignored'] == 1
    assert audited(result)['exclusions'] == {'outside_pass_run':2}
    assert audited(result,'synthetic-3')['exclusions'] == {
        'kneel':1,'spike':1,'deleted':1,'special_teams':1,'two_point_conversion':1,
        'unknown_filter_flags':1,'outside_pass_run':2}
    assert all(result['reconciliation.json']['checks'].values())


@pytest.mark.parametrize('field,value', [('posteam',None),('defteam',None),('posteam','C'),('defteam','A')])
def test_candidate_teams_fail_before_even_conversion_filter(source,field,value):
    calendars,plays,inputs=copy.deepcopy(source)
    plays[0][field]=value
    plays[0]['two_point_attempt']=1
    with pytest.raises(ValueError,match='participant'):
        run((calendars,plays,inputs))


@pytest.mark.parametrize('field,value', [
    ('play_id',None),('play_id','NaN'),('play_id',True),('drive','Infinity'),
    ('season',2025),('week',2),('season_type','POST'),('season_type','PRE'),
    ('play_type',7),('posteam',''),('defteam','C'),('qb_kneel',2),('qb_spike',-1),
    ('play_deleted','oops'),('special_teams_play',0.5),('two_point_attempt',True),('epa','oops')])
def test_structural_invalid_even_outside_population(source,field,value):
    calendars,plays,inputs=copy.deepcopy(source)
    outside=next(p for p in plays if p['play_type'] is None)
    outside[field]=value
    with pytest.raises(ValueError):run((calendars,plays,inputs))


@pytest.mark.parametrize('flag', ['qb_kneel','qb_spike','play_deleted','special_teams_play','two_point_attempt'])
def test_unknown_flags_and_precedence(source,flag):
    games,_=calendar_index(source[0])
    row={**source[1][0],flag:None}
    assert exclusion_reason(normalize_play(row,games))=='unknown_filter_flags'
    row['qb_kneel']=1
    assert exclusion_reason(normalize_play(row,games))=='kneel'


@pytest.mark.parametrize('field,value', [('epa','2'),('drive',2),('posteam','B'),('qb_kneel',1)])
@pytest.mark.parametrize('outside',[False,True])
def test_replica_conflicts_including_excluded_rows(source,field,value,outside):
    calendars,plays,inputs=copy.deepcopy(source)
    row=next(p for p in plays if (p['play_type'] is None) == outside)
    replica={**row,field:value}
    if field=='posteam' and not outside:replica['defteam']='A'
    plays.append(replica)
    # Direct raw reconciliation deliberately precedes manifest/population checks.
    games,_=calendar_index(calendars)
    with pytest.raises(ValueError,match='Conflicting PBP replica'):
        reconcile_raw(plays,games)


def test_fractional_play_ids_never_truncated(source):
    games,_=calendar_index(source[0])
    row=source[1][0]
    unique,raw,dup=reconcile_raw([{**row,'play_id':'1.1'},{**row,'play_id':'1.9'}],games)
    assert [p['play_id'] for p in unique]==['1.1','1.9']
    assert sum(raw.values())==2 and not dup


@pytest.mark.parametrize('game_type,phase,round_', [('REG','REG','REG'),('POST','POST',None),('WC','POST','WC'),('DIV','POST','DIV'),('CON','POST','CON'),('SB','POST','SB')])
def test_phase_round(game_type,phase,round_):
    game=dict(game_id='g',season=2026,game_type=game_type,week=20,home_team='A',away_team='B')
    games,_=calendar_index([game])
    assert (games['g']['phase'],games['g']['round'])==(phase,round_)
    row=dict(zip(PBP_FIELDS, ['g',1,1,2026,phase,20,'A','B','pass',0,0,0,0,0,'1']))
    assert normalize_play(row,games)['phase']==phase
    if round_ not in (None,'REG','SB'):
        row['season_type']='SB'
        with pytest.raises(ValueError,match='round conflict'):normalize_play(row,games)


def test_absent_unknown_subset_complete_empty_and_zero_distinct(source):
    metadata=json.loads((FIXTURE/'metadata.json').read_text())
    result=run(source,metadata)
    assert audited(result)['completeness']=='UNKNOWN'
    assert sums(result)['scope']=='AUDITABLE_SUBSET'
    assert sums(result)['statistics_status']=='PARTIAL'
    assert audited(result,'synthetic-5')['eligible_content_n'] is None
    assert not any(s['game_id']=='synthetic-5' for s in result['statistics.json'])
    complete=sums(result,'synthetic-6')
    assert complete['eligible_n']==0 and complete['epa_sum'] is None and complete['completeness']=='COMPLETE'
    zero=sums(result,'synthetic-2',foundation='classified_pass')
    assert zero['epa_sum']=='0' and zero['epa_n']==2
    assert result['reconciliation.json']['calendar_without_pbp']==['synthetic-5','synthetic-6']


def test_manifest_counts_are_raw_unique_not_filtered(source):
    metadata=json.loads((FIXTURE/'metadata.json').read_text())
    metadata['games']['synthetic-1']={'completeness':'COMPLETE','expected_unique_rows':9,
        'evidence':{'basis':'SYNTHETIC_FINAL_MANIFEST','reference':'test'}}
    result=run(source,metadata)
    assert audited(result)['completeness']=='COMPLETE'
    assert sums(result)['eligible_n']==7
    metadata['games']['synthetic-1']['expected_unique_rows']=10
    result=run(source,metadata)
    assert audited(result)['completeness']=='PARTIAL'
    assert sums(result)['scope']=='AUDITABLE_SUBSET'
    assert not audited(result)['expected_raw_unique_count_matches']


@pytest.mark.parametrize('change', ['no_evidence','wrong_hash','no_expected','wrong_evidence','unknown_game','bad_timestamp','no_timestamp_evidence'])
def test_metadata_requires_bound_bytes_and_evidence(source,change):
    m=json.loads((FIXTURE/'metadata.json').read_text()); record=m['games']['synthetic-6']
    if change=='no_evidence':record.pop('evidence')
    elif change=='wrong_hash':m['pbp_sha256']=['0'*64]
    elif change=='no_expected':record.pop('expected_unique_rows')
    elif change=='wrong_evidence':record['evidence']={'basis':'scores filled'}
    elif change=='unknown_game':m['games']['not-scheduled']=record
    elif change=='bad_timestamp':record['available_at']={'value':'2026-10-08','evidence':record['evidence']}
    else:record['available_at']={'value':'2026-10-08T00:00:00Z'}
    with pytest.raises(ValueError):run(source,m)


def test_proven_metadata_separate_from_adapter_version(source):
    m=json.loads((FIXTURE/'metadata.json').read_text())
    digest=m['pbp_sha256'][0]
    proof={'basis':'SYNTHETIC_RECEIPT','reference':'test only'}
    m['sources']={digest:{'source_model_version':{'value':'synthetic-model-9','evidence':proof}}}
    m['games']['synthetic-6']['available_at']={'value':'2026-10-08T09:00:00-03:00','evidence':proof}
    result=run(source,m)
    assert result['manifest.json']['source_model_versions'][digest]['value']=='synthetic-model-9'
    assert result['manifest.json']['versions']['adapter']=='1.0.0'
    assert audited(result,'synthetic-6')['provenance']['available_at']['value']=='2026-10-08T12:00:00Z'
    assert not result['reconciliation.json']['historical_availability_certified']


def test_permutations_preserve_all_artifact_bytes(source):
    expected=artifact.json_bytes(run(source))
    rng=random.Random(5105)
    for _ in range(30):
        shuffled=copy.deepcopy(source)
        rng.shuffle(shuffled[0]);rng.shuffle(shuffled[1]);rng.shuffle(shuffled[2])
        assert artifact.json_bytes(run(shuffled))==expected


def test_parts_disjoint_after_global_dedup_and_overlapping_partitions(source):
    games,_=calendar_index(source[0])
    unique,_,_=reconcile_raw(source[1],games)
    plays=[p for p in unique if p['game_id']=='synthetic-1' and exclusion_reason(p) is None]
    whole=accumulate(games['synthetic-1'],plays)
    for cut in range(len(plays)+1):
        left=accumulate(games['synthetic-1'],plays[:cut]);right=accumulate(games['synthetic-1'],plays[cut:])
        for a,b,w in zip(left,right,whole):
            def acc(r):return Sums(**{k:r[k] for k in COUNTS},epa_sum=Decimal(r['epa_sum'] or '0'))
            assert acc(a).merge(acc(b)).serialize()==fields(w)
    overlapped=source[1][:8]+source[1][4:]
    merged,_,_=reconcile_raw(overlapped,games)
    assert merged==unique


def test_exact_cancellation_not_decimal_context_or_float_order_dependent():
    values=[Decimal('100000000000000000000000000000000000000000'),Decimal('0.000000000000000001'),Decimal('-100000000000000000000000000000000000000000')]
    with localcontext() as ctx:
        ctx.prec=2
        for perm in itertools.permutations(values):
            assert exact_sum(perm)==Decimal('0.000000000000000001')
            acc=Sums()
            for v in perm:acc.add(str(v))
            assert acc.serialize()['epa_sum']=='0.000000000000000001'


def test_all_missing_nonfinite_preserves_volume_and_null_sum(source):
    games,_=calendar_index(source[0])
    for value,field in [(None,'epa_missing_n'),('NaN','epa_nonfinite_n'),('Infinity','epa_nonfinite_n'),('-Infinity','epa_nonfinite_n')]:
        play=normalize_play({**source[1][0],'epa':value},games)
        row=next(s for s in accumulate(games[play['game_id']],[play]) if s['team']=='A' and s['role']=='off' and s['foundation']=='general')
        assert row['eligible_n']==1 and row[field]==1 and row['epa_sum'] is None and row['epa_n']==0


def test_calendar_conflicts_unknown_games_and_missing_columns(source):
    calendars,plays,inputs=copy.deepcopy(source)
    with pytest.raises(ValueError,match='Conflicting calendar'):
        calendar_index(calendars+[{**calendars[0],'home_team':'C'}])
    games,duplicates=calendar_index(calendars+[calendars[0]])
    assert duplicates=={'synthetic-1':1}
    with pytest.raises(ValueError,match='absent from calendar'):
        normalize_play({**plays[0],'game_id':'absent'},games)
    for key in PBP_FIELDS:
        row=plays[0].copy();row.pop(key)
        with pytest.raises(ValueError,match='Missing schema'):normalize_play(row,games)
    with pytest.raises(ValueError,match='outside explicit selection'):
        artifact.calculate(*source,seasons=(2025,))


def test_parquet_projection_float_round_trip_schema_and_empty(tmp_path,source):
    row={k:source[1][0][k] for k in PBP_FIELDS};row['epa']=0.10000000000000002
    row['play_id']=1.25
    path=tmp_path/'plays.parquet'
    pl.DataFrame([row]).write_parquet(path)
    rows,descriptor=read_source(path,'pbp')
    games,_=calendar_index(source[0])
    assert normalize_play(rows[0],games)['epa']=='0.10000000000000002'
    assert normalize_play(rows[0],games)['play_id']=='1.25'
    assert descriptor['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert descriptor['relevant_schema']['epa']=='Float64'
    pl.DataFrame([row]).clear().write_parquet(path)
    assert read_source(path,'pbp')[0]==[]
    pl.DataFrame([row]).drop('drive').write_parquet(path)
    with pytest.raises(ValueError,match='Missing schema'):read_source(path,'pbp')


def cli_args(output):
    return ['--calendar',str(FIXTURE/'calendar.json'),'--pbp',str(FIXTURE/'pbp.json'),
            '--metadata',str(FIXTURE/'metadata.json'),'--output',str(output)]


def test_cli_deterministic_new_destination_and_failures(tmp_path):
    a,b=tmp_path/'a',tmp_path/'b'
    assert main(cli_args(a))==main(cli_args(b))==0
    assert {p.name:p.read_bytes() for p in a.iterdir()}=={p.name:p.read_bytes() for p in b.iterdir()}
    with pytest.raises(SystemExit) as exc:main(cli_args(a))
    assert exc.value.code==2
    invalid=tmp_path/'invalid.json'
    doc=json.loads((FIXTURE/'pbp.json').read_text());doc['rows'][0]['posteam']=None
    invalid.write_text(json.dumps(doc))
    output=tmp_path/'failed';args=cli_args(output);args[3]=str(invalid)
    with pytest.raises(SystemExit):main(args)
    assert not output.exists() and not list(tmp_path.glob('.*.pending-*'))


def test_writer_cleanup_on_io_failure_and_no_clobber_race(tmp_path,source,monkeypatch):
    result=run(source);output=tmp_path/'out'
    original=Path.write_bytes
    def fail(path,data):
        if path.name=='statistics.json':raise OSError('simulated disk failure')
        return original(path,data)
    monkeypatch.setattr(Path,'write_bytes',fail)
    with pytest.raises(OSError):artifact.write_artifact(output,result)
    assert not output.exists() and not list(tmp_path.glob('.*.pending-*'))
    monkeypatch.setattr(Path,'write_bytes',original)
    rename=artifact.rename_exclusive
    def competitor(src,dst):
        dst.mkdir()
        rename(src,dst)
    monkeypatch.setattr(artifact,'rename_exclusive',competitor)
    with pytest.raises(FileExistsError):artifact.write_artifact(output,result)
    assert output.is_dir() and not list(output.iterdir())
    assert not list(tmp_path.glob('.*.pending-*'))


def test_public_output_forbidden_and_symlink(tmp_path):
    for output in (tmp_path/'web-ui/public/data/out',tmp_path/'web-ui/public/data'):
        with pytest.raises(ValueError,match='forbidden'):artifact.ensure_destination(output)
    public=tmp_path/'web-ui/public/data';public.mkdir(parents=True)
    link=tmp_path/'alias';link.symlink_to(public,target_is_directory=True)
    with pytest.raises(ValueError,match='forbidden'):artifact.ensure_destination(link/'out')


def test_cli_import_path_does_not_load_env_network_or_db(tmp_path):
    # Fail immediately if the offline path imports any acquisition/DB/env module.
    script='''
import importlib.abc, sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'dotenv','psycopg2','boto3','nflreadpy','requests','httpx','load_metrics','run_pipeline'}:
            raise AssertionError('Forbidden import: '+fullname)
sys.meta_path.insert(0,Guard())
from nfl_sideline_etl.offline_metrics.__main__ import main
main(sys.argv[1:])
'''
    # pytest's environment already supplies PYTHONPATH for the tested checkout.
    completed=subprocess.run([sys.executable,'-c',script,*cli_args(tmp_path/'guarded')],capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr


@pytest.mark.parametrize('case_id', ['unequal_week_volumes','single_tiny_positive','zero_and_negative','partial_epa',
    'classified_pass_vs_dropback','no_eligible_plays','all_epa_missing','population_boundaries',
    'identical_duplicates','defense_is_opponent_success'])
def test_e5a_independent_calculation_ledgers(case_id):
    case=next(c for c in json.loads((ROOT/'contracts/metrics/e5a-v1/fixtures/cases.json').read_text())['cases'] if c['id']==case_id)
    calendars=[dict(game_id=g['game_id'],season=g['season'],week=g['week'],game_type=g['phase'],home_team=g['teams'][0],away_team=g['teams'][1]) for g in case['games']]
    games,_=calendar_index(calendars)
    unique,_,_=reconcile_raw(case['plays'],games)
    team,role=case['query']['team'],case['query']['role']
    expected=case['expected']['stats']
    for foundation,check in expected.items():
        acc=Sums()
        for game in games.values():
            plays=[p for p in unique if p['game_id']==game['game_id'] and exclusion_reason(p) is None]
            row=next(s for s in accumulate(game,plays) if (s['team'],s['role'],s['foundation'])==(team,role,foundation))
            acc=acc.merge(Sums(**{k:row[k] for k in COUNTS},epa_sum=Decimal(row['epa_sum'] or '0')))
        got=acc.serialize()
        for key,value in check.items():
            if key in COUNTS:assert got[key]==value
            elif key=='epa_sum':assert (None if got[key] is None else Fraction(got[key]))==(None if value is None else Fraction(value))
            elif key=='epa':assert (None if not acc.epa_n else Fraction(acc.epa_sum)/acc.epa_n)==(None if value is None else Fraction(value))
            elif key=='success_rate':assert (None if not acc.epa_n else Fraction(acc.success_n,acc.epa_n))==(None if value is None else Fraction(value))


def test_file_partitions_overlap_order_and_path_independence(tmp_path):
    doc=json.loads((FIXTURE/'pbp.json').read_text())
    a,b=tmp_path/'a.json',tmp_path/'b.json'
    # Partition replicas overlap the original candidate and the excluded null-team row.
    a.write_text(json.dumps({**doc,'rows':doc['rows'][:12]}))
    b.write_text(json.dumps({**doc,'rows':doc['rows'][8:]}))
    left=read_inputs([FIXTURE/'calendar.json'],[a,b])
    right=read_inputs([FIXTURE/'calendar.json'],[b,a])
    assert artifact.json_bytes(run(left))==artifact.json_bytes(run(right))
    whole=run(read_inputs([FIXTURE/'calendar.json'],[FIXTURE/'pbp.json']))
    assert [fields(s) for s in run(left)['statistics.json']]==[fields(s) for s in whole['statistics.json']]
    assert run(left)['reconciliation.json']['duplicate_rows_ignored']==5
    moved=tmp_path/'moved';moved.mkdir()
    for src in (a,b,FIXTURE/'calendar.json'):(moved/src.name).write_bytes(src.read_bytes())
    assert artifact.json_bytes(run(read_inputs([moved/'calendar.json'],[moved/'a.json',moved/'b.json'])))==artifact.json_bytes(run(left))


@pytest.mark.parametrize('kind,fields_', [('calendar',CALENDAR_FIELDS),('pbp',PBP_FIELDS)])
def test_empty_file_still_requires_schema(tmp_path,kind,fields_):
    path=tmp_path/'empty.json'
    for absent in fields_:
        path.write_text(json.dumps({'columns':[f for f in fields_ if f!=absent],'rows':[]}))
        with pytest.raises(ValueError,match='Missing schema'):read_source(path,kind)
    path.write_text(json.dumps({'columns':list(fields_),'rows':[]}))
    assert read_source(path,kind)[0]==[]


def test_no_nonstandard_json_or_duplicate_fields(tmp_path):
    from nfl_sideline_etl.offline_metrics.inputs import load_json
    for data in ['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}']:
        with pytest.raises(ValueError):load_json(data)
    doc=json.loads((FIXTURE/'pbp.json').read_text());doc['columns'].remove('drive')
    path=tmp_path/'schema.json';path.write_text(json.dumps(doc))
    args=cli_args(tmp_path/'no-final');args[3]=str(path)
    with pytest.raises(SystemExit):main(args)
    assert not (tmp_path/'no-final').exists()


def test_manifest_raw_count_mismatch_rejected(source):
    altered=copy.deepcopy(source)
    altered[2][0]['raw_rows']-=2  # A filtered manifest must not pass as raw input metadata.
    with pytest.raises(ValueError,match='manifest raw count mismatch'):run(altered)


def test_distinct_season_and_phase_same_week_retained(source):
    row=copy.deepcopy(source[1][0])
    calendars=[dict(game_id=g,season=s,week=1,game_type=p,home_team='A',away_team='B')
               for g,s,p in [('reg26',2026,'REG'),('post26',2026,'WC'),('reg25',2025,'REG')]]
    games,_=calendar_index(calendars)
    plays=[{**row,'game_id':g['game_id'],'season':g['season'],'season_type':g['phase'],'week':1}
           for g in games.values()]
    unique,_,_=reconcile_raw(plays,games)
    assert len(unique)==3
    assert {(p['season'],p['phase']) for p in unique}=={(2026,'REG'),(2026,'POST'),(2025,'REG')}


def test_known_different_models_not_silently_pooled(source):
    m=json.loads((FIXTURE/'metadata.json').read_text())
    calendars,plays,inputs=copy.deepcopy(source)
    extra={**inputs[1],'sha256':'extra','source_revision_id':'sha256:extra','raw_rows':0}
    inputs.append(extra);m['pbp_sha256'].append('extra')
    evidence={'basis':'synthetic','reference':'test'}
    m['sources']={digest:{'source_model_version':{'value':model,'evidence':evidence}}
                  for digest,model in [(m['pbp_sha256'][0],'model-1'),('extra','model-2')]}
    with pytest.raises(ValueError,match='model versions differ'):run((calendars,plays,inputs),m)


@pytest.mark.parametrize('field,dtype', [('epa',pl.Binary),('play_id',pl.Boolean),('posteam',pl.Int64)])
def test_invalid_parquet_schema_even_when_empty(tmp_path,source,field,dtype):
    row={k:source[1][0][k] for k in PBP_FIELDS}
    frame=pl.DataFrame([row]).clear().with_columns(pl.lit(None,dtype=dtype).alias(field))
    path=tmp_path/'bad.parquet';frame.write_parquet(path)
    with pytest.raises(ValueError,match='Invalid Parquet schema type'):read_source(path,'pbp')


def test_corrupted_parquet_rejected_without_final_output(tmp_path):
    path=tmp_path/'broken.parquet';path.write_bytes(b'not parquet bytes')
    with pytest.raises(ValueError,match='Invalid local Parquet'):read_source(path,'pbp')
    args=cli_args(tmp_path/'no-final');args[3]=str(path)
    with pytest.raises(SystemExit):main(args)
    assert not (tmp_path/'no-final').exists()
