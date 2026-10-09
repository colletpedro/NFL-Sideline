"""Real SQL, actual writer login and actual archive; no mocked database claims."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
import subprocess
import sys

import psycopg2
from psycopg2 import sql
import pytest

from nfl_sideline_etl.offline_metrics.artifact import calculate, identity, write_artifact
from nfl_sideline_etl.offline_metrics.inputs import read_inputs
from nfl_sideline_etl.metrics_persistence.archive import Archive
from nfl_sideline_etl.metrics_persistence.connection import connect
from nfl_sideline_etl.metrics_persistence.plan import prepare
from nfl_sideline_etl.metrics_persistence.writer import persist, immutable_insert, TABLES

ROOT = Path(__file__).resolve().parents[5]
FIXTURE = ROOT / 'etl-pipeline/tests/fixtures/offline_metrics'
ARTIFACT = ROOT / 'docs/plans/metrics/e5b-1/synthetic-result'


def original(tmp_path):
    return prepare(ARTIFACT,[FIXTURE/'calendar.json'],[FIXTURE/'pbp.json'],tmp_path/'archive')


def make_plan(tmp_path, *, metadata=None, pbp=None, calendars=None, name='new'):
    paths = pbp or [FIXTURE/'pbp.json']
    calendars = calendars or [FIXTURE/'calendar.json']
    inputs = read_inputs(calendars, paths)
    result = calculate(*inputs, metadata, seasons=(2026,))
    output = tmp_path/name
    write_artifact(output,result)
    return prepare(output,calendars,paths,tmp_path/'archive')


def query(config, statement, args=()):
    conn = connect(config)
    try:
        with conn.cursor() as cursor:
            cursor.execute(statement,args)
            return cursor.fetchall()
    finally:
        conn.close()


def sizes(config):
    return {table:query(config,f'select count(*) from metrics_private.{table}')[0][0] for table in TABLES}


def test_migrations_clean_schema_access_and_inheritance(db):
    config, admin = db
    assert len(query(config,"select relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                       "where n.nspname='metrics_private' and relkind='r' and relrowsecurity and relforcerowsecurity")) == len(TABLES)
    flags=query(config,'select rolsuper,rolbypassrls,rolcreatedb,rolcreaterole from pg_roles where rolname=current_user')[0]
    assert flags == (False,False,False,False)
    for table in TABLES:
        name='metrics_private.'+table
        assert query(config,'select has_table_privilege(current_user,%s,\'SELECT\'), '
                     'has_table_privilege(current_user,%s,\'INSERT\'), '
                     'has_table_privilege(current_user,%s,\'UPDATE,DELETE,TRUNCATE\')',(name,name,name))[0] == (True,True,False)
        for role in ('anon','authenticated','service_role'):
            assert query(config,'select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER\')',(role,name))[0] == (False,)
    assert query(config,"select has_table_privilege(current_user,'public.games','SELECT,INSERT,UPDATE,DELETE')")[0] == (False,)
    with psycopg2.connect(**admin) as conn:
        with conn.cursor() as cur:
            cur.execute("drop role if exists e5b2_public_probe; create role e5b2_public_probe nologin inherit; grant anon, authenticated to e5b2_public_probe")
            for role in ('anon','authenticated','service_role','e5b2_public_probe'):
                cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
                cur.execute("select has_schema_privilege(current_user,'metrics_private','USAGE')")
                assert cur.fetchone() == (False,)
                cur.execute('reset role')
    # Try actual access as public/inherited role, not only catalog booleans.
    for role in ('anon','authenticated','e5b2_public_probe'):
        with psycopg2.connect(**admin) as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
                with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                    cur.execute('select * from metrics_private.metric_archive_blob')
    for role in ('anon','authenticated','service_role','e5b2_public_probe'):
        for type_name in ('sha256_id','byte_hash',*TABLES):
            assert query(config, "select has_type_privilege(%s,%s,'USAGE')",
                         (role,'metrics_private.'+type_name))[0] == (False,)
    assert query(config, "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace, "
                        "lateral aclexplode(c.relacl) a where n.nspname='metrics_private' and a.grantee=0")[0] == (0,)
    policies = query(config,"select roles,cmd from pg_policies where schemaname='metrics_private'")
    assert len(policies) == len(TABLES)*2
    assert all(roles==['metric_persistence_writer'] and cmd in ('SELECT','INSERT') for roles,cmd in policies)


def test_exact_stats_states_and_original_artifact_round_trip(db,tmp_path):
    config,_=db
    plan=original(tmp_path)
    report=persist(plan,tmp_path/'archive',config)
    assert report['inserted']>0 and report['reused']==0
    rows=query(config,'select record_json,eligible_n,epa_n,success_n,epa_missing_n,epa_nonfinite_n,epa_sum '
                      'from metrics_private.team_game_metric_sums')
    assert len(rows)==60
    assert sorted((r[0] for r in rows),key=lambda s:(s['coverage_revision_id'],s['team'],s['role'],s['foundation'])) == sorted(
        plan.result['statistics.json'],key=lambda s:(s['coverage_revision_id'],s['team'],s['role'],s['foundation']))
    for record,*values in rows:
        assert values == [record[k] for k in ('eligible_n','epa_n','success_n','epa_missing_n','epa_nonfinite_n')] + [
            None if record['epa_sum'] is None else Decimal(record['epa_sum'])]
    assert any(r[-1] is not None and r[-1]<0 for r in rows)
    assert any(r[-1]==0 and r[2]>0 for r in rows)
    assert any(r[-1] is None and r[2]==0 for r in rows)
    assert any(r[5]>0 for r in rows)
    states=query(config,'select game_id,completeness,scope,statistics_status,eligible_content_n '
                        'from metrics_private.game_metric_coverage_revision order by game_id')
    assert states[-2]==('synthetic-5','UNKNOWN','NO_SOURCE_OBSERVATION','SOURCE_UNKNOWN',None)
    assert states[-1]==('synthetic-6','COMPLETE','FULL_GAME_CONTENT','COMPLETE',0)
    assert states[0][1:4]==('UNKNOWN','AUDITABLE_SUBSET','PARTIAL')
    assert query(config,'select count(*) from metrics_private.metric_calculation_coverage')[0]==(6,)
    archived=Archive(tmp_path/'archive')
    files=query(config,'select filename,sha256 from metrics_private.metric_artifact_file')
    assert {name:archived.read(sha) for name,sha in files}==plan.artifact_bytes


def test_idempotency_preserves_first_receipts_and_sql_instants(db,tmp_path):
    config,_=db
    plan=original(tmp_path)
    persist(plan,tmp_path/'archive',config)
    before=sizes(config)
    first=query(config,'select receipt_id,observed_at,persisted_at from metrics_private.metric_archive_receipt order by receipt_id')
    calc_time=query(config,'select persisted_at from metrics_private.metric_calculation')
    report=persist(plan,tmp_path/'archive',config)
    assert report=={'inserted':0,'reused':sum(before.values()),'conflicts':0}
    assert sizes(config)==before
    assert query(config,'select receipt_id,observed_at,persisted_at from metrics_private.metric_archive_receipt order by receipt_id')==first
    assert query(config,'select persisted_at from metrics_private.metric_calculation')==calc_time
    assert all(observed<=persisted for _,observed,persisted in first)


def test_correction_new_revision_preserves_old(db,tmp_path):
    config,_=db
    old=original(tmp_path)
    persist(old,tmp_path/'archive',config)
    previous=query(config,'select coverage_revision_id,record_json from metrics_private.team_game_metric_sums')
    document=json.loads((FIXTURE/'pbp.json').read_text())
    document['rows'][0]['epa']='-123.12345678901234567890123456789012345'
    path=tmp_path/'corrected.json';path.write_text(json.dumps(document))
    # Corrected bytes require newly bound metadata; no historical proof added.
    corrected=make_plan(tmp_path,pbp=[path],name='corrected-result')
    persist(corrected,tmp_path/'archive',config)
    assert sizes(config)['metric_source_revision']==3
    assert sizes(config)['metric_calculation']==2
    assert sizes(config)['game_metric_coverage_revision']==12
    now=query(config,'select coverage_revision_id,record_json from metrics_private.team_game_metric_sums')
    assert all(row in now for row in previous)
    assert old.result['manifest.json']['calculation_id']!=corrected.result['manifest.json']['calculation_id']


def test_model_evidence_changes_calculation_not_coverage(db,tmp_path):
    config,_=db
    old=original(tmp_path)
    persist(old,tmp_path/'archive',config)
    meta=json.loads((FIXTURE/'metadata.json').read_text())
    sha=meta['pbp_sha256'][0]
    meta['sources']={sha:{'source_model_version':{'value':'synthetic-model-2',
        'evidence':{'basis':'SYNTHETIC_DECLARATION','reference':'v2-proof'}}}}
    revised=make_plan(tmp_path,metadata=meta)
    assert old.result['game-audit.json']==revised.result['game-audit.json']
    persist(revised,tmp_path/'archive',config)
    assert sizes(config)['metric_source_revision']==2
    assert sizes(config)['game_metric_coverage_revision']==6
    assert sizes(config)['team_game_metric_sums']==60
    assert sizes(config)['metric_calculation']==2
    manifests=query(config,'select manifest_json from metrics_private.metric_calculation')
    assert old.result['manifest.json'] in [m[0] for m in manifests]
    assert revised.result['manifest.json'] in [m[0] for m in manifests]


def test_game_evidence_revision_preserves_history_and_partial(db,tmp_path):
    config,_=db
    old=original(tmp_path);persist(old,tmp_path/'archive',config)
    meta=json.loads((FIXTURE/'metadata.json').read_text())
    meta['games']['synthetic-1']={'completeness':'PARTIAL','expected_unique_rows':30,
        'evidence':{'basis':'SYNTHETIC_PARTITION','reference':'new-proof'},
        'available_at':{'value':'2026-10-09T10:00:00-03:00','evidence':{'basis':'DECLARED','reference':'not-authenticated'}}}
    revised=make_plan(tmp_path,metadata=meta)
    persist(revised,tmp_path/'archive',config)
    states=query(config,"select completeness,scope,statistics_status,audit_json from metrics_private.game_metric_coverage_revision where game_id='synthetic-1'")
    assert {r[0] for r in states}=={'UNKNOWN','PARTIAL'}
    assert all(r[1:3]==('AUDITABLE_SUBSET','PARTIAL') for r in states)
    assert any(r[3]['provenance']['available_at']['value']=='2026-10-09T13:00:00Z' for r in states if r[0]=='PARTIAL')


@pytest.mark.parametrize('stage',['after_archive','after_sources','before_commit'])
def test_rollback_and_orphan_archive_recovery(db,tmp_path,stage):
    config,_=db
    plan=original(tmp_path)
    before=sizes(config)
    def fail(checkpoint):
        if checkpoint==stage: raise RuntimeError('intentional rollback')
    with pytest.raises(RuntimeError,match='intentional'):
        persist(plan,tmp_path/'archive',config,_checkpoint=fail)
    assert sizes(config)==before
    archive=Archive(tmp_path/'archive')
    receipts={p.name:p.read_bytes() for p in (archive.root/'receipts').iterdir()}
    assert len(receipts)==8
    assert persist(plan,tmp_path/'archive',config)['inserted']>0
    assert receipts=={p.name:p.read_bytes() for p in (archive.root/'receipts').iterdir()}


def test_conflicting_identity_rejects_and_rolls_back(db,tmp_path):
    config,admin=db
    plan=original(tmp_path);persist(plan,tmp_path/'archive',config)
    first=plan.result['game-audit.json'][0]['coverage_revision_id']
    # Simulate preexisting incompatible immutable content as administrator;
    # writer never has UPDATE. Must reject even though the incoming artifact is valid.
    with psycopg2.connect(**admin) as conn:
        with conn.cursor() as cur:
            cur.execute("update metrics_private.game_metric_coverage_revision set audit_json=audit_json || '{\"tampered\":true}'::jsonb where coverage_revision_id=%s",(first,))
    before=sizes(config)
    with pytest.raises(ValueError,match='Immutable identity conflict'):
        persist(plan,tmp_path/'other-archive',config)
    assert sizes(config)==before
    assert query(config,'select count(*) from metrics_private.metric_archive_receipt')[0]==(8,)


def test_partitions_and_repeated_bytes_associations(db,tmp_path):
    config,_=db
    document=json.loads((FIXTURE/'pbp.json').read_text())
    paths=[]
    for name,rows in [('p1',document['rows'][:12]),('p2',document['rows'][8:])]:
        path=tmp_path/(name+'.json');path.write_text(json.dumps({**document,'rows':rows}));paths.append(path)
    plan=make_plan(tmp_path,pbp=paths)
    persist(plan,tmp_path/'archive',config)
    assert sizes(config)['metric_source_revision']==3
    members=query(config,"select ordinal,source_id,raw_rows from metrics_private.metric_source_member where kind='pbp' order by ordinal")
    assert len(members)==2 and {r[1] for r in members}=={'sha256:'+d['sha256'] for d in plan.sets['pbp']}
    repeated=make_plan(tmp_path,pbp=paths+[paths[0]],name='repeated')
    persist(repeated,tmp_path/'archive',config)
    assert sizes(config)['metric_source_revision']==3
    assert sizes(config)['metric_source_member']==6 # calendar reused + 2 + 3 PBP members
    assert repeated.result['reconciliation.json']['pbp_unique_n']==26


def test_two_concurrent_identical_persistences(db,tmp_path):
    config,_=db
    plan=original(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reports=list(pool.map(lambda _:persist(plan,tmp_path/'archive',config),range(2)))
    assert sorted(r['inserted'] for r in reports)[0]==0
    assert sizes(config)['team_game_metric_sums']==60
    assert sizes(config)['metric_calculation']==1
    assert sizes(config)['metric_archive_receipt']==8


def test_numeric_exact_beyond_decimal_context(db,tmp_path):
    config,_=db
    doc=json.loads((FIXTURE/'pbp.json').read_text())
    values=['1'+'0'*60,'0.000000000000000000000000000000000000000123456789012345678901','-'+('1'+'0'*60)]
    rows=[{**doc['rows'][0],'play_id':i+100,'epa':v} for i,v in enumerate(values)]
    path=tmp_path/'precise.json';path.write_text(json.dumps({**doc,'rows':rows}))
    plan=make_plan(tmp_path,pbp=[path])
    with localcontext() as ctx:
        ctx.prec=2
        persist(plan,tmp_path/'archive',config)
    value=query(config,"select epa_sum from metrics_private.team_game_metric_sums where team='A' and role='off' and foundation='general'")[0][0]
    assert value==Decimal(values[1])


@pytest.mark.parametrize('changes,expected',[
    ({'eligible_n':-1},psycopg2.errors.CheckViolation),
    ({'success_n':50},psycopg2.errors.CheckViolation),
    ({'epa_missing_n':90},psycopg2.errors.CheckViolation),
    ({'epa_n':0,'success_n':0,'eligible_n':4,'epa_missing_n':1,'epa_nonfinite_n':3,'epa_sum':Decimal('0')},psycopg2.errors.CheckViolation),
    ({'epa_sum':None},psycopg2.errors.CheckViolation),
    ({'epa_sum':Decimal('NaN')},psycopg2.errors.CheckViolation),
    ({'epa_sum':Decimal('Infinity')},psycopg2.errors.CheckViolation),
    ({'epa_sum':Decimal('-Infinity')},psycopg2.errors.CheckViolation),
    ({'role':'bad'},psycopg2.errors.CheckViolation),
    ({'foundation':'bad'},psycopg2.errors.CheckViolation),
    ({'scope':'bad'},psycopg2.errors.CheckViolation),
    ({'statistics_status':'bad'},psycopg2.errors.CheckViolation),
    ({'coverage_revision_id':'sha256:'+'a'*64},psycopg2.errors.ForeignKeyViolation),
    ({'team':'absent'},psycopg2.errors.ForeignKeyViolation),
    ({'scope':'FULL_GAME_CONTENT','statistics_status':'COMPLETE','completeness':'COMPLETE'},psycopg2.errors.ForeignKeyViolation),
])
def test_sql_constraints_and_fks_as_writer(db,tmp_path,changes,expected):
    config,_=db
    plan=original(tmp_path);persist(plan,tmp_path/'archive',config)
    record=query(config,"select row_to_json(s)::jsonb from metrics_private.team_game_metric_sums s where epa_n>0 limit 1")[0][0]
    record['epa_sum']=None if record['epa_sum'] is None else Decimal(str(record['epa_sum']))
    record['population_version']='sql-constraint-probe'
    record.update(changes)
    conn=connect(config)
    try:
        with conn.cursor() as cur:
            with pytest.raises(expected):
                immutable_insert(cur,'team_game_metric_sums',('coverage_revision_id','team','role','foundation','population_version','definition_version'),record,{'inserted':0,'reused':0})
    finally:
        conn.close()


@pytest.mark.parametrize('missing',['game','team'])
def test_missing_domain_entities_fail_no_silent_seed(db,tmp_path,missing):
    config,_=db
    calendar=json.loads((FIXTURE/'calendar.json').read_text())
    if missing=='game': calendar['rows'][4]['game_id']='not-in-domain'
    else: calendar['rows'][4]['home_team']='C'
    path=tmp_path/'calendar.json';path.write_text(json.dumps(calendar))
    plan=make_plan(tmp_path,calendars=[path])
    with pytest.raises(psycopg2.errors.ForeignKeyViolation):persist(plan,tmp_path/'archive',config)
    assert all(n==0 for n in sizes(config).values())


def test_wrong_instance_privileged_role_and_ambient_libpq_refused(db,monkeypatch):
    config,_=db
    wrong={**config,'instance_id':'00000000-0000-0000-0000-000000000001'}
    with pytest.raises(ValueError,match='Unidentified'):connect(wrong)
    monkeypatch.setenv('PGSERVICE','remote-default')
    with pytest.raises(ValueError,match='Ambient'):connect(config)


def test_actual_cli_first_load_reexecution_and_sanitized_database_error(instance,db,tmp_path):
    root,config,_=instance
    from nfl_sideline_etl.metrics_persistence.__main__ import main
    args=['--persist','--artifact',str(ARTIFACT),'--calendar',str(FIXTURE/'calendar.json'),
          '--pbp',str(FIXTURE/'pbp.json'),'--archive',str(tmp_path/'archive'),'--local-config',str(root/'writer.json')]
    result=subprocess.run([sys.executable,'-B','-m','nfl_sideline_etl.metrics_persistence',*args],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)['inserted']>0
    result=subprocess.run([sys.executable,'-B','-m','nfl_sideline_etl.metrics_persistence',*args],capture_output=True,text=True)
    assert result.returncode==0 and json.loads(result.stdout)['inserted']==0
    wrong=tmp_path/'wrong-config.json';wrong.write_text(json.dumps({**config,'password':'secret-never-output'}))
    args[-1]=str(wrong)
    result=subprocess.run([sys.executable,'-B','-m','nfl_sideline_etl.metrics_persistence',*args],capture_output=True,text=True)
    assert result.returncode==2
    assert 'secret-never-output' not in result.stdout+result.stderr


@pytest.mark.parametrize('changes,expected', [
    ({'phase':'PRE'},psycopg2.errors.CheckViolation),
    ({'round':'DIV'},psycopg2.errors.CheckViolation),
    ({'round':None},psycopg2.errors.CheckViolation),
    ({'home_team':'B'},psycopg2.errors.CheckViolation),
    ({'raw_n':-1},psycopg2.errors.CheckViolation),
    ({'unknown_filter_flags_n':-1},psycopg2.errors.CheckViolation),
    ({'outside_pass_run_null_teams_n':900},psycopg2.errors.CheckViolation),
    ({'calendar_duplicate_rows_ignored':-1},psycopg2.errors.CheckViolation),
    ({'raw_n':900},psycopg2.errors.CheckViolation),
    ({'eligible_content_n':None},psycopg2.errors.CheckViolation),
    ({'statistics_status':'COMPLETE'},psycopg2.errors.CheckViolation),
    ({'completeness':'invalid'},psycopg2.errors.CheckViolation),
    ({'pbp_revision_id':'sha256:'+'b'*64},psycopg2.errors.ForeignKeyViolation),
    ({'calendar_revision_id':'sha256:'+'b'*64},psycopg2.errors.ForeignKeyViolation),
    ({'game_id':'missing'},psycopg2.errors.ForeignKeyViolation),
])
def test_coverage_sql_constraints_source_references(db,tmp_path,changes,expected):
    config,_=db
    persist(original(tmp_path),tmp_path/'archive',config)
    record=query(config,"select row_to_json(c)::jsonb from metrics_private.game_metric_coverage_revision c where game_id='synthetic-1'")[0][0]
    record['coverage_revision_id']='sha256:'+'c'*64
    record.update(changes)
    conn=connect(config)
    try:
        with conn.cursor() as cur:
            with pytest.raises(expected):
                immutable_insert(cur,'game_metric_coverage_revision',('coverage_revision_id',),record,{'inserted':0,'reused':0})
    finally:
        conn.close()


@pytest.mark.parametrize('operation',['update','delete','truncate'])
def test_writer_cannot_rewrite_immutable_rows(db,tmp_path,operation):
    config,_=db
    persist(original(tmp_path),tmp_path/'archive',config)
    statements={'update':'update metrics_private.metric_source_revision set revision_id=revision_id',
                'delete':'delete from metrics_private.metric_source_revision',
                'truncate':'truncate metrics_private.metric_source_revision'}
    conn=connect(config)
    try:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):cur.execute(statements[operation])
    finally:
        conn.close()


def test_marker_mismatch_and_superuser_refused(db):
    config,admin=db
    with psycopg2.connect(**admin) as conn:
        with conn.cursor() as cur:
            cur.execute("update e5b2_instance.identity set purpose='wrong-delivery'")
    try:
        with pytest.raises(ValueError,match='identification mismatch'):connect(config)
    finally:
        with psycopg2.connect(**admin) as conn:
            with conn.cursor() as cur:
                cur.execute("update e5b2_instance.identity set purpose='metrics-persistence-e5b2-disposable'")
    password=config['password']+'-probe'
    with psycopg2.connect(**admin) as conn:
        with conn.cursor() as cur:
            cur.execute('create role e5b2_admin_probe login superuser password %s',(password,))
    try:
        with pytest.raises(ValueError,match='unprivileged'):connect({**config,'user':'e5b2_admin_probe','password':password})
    finally:
        with psycopg2.connect(**admin) as conn:
            with conn.cursor() as cur:cur.execute('drop role e5b2_admin_probe')
