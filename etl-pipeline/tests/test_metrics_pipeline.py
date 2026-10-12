from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
import json
import uuid

import polars as pl
import pytest

import run_pipeline as pipeline
from nfl_sideline_etl import metrics_pipeline as stage
from nfl_sideline_etl.metrics_persistence.archive import Archive
from nfl_sideline_etl.metrics_persistence.plan import prepare
from nfl_sideline_etl.offline_metrics.artifact import json_bytes
from metrics_pipeline_support import fixtures, specification
from test_run_pipeline import FakeConnection, install_success_stages


def args(tmp_path, entry, mode='plan', *, allow=False):
    source = specification(tmp_path / 'inputs.json', {2026: entry})
    argv = ['--season', '2026', '--game-metrics', mode, '--metrics-inputs', str(source),
            '--metrics-output', str(tmp_path / 'attempts')]
    if allow:
        argv += ['--allow-missing-pbp']
    if mode == 'local':
        argv += ['--skip-acquire', '--data-dir', str(tmp_path / 'data'),
                 '--legacy-local-config', str(tmp_path / 'legacy.json'),
                 '--metrics-local-config', str(tmp_path / 'writer.json'),
                 '--metrics-archive', str(tmp_path / 'archive')]
    return pipeline.build_parser().parse_args(argv)


def config(tmp_path, user='domain', **overrides):
    instance = 'eeeeeeee-1111-4444-8888-123456789012'
    v = dict(host='127.0.0.1', port=55491, database='nfl_e5b2_eeeeeeee1111',
             user=user, password='test-only', instance_id=instance)
    v.update(overrides)
    p = tmp_path / ('legacy.json' if user == 'domain' else 'writer.json')
    p.write_bytes(json_bytes(v))
    return p


def local(tmp_path, monkeypatch, *, empty=False, missing=False, allow=False):
    entry = fixtures(tmp_path / 'data', empty=empty, missing=missing)
    config(tmp_path)
    config(tmp_path, 'writer')
    monkeypatch.setattr(stage, 'connect_legacy', lambda c: FakeConnection())
    monkeypatch.setattr(stage.connection, 'connect', lambda c: FakeConnection())
    monkeypatch.setattr(stage, '_identity_check', lambda c, v: tuple(v[k] for k in ('host','port','database','instance_id')))
    execution = stage.configure(args(tmp_path, entry, 'local', allow=allow), (2026,))
    return execution, entry


def events(attempt):
    return [json.loads(p.read_text()) for p in sorted(attempt.root.glob('*.json'))]


def test_default_has_no_new_effects(tmp_path, monkeypatch):
    for fn in ('_spec', 'connect_legacy'):
        monkeypatch.setattr(stage, fn, Mock(side_effect=AssertionError('new effect')))
    monkeypatch.setattr(stage.connection, 'connect', Mock(side_effect=AssertionError('SQL')))
    parsed = pipeline.build_parser().parse_args([])
    assert stage.configure(parsed, (2026,)) is None
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('extra', [
    ['--skip-acquire'], ['--data-dir', '/tmp/data'], ['--metrics-archive', '/tmp/archive'],
    ['--legacy-local-config', '/tmp/config'], ['--metrics-local-config', '/tmp/config']])
def test_plan_rejects_legacy_or_sql_arguments_before_writes(tmp_path, extra):
    parsed = args(tmp_path, fixtures(tmp_path / 'data'))
    for i in range(0, len(extra), 2):
        setattr(parsed, extra[i][2:].replace('-', '_'), True if len(extra) == 1 else Path(extra[i+1]))
    with pytest.raises(ValueError, match='offline only'):
        stage.configure(parsed, (2026,))
    assert not parsed.metrics_output.exists()


@pytest.mark.parametrize('field', ['skip_acquire', 'data_dir', 'legacy_local_config',
                                   'metrics_local_config', 'metrics_archive', 'metrics_inputs', 'metrics_output'])
def test_missing_required_local_arguments_refused_before_any_connection(tmp_path, monkeypatch, field):
    parsed = args(tmp_path, fixtures(tmp_path / 'data'), 'local')
    setattr(parsed, field, False if field == 'skip_acquire' else None)
    monkeypatch.setattr(stage, 'connect_legacy', Mock(side_effect=AssertionError('connection')))
    with pytest.raises(ValueError):
        stage.configure(parsed, (2026,))
    assert not (tmp_path / 'attempts').exists()


def test_off_rejects_metrics_arguments(tmp_path):
    parsed = pipeline.build_parser().parse_args(['--metrics-output', str(tmp_path / 'out')])
    with pytest.raises(ValueError):
        stage.configure(parsed, (2026,))
    assert not (tmp_path / 'out').exists()


def test_plan_no_sql_env_archive_acquisition_or_ingestion(tmp_path, monkeypatch):
    entry = fixtures(tmp_path / 'data')
    monkeypatch.setenv('PGHOST', 'remote.invalid')  # never consumed in plan
    for obj, name in [(stage.connection,'connect'), (stage,'connect_legacy'),
                      (pipeline,'start_run'), (pipeline,'run_pipeline'),
                      (pipeline.load_metrics,'_read_db_config'), (pipeline.run_local,'acquire_season'),
                      (stage.writer,'persist')]:
        monkeypatch.setattr(obj, name, Mock(side_effect=AssertionError(name)))
    parsed = args(tmp_path, entry)
    execution = stage.configure(parsed, (2026,))
    stage.plan(execution, (2026,))
    report = json.loads(next(execution.output.rglob('*-PLANNED.json')).read_text())
    assert report['global_status'] == 'NOT_STARTED' and report['ingestion_run'] is None
    assert report['stage_result'] == 'PLANNED' and report['database_connected'] is False
    assert len(report['coverages']) == 4
    assert not list(execution.output.rglob('ARCHIVE.json'))


def test_multigame_exact_sums_denominators_and_empty_proof(tmp_path):
    execution = stage.configure(args(tmp_path, fixtures(tmp_path / 'data')), (2026,))
    attempt = execution.attempt(2026)
    attempt.freeze(); attempt.run()
    p = attempt.plan
    r = p.result['reconciliation.json']
    assert (r['pbp_raw_n'], r['pbp_unique_n'], r['duplicate_rows_ignored'], r['eligible_content_n']) == (6,5,1,5)
    stats = p.result['statistics.json']
    s = next(s for s in stats if s['game_id'] == 'synthetic-1' and s['team']=='A' and s['role']=='off' and s['foundation']=='general')
    assert (s['eligible_n'],s['epa_n'],s['success_n'],s['epa_missing_n'],s['epa_sum']) == (3,2,1,1,'-0.5')
    second = next(s for s in stats if s['game_id']=='synthetic-3' and s['team']=='A' and s['role']=='off' and s['foundation']=='general')
    assert (second['eligible_n'],second['epa_n'],second['epa_sum']) == (1,1,'0.5')
    audits = {a['game_id']:a for a in p.result['game-audit.json']}
    assert audits['synthetic-5']['scope']=='NO_SOURCE_OBSERVATION'
    assert not any(s['game_id']=='synthetic-5' for s in stats)
    assert audits['synthetic-6']['completeness']=='COMPLETE'
    assert all(s['eligible_n']==0 and s['epa_sum'] is None for s in stats if s['game_id']=='synthetic-6')
    assert len({p.result['manifest.json']['calculation_id']}) == 1


@pytest.mark.parametrize('missing,empty,expected', [(True,False,'UNAVAILABLE_MISSING_PBP'),(False,True,'PLANNED')])
def test_missing_distinct_from_existing_empty(tmp_path, missing, empty, expected):
    entry = fixtures(tmp_path / 'data', missing=missing, empty=empty, metadata=False)
    execution = stage.configure(args(tmp_path, entry, allow=True), (2026,))
    attempt = execution.attempt(2026); attempt.freeze(); attempt.run()
    assert attempt.stage_result == expected
    if missing:
        assert attempt.plan is None and not list(attempt.root.rglob('pbp*.parquet'))
    else:
        assert attempt.details['pbp_state']=='EMPTY_PRESENT'
        assert attempt.plan.result['statistics.json']==[]
        assert all(a['completeness']=='UNKNOWN' for a in attempt.plan.result['game-audit.json'])


@pytest.mark.parametrize('empty', [False,True])
def test_missing_or_empty_requires_allow_flag(tmp_path, empty):
    entry = fixtures(tmp_path / 'data', missing=not empty, empty=empty)
    execution = stage.configure(args(tmp_path, entry), (2026,))
    attempt = execution.attempt(2026)
    with pytest.raises(ValueError, match='required|requires'):
        attempt.freeze()
    assert events(attempt)[-1]['stage']=='FAILED'


@pytest.mark.parametrize('corruption', ['bytes','schema','conflict','metadata'])
def test_corruption_stays_fatal_with_allow(tmp_path, corruption):
    entry = fixtures(tmp_path / 'data')
    path = Path(entry['pbp'][0])
    if corruption=='bytes': path.write_bytes(b'corrupt')
    if corruption=='schema': pl.DataFrame({'x':[1]}).write_parquet(path)
    if corruption=='conflict':
        frame=pl.read_parquet(entry['pbp'][1]).with_columns(pl.when(pl.col('game_id')=='synthetic-1').then(pl.lit(99.0)).otherwise(pl.col('epa')).alias('epa'))
        frame.write_parquet(entry['pbp'][1])
        entry['metadata']=None
    if corruption=='metadata': Path(entry['metadata']).write_bytes(b'{bad')
    execution = stage.configure(args(tmp_path, entry, allow=True), (2026,))
    attempt = execution.attempt(2026)
    with pytest.raises((ValueError,pl.exceptions.PolarsError)):
        attempt.freeze(); attempt.run()
    assert not (tmp_path/'archive').exists()


@pytest.mark.parametrize('where', ['original','frozen','legacy_frozen','metadata'])
def test_swapped_source_fails_before_writer(tmp_path, monkeypatch, where):
    execution, _ = local(tmp_path,monkeypatch)
    attempt=execution.attempt(2026); attempt.freeze()
    record=next(r for r in attempt.sources if r['kind']==('metadata' if where=='metadata' else 'pbp'))
    Path(record['original' if where=='metadata' else where]).write_bytes(b'changed')
    monkeypatch.setattr(stage.writer,'persist',Mock(side_effect=AssertionError('writer must not run')))
    with pytest.raises(ValueError,match='changed'):
        attempt.run()


def test_idempotence_and_source_correction_preserve_prior_attempts(tmp_path):
    entry=fixtures(tmp_path/'data',metadata=False)
    execution=stage.configure(args(tmp_path,entry),(2026,))
    first=execution.attempt(2026); first.freeze();first.run()
    second=execution.attempt(2026);second.freeze();second.run()
    assert first.attempt_id!=second.attempt_id
    assert first.plan.artifact_id==second.plan.artifact_id
    before={p.name:p.read_bytes() for p in (first.root/'artifact').iterdir()}
    frame=pl.read_parquet(entry['pbp'][0]).with_columns(pl.when(pl.col('play_id')==2).then(pl.lit(-1.25)).otherwise(pl.col('epa')).alias('epa'))
    frame.write_parquet(entry['pbp'][0])
    third=execution.attempt(2026);third.freeze();third.run()
    assert third.plan.artifact_id!=first.plan.artifact_id
    assert before=={p.name:p.read_bytes() for p in (first.root/'artifact').iterdir()}
    assert first.plan.result['manifest.json']['calculation_id']!=third.plan.result['manifest.json']['calculation_id']


def test_existing_artifact_must_pass_prepare(tmp_path):
    entry=fixtures(tmp_path/'data');execution=stage.configure(args(tmp_path,entry),(2026,))
    attempt=execution.attempt(2026);attempt.freeze();attempt.run()
    (attempt.root/'artifact/statistics.json').write_bytes(b'[]')
    with pytest.raises(ValueError,match='hash mismatch'):
        prepare(attempt.root/'artifact',attempt.paths['calendar'],attempt.paths['pbp'],tmp_path/'cas')


@pytest.mark.parametrize('field,value', [('host','example.com'),('port',0),('database','postgres')])
def test_remote_or_invalid_configuration_rejected_without_sql(tmp_path,monkeypatch,field,value):
    entry=fixtures(tmp_path/'data');config(tmp_path);config(tmp_path,'writer',**{field:value})
    monkeypatch.setattr(stage,'connect_legacy',Mock(side_effect=AssertionError('connect')))
    with pytest.raises(ValueError):stage.configure(args(tmp_path,entry,'local'),(2026,))
    assert not (tmp_path/'attempts').exists()


@pytest.mark.parametrize('field,value', [('port',55492),('host','::1'),('instance_id','aaaaaaaa-1111-4444-8888-123456789012')])
def test_different_instances_rejected_before_connections(tmp_path,monkeypatch,field,value):
    entry=fixtures(tmp_path/'data');config(tmp_path)
    overrides={field:value}
    if field=='instance_id':overrides['database']='nfl_e5b2_aaaaaaaa1111'
    config(tmp_path,'writer',**overrides)
    monkeypatch.setattr(stage,'connect_legacy',Mock(side_effect=AssertionError('connect')))
    with pytest.raises(ValueError,match='same local instance'):
        stage.configure(args(tmp_path,entry,'local'),(2026,))
    assert not (tmp_path/'attempts').exists()


def test_incomplete_partition_list_rejected_before_connections(tmp_path):
    entry=fixtures(tmp_path/'data');entry['pbp']=entry['pbp'][:1]
    with pytest.raises(ValueError,match='inventory'):
        stage.configure(args(tmp_path,entry,'local'),(2026,))
    assert not (tmp_path/'attempts').exists()


@pytest.mark.parametrize('boundary', ['CALCULATING','VALIDATED','PERSISTING','ARCHIVED','after_sources','before_commit','PRIVATE_COMMITTED','FINISHING_GLOBAL','finish_success'])
def test_failure_boundaries_fail_fast_preserve_original_and_status(tmp_path,monkeypatch,boundary):
    execution,_=local(tmp_path,monkeypatch)
    order=[];install_success_stages(monkeypatch,order)
    attempt=execution.attempt(2026)
    original=RuntimeError('original password=do-not-record\nsecond line')
    def checkpoint(s):
        if s==boundary:raise original
    attempt._checkpoint=checkpoint
    monkeypatch.setattr(execution,'attempt',lambda season:attempt if season==2026 else pytest.fail('next season'))
    def persist(plan,root,conf,*,_checkpoint):
        ar=Archive(root)
        for h,(b,o) in plan.source_bytes.items():ar.put(b,h,o)
        for n,b in plan.artifact_bytes.items():ar.put(b,plan.file_hashes[n],{'filename':n})
        for point in ('after_archive','after_sources','before_commit'):_checkpoint(point)
        return {'inserted':1,'reused':0,'conflicts':0}
    monkeypatch.setattr(stage.writer,'persist',persist)
    if boundary=='finish_success':
        monkeypatch.setattr(pipeline,'finish_run_succeeded',lambda *a,**kw:(_ for _ in ()).throw(original))
    with pytest.raises(RuntimeError) as caught:
        pipeline.run_pipeline((2026,2027),data_dir=tmp_path/'data',allow_missing_pbp=False,skip_acquire=True,metrics_execution=execution)
    assert caught.value is original
    assert not any(e[0]=='succeeded' for e in order)
    assert [e[0] for e in order].count('start')==1
    assert order[-1][0]=='failed'
    last=events(attempt)[-1]
    assert last['global_status']=='FAILED' and 'do-not-record' not in last['diagnostic']
    assert last['stage_result']==('PERSISTED' if boundary in ('PRIVATE_COMMITTED','FINISHING_GLOBAL','finish_success') else 'FAILED')
    assert any(e['stage']=='ARCHIVED' for e in events(attempt))==(boundary in ('ARCHIVED','after_sources','before_commit','PRIVATE_COMMITTED','FINISHING_GLOBAL','finish_success'))


def test_integrated_order_and_legacy_counts(tmp_path,monkeypatch):
    execution,_=local(tmp_path,monkeypatch);order=[];install_success_stages(monkeypatch,order)
    attempt=execution.attempt(2026)
    monkeypatch.setattr(execution,'attempt',lambda s:attempt)
    monkeypatch.setattr(stage.writer,'persist',lambda *a,**kw:order.append(('private',2026)) or {'inserted':10,'reused':0})
    result=pipeline.run_pipeline((2026,),data_dir=tmp_path/'data',allow_missing_pbp=False,skip_acquire=True,metrics_execution=execution)[0]
    assert [e[0] for e in order]==['start','seed','games','metrics','private','succeeded']
    assert (result.rows_games,result.rows_pbp,result.rows_metrics)==(8,120,12)
    assert result.metrics_attempt==attempt.attempt_id
    assert events(attempt)[-1]['stage_result']=='PERSISTED'


def test_failed_status_and_journal_do_not_hide_original(tmp_path,monkeypatch):
    execution,_=local(tmp_path,monkeypatch);order=[];install_success_stages(monkeypatch,order)
    attempt=execution.attempt(2026);monkeypatch.setattr(execution,'attempt',lambda s:attempt)
    original=ValueError('private original')
    monkeypatch.setattr(stage.writer,'persist',Mock(side_effect=original))
    monkeypatch.setattr(pipeline,'finish_run_failed',Mock(side_effect=RuntimeError('status failed')))
    real=attempt.event
    def event(s,**kw):
        if s=='FAILED':raise OSError('journal failed')
        real(s,**kw)
    monkeypatch.setattr(attempt,'event',event)
    with pytest.raises(ValueError) as caught:
        pipeline.process_season(2026,data_dir=tmp_path/'data',allow_missing_pbp=False,skip_acquire=True,metrics_execution=execution)
    assert caught.value is original
    assert attempt.global_status=='UNKNOWN'


class GuardCursor:
    def __init__(self, *, privileged=False, endpoint=('nfl_e5b2_eeeeeeee1111','127.0.0.1',55491), marker=True, writer=False, permission=True):
        self.privileged,self.endpoint,self.marker,self.writer,self.permission=privileged,endpoint,marker,writer,permission
        self.query=''
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def execute(self,q,p=None):self.query=q
    def fetchone(self):
        if 'inet_server_port' in self.query:return self.endpoint
        if 'exists(select' in self.query:return (self.privileged,)
        if 'metric_persistence_writer' in self.query:return (self.writer,)
        if 'pg_get_serial_sequence' in self.query:return ('public.ingestion_runs_id_seq',)
        return (self.permission,)
    def fetchall(self):
        return [('eeeeeeee-1111-4444-8888-123456789012','metrics-persistence-e5b2-disposable')] if self.marker else []


@pytest.mark.parametrize('changes', [{'privileged':True},{'endpoint':('different','127.0.0.1',55491)},
                                    {'marker':False},{'writer':True},{'permission':False}])
def test_guard_refuses_admin_wrong_actual_marker_writer_or_domain_privileges(tmp_path,monkeypatch,changes):
    import psycopg2
    cfg=stage.connection.configuration(config(tmp_path))
    conn=FakeConnection();cursor=GuardCursor(**changes);conn.cursor=lambda:cursor
    monkeypatch.setattr(psycopg2,'connect',lambda **kw:conn)
    with pytest.raises(ValueError):stage.connect_legacy(cfg)
    assert conn.closed


def test_pg_ambient_or_direct_remote_config_refused_before_connect(tmp_path,monkeypatch):
    import psycopg2
    cfg=stage.connection.configuration(config(tmp_path))
    monkeypatch.setattr(psycopg2,'connect',Mock(side_effect=AssertionError('SQL connect')))
    with pytest.raises(ValueError,match='loopback'):stage.connect_legacy({**cfg,'host':'remote.invalid'})
    monkeypatch.setenv('PGSERVICE','remote')
    with pytest.raises(ValueError,match='PG'):stage.connect_legacy(cfg)


def test_preflight_connection_failure_closes_domain_and_never_creates_output(tmp_path,monkeypatch):
    entry=fixtures(tmp_path/'data');config(tmp_path);config(tmp_path,'writer')
    conn=FakeConnection();monkeypatch.setattr(stage,'connect_legacy',lambda c:conn)
    monkeypatch.setattr(stage.connection,'connect',Mock(side_effect=RuntimeError('writer unavailable')))
    with pytest.raises(RuntimeError):stage.configure(args(tmp_path,entry,'local'),(2026,))
    assert conn.closed and not (tmp_path/'attempts').exists()


def test_partial_missing_set_stays_unavailable_and_rejects_conflicts(tmp_path):
    entry=fixtures(tmp_path/'data',metadata=False)
    entry['pbp'].append(str(tmp_path/'data/raw/pbp/season=2026/absent.parquet'))
    execution=stage.configure(args(tmp_path,entry,allow=True),(2026,))
    a=execution.attempt(2026);a.freeze();a.run()
    assert a.stage_result=='UNAVAILABLE_MISSING_PBP' and a.plan is None
    path=Path(entry['pbp'][1]);pl.read_parquet(path).with_columns(pl.lit(5.0).alias('epa')).write_parquet(path)
    b=execution.attempt(2026)
    with pytest.raises(ValueError,match='Conflict'):b.freeze()
    assert events(b)[-1]['stage']=='FAILED'


def test_empty_existing_complete_evidence_is_preserved(tmp_path):
    entry=fixtures(tmp_path/'data',empty=True)
    execution=stage.configure(args(tmp_path,entry,allow=True),(2026,))
    a=execution.attempt(2026);a.freeze();a.run()
    assert len(a.plan.result['statistics.json'])==12
    assert all(s['game_id']=='synthetic-6' and s['eligible_n']==0 and s['epa_sum'] is None for s in a.plan.result['statistics.json'])
    assert a.plan.result['game-audit.json'][0]['scope']=='NO_SOURCE_OBSERVATION'


def test_receipt_recovery_verifies_existing_bytes_without_moving_observation(tmp_path):
    ar=Archive(tmp_path/'archive')
    from nfl_sideline_etl.metrics_persistence.archive import digest
    data=b'unchanging';sha=digest(data);first=ar.put(data,sha,{'attempt':'first'})
    again=ar.put(data,sha,{'attempt':'second'})
    assert again==first
    ar.path(ar.locator(sha)).write_bytes(b'corrupt')
    with pytest.raises(ValueError):ar.put(data,sha,{'attempt':'third'})


def test_swap_after_archive_prevents_private_sql(tmp_path,monkeypatch):
    execution,entry=local(tmp_path,monkeypatch)
    a=execution.attempt(2026);a.freeze()
    def persist(p,root,c,*,_checkpoint):
        ar=Archive(root)
        for h,(b,o) in p.source_bytes.items():ar.put(b,h,o)
        for n,b in p.artifact_bytes.items():ar.put(b,p.file_hashes[n],{'filename':n})
        Path(entry['pbp'][0]).write_bytes(b'swapped')
        _checkpoint('after_archive')
        pytest.fail('private SQL must not execute')
    monkeypatch.setattr(stage.writer,'persist',persist)
    with pytest.raises(ValueError,match='changed'):a.run()
    assert a.last_stage=='ARCHIVED' and a.stage_result!='PERSISTED'


def test_pipeline_refuses_plan_execution_and_acquisition_before_attempt(tmp_path,monkeypatch):
    execution=stage.configure(args(tmp_path,fixtures(tmp_path/'data')),(2026,))
    monkeypatch.setattr(execution,'attempt',Mock(side_effect=AssertionError('attempt')))
    with pytest.raises(ValueError):
        pipeline.process_season(2026,data_dir=tmp_path/'data',allow_missing_pbp=False,skip_acquire=True,metrics_execution=execution)
    assert not list(execution.output.iterdir())
