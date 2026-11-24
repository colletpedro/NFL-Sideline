"""No database required. Real PostgreSQL tests live in the explicit e5b-2 suite."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from nfl_sideline_etl.offline_metrics.artifact import identity, json_bytes, write_artifact
from nfl_sideline_etl.metrics_persistence.archive import Archive, digest
from nfl_sideline_etl.metrics_persistence.connection import configuration
from nfl_sideline_etl.metrics_persistence.plan import prepare

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'etl-pipeline/tests/fixtures/offline_metrics'
ARTIFACT = ROOT / 'docs/plans/metrics/e5b-1/synthetic-result'


def plan(root=ARTIFACT, archive='/tmp/nfl-e5b2-test-unused-archive'):
    return prepare(root, [FIXTURE / 'calendar.json'], [FIXTURE / 'pbp.json'], archive)


def rewritten(tmp_path, mutation):
    result = deepcopy(plan().result)
    mutation(result)
    result['manifest.json'].pop('calculation_id')
    result['manifest.json']['calculation_id'] = identity(result)
    output = tmp_path / 'forged'
    write_artifact(output, result)
    return output


def test_dry_run_no_database_network_env_or_archive(tmp_path):
    archive = tmp_path / 'archive'
    script = '''
import importlib.abc, sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'dotenv','psycopg2','boto3','nflreadpy','requests','httpx'}:
            raise AssertionError('Forbidden import: '+fullname)
sys.meta_path.insert(0, Guard())
from nfl_sideline_etl.metrics_persistence.__main__ import main
raise SystemExit(main(sys.argv[1:]))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, '--dry-run', '--artifact', str(ARTIFACT),
        '--calendar', str(FIXTURE / 'calendar.json'), '--pbp', str(FIXTURE / 'pbp.json'),
        '--archive', str(archive), '--local-config', str(tmp_path / 'nonexistent')],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['database_connected'] is False
    assert not archive.exists()


@pytest.mark.parametrize('mutation', [
    lambda r: r['statistics.json'][0].update(eligible_n=-1),
    lambda r: r['statistics.json'][0].update(epa_n=100),
    lambda r: r['statistics.json'][0].update(success_n=100),
    lambda r: r['statistics.json'][0].update(epa_sum='NaN'),
    lambda r: r['statistics.json'][0].update(epa_sum='0'),
    lambda r: r['statistics.json'][0].update(team='C'),
    lambda r: r['statistics.json'][0].update(role='other'),
    lambda r: r['statistics.json'][0].update(scope='FULL_GAME_CONTENT',statistics_status='COMPLETE'),
    lambda r: r['statistics.json'].append(deepcopy(r['statistics.json'][0])),
    lambda r: r['statistics.json'].pop(),
    lambda r: r['game-audit.json'][0].update(coverage_revision_id='sha256:' + '1'*64),
    lambda r: r['game-audit.json'][0].update(unique_n=500),
    lambda r: r['reconciliation.json']['checks'].update(general_equals_pass_plus_rush=False),
    lambda r: r['manifest.json']['source_model_versions'].clear(),
])
def test_rehashed_semantically_invalid_artifact_rejected(tmp_path, mutation):
    with pytest.raises(ValueError, match='semantic'):
        plan(rewritten(tmp_path, mutation), tmp_path / 'archive')
    assert not (tmp_path / 'archive').exists()


@pytest.mark.parametrize('failure', ['missing', 'corrupt', 'incomplete', 'calculation', 'version', 'duplicate_json'])
def test_artifact_integrity_and_structure(tmp_path, failure):
    import shutil
    output = tmp_path / 'artifact'
    shutil.copytree(ARTIFACT, output)
    if failure == 'missing':
        (output / 'statistics.json').unlink()
    elif failure == 'corrupt':
        (output / 'statistics.json').write_bytes(b'[]')
    elif failure == 'incomplete':
        (output / 'COMPLETED.json').unlink()
    elif failure == 'duplicate_json':
        (output / 'COMPLETED.json').write_text('{"files":{},"files":{}}')
    else:
        marker = json.loads((output / 'COMPLETED.json').read_text())
        marker['calculation_id' if failure == 'calculation' else 'artifactVersion'] = 'wrong'
        (output / 'COMPLETED.json').write_text(json.dumps(marker))
    with pytest.raises(ValueError):
        plan(output, tmp_path / 'archive')


def test_sources_must_match_descriptors_and_multiplicity(tmp_path):
    pbp = tmp_path / 'pbp.json'
    pbp.write_bytes((FIXTURE / 'pbp.json').read_bytes() + b'\n')
    with pytest.raises(ValueError, match='sources'):
        prepare(ARTIFACT, [FIXTURE / 'calendar.json'], [pbp], tmp_path / 'archive')
    with pytest.raises(ValueError, match='sources'):
        prepare(ARTIFACT, [FIXTURE / 'calendar.json'], [FIXTURE / 'pbp.json'] * 2, tmp_path / 'archive')


def test_archive_idempotent_first_receipt_and_exact_retrieval(tmp_path):
    archive = Archive(tmp_path / 'archive')
    data = b'exact local bytes\x00\xff'
    sha = digest(data)
    first = archive.put(data, sha, {'path':'first'})
    second = Archive(archive.root).put(data, sha, {'path':'different'})
    assert first == second
    assert archive.read(sha) == data
    assert len(list((archive.root / 'blobs').rglob(sha))) == 1
    assert len(list((archive.root / 'receipts').iterdir())) == 1
    assert first['observed_at'].endswith('Z')


@pytest.mark.parametrize('failure', ['corrupt', 'missing', 'receipt', 'bad_bytes', 'symlink'])
def test_archive_rejects_invalid_content_without_overwrite(tmp_path, failure):
    archive = Archive(tmp_path / 'archive')
    data = b'bytes'
    sha = digest(data)
    archive.put(data, sha, {'path': 'original'})
    blob = archive.root / archive.locator(sha)
    if failure == 'corrupt': blob.write_bytes(b'wrong')
    elif failure == 'missing': blob.unlink()
    elif failure == 'receipt': (archive.root / 'receipts' / f'{sha}.json').write_bytes(b'{}')
    elif failure == 'symlink':
        blob.unlink()
        link_target = tmp_path / 'external'
        link_target.write_bytes(data)
        blob.symlink_to(link_target)
    if failure == 'missing':
        with pytest.raises(ValueError): archive.read(sha)
        assert archive.put(data, sha, {'path': 'retry'})
    else:
        with pytest.raises(ValueError): archive.put(b'other' if failure == 'bad_bytes' else data, sha, {})
    if failure == 'corrupt': assert blob.read_bytes() == b'wrong'


def test_public_archive_including_symlink_forbidden(tmp_path):
    public = tmp_path / 'web-ui/public/data'
    public.mkdir(parents=True)
    link = tmp_path / 'alias'
    link.symlink_to(public, target_is_directory=True)
    for root in (public, link):
        with pytest.raises(ValueError, match='forbidden'): Archive(root)
        with pytest.raises(ValueError, match='forbidden'): plan(archive=root)


@pytest.mark.parametrize('host', ['localhost','db.remote.test','127.0.0.1,db.remote.test','/tmp',''])
def test_explicit_config_rejects_nonliteral_local_host(tmp_path, host):
    path = tmp_path / 'local.json'
    path.write_text(json.dumps(dict(host=host, port=55482, database='other', user='writer',
                                   password='secret-never-log',instance_id='00000000-0000-0000-0000-000000000001')))
    with pytest.raises(ValueError, match='loopback'): configuration(path)


def test_cli_error_sanitized_no_password_or_dsn(tmp_path, capsys):
    from nfl_sideline_etl.metrics_persistence.__main__ import main
    config = tmp_path / 'bad.json'
    config.write_text(json.dumps({'password':'secret-never-log','dsn':'postgres://secret-never-log@remote'}))
    assert main(['--persist','--artifact',str(ARTIFACT),'--calendar',str(FIXTURE / 'calendar.json'),
                 '--pbp',str(FIXTURE / 'pbp.json'),'--archive',str(tmp_path / 'archive'),
                 '--local-config',str(config)]) == 2
    output = capsys.readouterr()
    assert 'secret-never-log' not in output.out + output.err
    assert 'postgres://' not in output.out + output.err
    assert not (tmp_path / 'archive').exists()


def test_nested_archive_symlink_cannot_escape_to_public(tmp_path):
    archive=Archive(tmp_path/'archive')
    public=tmp_path/'web-ui/public/data';public.mkdir(parents=True)
    (archive.root/'blobs').symlink_to(public,target_is_directory=True)
    with pytest.raises(ValueError,match='symlink'):
        archive.put(b'bytes',digest(b'bytes'),{})
    assert not list(public.iterdir())


def test_mutated_python_plan_cannot_bypass_validation(tmp_path):
    from nfl_sideline_etl.metrics_persistence.plan import validate_plan
    planned=plan(archive=tmp_path/'archive')
    planned.result['statistics.json'][0]['epa_sum']='123'
    with pytest.raises(ValueError,match='differs'):validate_plan(planned,tmp_path/'archive')
    assert not (tmp_path/'archive').exists()
