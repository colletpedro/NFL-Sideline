"""E5b-4 offline gate at its exact integration base; no historical evidence edits."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / 'etl-pipeline/tests/fixtures/temporal_metrics'
BASE = '8f583c4ec9ed83f86c2229b0f1656d32403bcc31'


def run(args):
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError('Gate failed: ' + ' '.join(map(str, args)) + '\n' + completed.stdout + completed.stderr)
    return completed.stdout, completed.stderr


def python(*args):
    return run([sys.executable, '-B', *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New verification report file')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Report already exists')
    report = {'base': BASE, 'scope': 'OFFLINE_ONLY', 'databaseConnected': False,
              'algorithmVersion':'metrics-temporal-1.0.1', 'resultVersion':'metrics-temporal-result-v2',
              'historicalEvidenceHead':'767cf7f1d15f26022a7c4a982545a6c24c125134',
              'candidateHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    report['materializerSourceHashes'] = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'etl-pipeline/src/nfl_sideline_etl/metrics_materialization').glob('*.py'))}
    report['testedSourceHashes'] = {
        str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'etl-pipeline/src/nfl_sideline_etl/temporal_metrics').glob('*.py'))}
    report['testedSourceHashes'].update({
        str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'etl-pipeline/tests').glob('test_temporal_metrics*.py'))})
    report['historicalEvidenceHashes'] = {}
    historical = ROOT/'docs/plans/metrics/e5b-3'
    paths = [historical/'verification.json', *sorted((historical/'examples').rglob('*.json'))]
    for path in paths:
        relative = str(path.relative_to(ROOT))
        old = subprocess.check_output(['git','show',report['historicalEvidenceHead']+':'+relative],cwd=ROOT)
        if old != path.read_bytes():
            raise RuntimeError('Historical 1.0.0 evidence changed: '+relative)
        report['historicalEvidenceHashes'][relative] = hashlib.sha256(old).hexdigest()
    stdout, _ = python('-m', 'pytest', 'etl-pipeline', '-q', '-p', 'no:cacheprovider')
    report['etlTestsPassed'] = int(re.search(r'(\d+) passed', stdout).group(1))
    report['etlLog'] = stdout
    stdout, _ = python('contracts/metrics/e5a-v1/verify.py')
    report['e5aVerifier'] = json.loads(stdout)
    _, stderr = python('-m', 'unittest', 'discover', '-s', 'contracts/metrics/e5a-v1', '-p', 'test_*.py', '-v')
    report['e5aTestsPassed'] = int(re.search(r'Ran (\d+) tests', stderr).group(1))
    stdout, _ = python('docs/plans/metrics/e5a-review/reproduce_boundary.py')
    report['frozenContractChecks'] = json.loads(stdout)
    protected = ['contracts/metrics/e5a-v1', 'etl-pipeline/src/nfl_sideline_etl/offline_metrics',
                 'etl-pipeline/src/nfl_sideline_etl/metrics_persistence', 'docs/plans/metrics/e5b-1',
                 'docs/plans/metrics/e5b-2', 'supabase', 'web-ui', 'Spec.md', 'docs/current-state.md',
                 'etl-pipeline/src/nfl_sideline_etl/temporal_metrics',
                 'etl-pipeline/tests/test_temporal_metrics.py',
                 'etl-pipeline/tests/test_temporal_metrics_correction.py',
                 'docs/plans/metrics/e5b-3', 'docs/plans/metrics/e5b-3-review']
    stdout, _ = run(['git', 'diff', BASE, '--', *protected])
    if stdout:
        raise RuntimeError('Frozen/accepted scope changed')
    report['protectedPathsUnchanged'] = protected
    allowed = ('docs/plans/metrics/e5b-4/', 'etl-pipeline/src/nfl_sideline_etl/metrics_materialization/',
               'etl-pipeline/tests/test_metrics_materialization.py',
               'etl-pipeline/tests/fixtures/metrics_materialization/',
               'core-api/src/main/java/com/nflsideline/coreapi/metrics/temporal/',
               'core-api/src/test/java/com/nflsideline/coreapi/metrics/temporal/',
               'core-api/src/test/resources/metrics-temporal/')
    dispatcher = 'core-api/src/main/java/com/nflsideline/coreapi/CoreApiApplication.java'
    stdout, _ = run(['git', 'diff', '--name-only', BASE])
    unexpected = [path for path in stdout.splitlines() if path != dispatcher and not path.startswith(allowed)]
    if unexpected: raise RuntimeError('Outside E5b-4 boundary: ' + ','.join(unexpected))
    original_dispatcher = subprocess.check_output(['git','show',BASE+':'+dispatcher],cwd=ROOT,text=True)
    current_dispatcher = (ROOT/dispatcher).read_text()
    added = '''        if (args.length > 0 && "metrics-temporal-read".equals(args[0])) {
            int exitCode = com.nflsideline.coreapi.metrics.temporal.TemporalReadApplication.run(
                    Arrays.copyOfRange(args, 1, args.length));
            if (exitCode != 0) System.exit(exitCode);
            return;
        }
'''
    if current_dispatcher.replace(added, '') != original_dispatcher:
        raise RuntimeError('Previous dispatcher behavior changed')
    report['previousDispatcherPreserved'] = True
    with tempfile.TemporaryDirectory(prefix='nfl-e5b3-gates-') as temp:
        temp = Path(temp)
        old_fixture = 'etl-pipeline/tests/fixtures/offline_metrics/'
        original = temp / 'e5b1-regression'
        python('-m', 'nfl_sideline_etl.offline_metrics', '--calendar', old_fixture+'calendar.json',
               '--pbp', old_fixture+'pbp.json', '--metadata', old_fixture+'metadata.json',
               '--season', '2026', '--output', str(original))
        accepted = ROOT / 'docs/plans/metrics/e5b-1/synthetic-result'
        hashes = {}
        for file in accepted.iterdir():
            data = (original / file.name).read_bytes()
            if data != file.read_bytes():
                raise RuntimeError('E5b-1 regression differs: ' + file.name)
            hashes[file.name] = hashlib.sha256(data).hexdigest()
        report['e5b1ByteRegression'] = hashes
        archive = temp / 'dry-run-archive-must-not-exist'
        stdout, _ = python('-m', 'nfl_sideline_etl.metrics_persistence', '--dry-run',
                           '--artifact', str(accepted), '--calendar', old_fixture+'calendar.json',
                           '--pbp', old_fixture+'pbp.json', '--archive', str(archive))
        report['e5b2DryRun'] = json.loads(stdout)
        if archive.exists() or report['e5b2DryRun'].get('database_connected') is not False:
            raise RuntimeError('Dry-run crossed offline boundary')
        report['examples'] = {}
        for name, filename, mode in [('point-in-time', 'package.json', 'POINT_IN_TIME'),
                                     ('reconstruction', 'package.json', 'EVENT_RECONSTRUCTION'),
                                     ('unproven', 'package-unproven.json', 'POINT_IN_TIME')]:
            destination = temp / name
            command = ['-m', 'nfl_sideline_etl.temporal_metrics', '--input', str(FIXTURES/filename),
                       '--season','2026','--phase','REG','--team','A','--target-game-id','target',
                       '--target-week','4','--window','LAST_3_CALENDAR_WEEKS','--window','SEASON_TO_CUTOFF',
                       '--window','WEEK_OBSERVATION','--week','3','--as-of-instant','2026-09-28T12:00:00Z',
                       '--mode',mode,'--derived-at','2026-10-09T12:00:00Z','--output',str(destination)]
            if mode == 'EVENT_RECONSTRUCTION':
                command.extend(['--retrospective',str(FIXTURES/'retrospective.json')])
            python(*command)
            data = (destination/'result.json').read_bytes()
            saved = ROOT/'docs/plans/metrics/e5b-3/correction-1.0.1/examples'/name/'result.json'
            if data != saved.read_bytes():
                raise RuntimeError('Versioned example differs: ' + name)
            result = json.loads(data)
            report['examples'][name] = {'result_id':result['result_id'],'audit_id':result['audit_id'],
                                      'sha256':hashlib.sha256(data).hexdigest()}
            old = json.loads((ROOT/'docs/plans/metrics/e5b-3/examples'/name/'result.json').read_text())
            report['examples'][name]['historicalResultId'] = old['result_id']
            report['examples'][name]['historicalAuditId'] = old['audit_id']
            completed = (destination/'COMPLETED.json').read_bytes()
            if completed != (saved.parent/'COMPLETED.json').read_bytes():
                raise RuntimeError('Current marker differs: '+name)
        after = temp/'counterexamples-after.json'
        python('docs/plans/metrics/e5b-3/correction-1.0.1/reproduce.py','--output',str(after))
        report['counterexamplesAfter'] = json.loads(after.read_text())
        saved_after = json.loads((ROOT/'docs/plans/metrics/e5b-3/correction-1.0.1/counterexamples-after.json').read_text())
        if report['counterexamplesAfter']['cases'] != saved_after['cases']:
            raise RuntimeError('Corrected counterexamples differ')
        report['counterexamplesBeforeSha256'] = hashlib.sha256((ROOT/'docs/plans/metrics/e5b-3/correction-1.0.1/counterexamples-before.json').read_bytes()).hexdigest()
    run(['git', 'diff', '--check'])
    report['diffCheck'] = 'PASSED'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k:report[k] for k in ('etlTestsPassed','e5aTestsPassed','diffCheck')}))


if __name__ == '__main__':
    main()
