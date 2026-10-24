"""Read-only product checks plus a documentation receipt; never a human-study result."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'c5be5b0dbb525faea85fab350039d8a5c1c87af5'
REF = Path('/Users/pedrocollet/.codex/worktrees/broadcast-matchup-reading-v1/NFL Sideline')
BUNDLE = Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled')
PIN = 'sha256:b10a2028f26d6acc229f80bbd27269016dd2e6b2e4b432a6d8a9109f643e5ee4'
sys.path.insert(0, str(ROOT / 'etl-pipeline/src'))
from nfl_sideline_etl.comparison_foundation.package import read

def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True)

assert git('rev-parse', 'HEAD', cwd=REF).strip() == BASE
assert not git('status', '--porcelain', cwd=REF)
assert git('branch', '--show-current').strip() == 'codex/broadcast-comprehension-v1'
changed = set(git('diff', '--name-only', BASE).splitlines() + git('ls-files', '--others', '--exclude-standard').splitlines())
assert all(p.startswith('docs/plans/broadcast-comprehension-v1/') for p in changed), changed
historical = git('ls-tree', '-r', '--name-only', BASE).splitlines()
assert not git('diff', BASE, '--', *historical).strip()
subprocess.run(['git', 'diff', '--check', BASE], cwd=ROOT, check=True)

document, marker = read(BUNDLE, PIN)
raw = (BUNDLE / 'comparison.json').read_bytes()
assert marker['bundleId'] == PIN == 'sha256:' + hashlib.sha256(raw).hexdigest()

def fetch(port, path, header=None):
    headers = {header: '1'} if header else {}
    with urlopen(Request(f'http://127.0.0.1:{port}' + path, headers=headers), timeout=15) as response:
        return response.status, response.read(), dict(response.headers)

assert fetch(18102, '/?view=matchup-reading')[0] == 200
status, wire, headers = fetch(18102, '/__matchup-reading/', 'X-Local-Matchup')
assert status == 200 and wire == raw and headers['X-Comparison-Bundle'] == PIN
assert json.loads(fetch(18101, '/__comparison/', 'X-Local-Comparison')[1]) == document
assert document['game'] == dict(gameId='2026_01_NYJ_TEN', season=2026, phase='REG', weeks=[1], offenses=['NYJ', 'TEN'])
assert [p['offense'] for p in document['productions']] == ['NYJ', 'TEN']
assert sum(len(p['thirdAttempts']) for p in document['productions']) == 22
assert sum(len(p['redZoneCampaigns']) for p in document['productions']) == 4
assert [len(document['leagueReferences'][f]['teamRateDistribution']['points']) for f in ('third', 'redZone')] == [32, 31]
assert document['temporalContext']['mode'] == 'RETROSPECTIVE' and not document['temporalContext']['w2ContextAllowed']
assert all(value == 'UNKNOWN' for value in document['guarantees'].values())

calendar = fetch(18102, '/data/seasons/2026.json')[1]
assert calendar == (ROOT / 'web-ui/public/data/seasons/2026.json').read_bytes()
game = next(g for g in json.loads(calendar)['games'] if g['gameId'] == '2026_01_NYJ_TEN')
assert (game['awayTeamAbbr'], game['homeTeamAbbr'], game['season'], game['gameType'], game['week'], game['gameday'], game['awayScore'], game['homeScore'], game['result']) == ('NYJ', 'TEN', 2026, 'REG', 1, '2026-09-13', 23, 10, -13)

before = json.loads((HERE / 'checks/listeners-before.json').read_bytes())
listeners = {}
for port, original in before.items():
    pid = original.splitlines()[1].split()[1]
    current = subprocess.check_output(['lsof', '-nP', '-a', '-p', pid, f'-iTCP:{port}', '-sTCP:LISTEN'], text=True)
    assert f'127.0.0.1:{port}' in current
    listeners[port] = dict(pid=int(pid), loopback=True, samePidAsBeforePreparation=True)

# Inspect the already-built reference; no rebuild is implied by this receipt.
public = {p.suffix: hashlib.sha256(p.read_bytes()).hexdigest() for p in (REF / 'web-ui/dist/assets').iterdir() if p.suffix in ('.js', '.css')}
assert public == {'.js': '73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5', '.css': '2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d'}
assert (ROOT / 'web-ui/src/components/visual-preparation-regressions.test.tsx').read_text().count('  it.fails(') == 5

participant = (HERE / 'PARTICIPANT.md').read_text()
tasks = [
    'Compare o que os dois ataques fizeram nas terceiras descidas. O que você conclui e onde encontrou essa informação?',
    'De qual jogo ou período são esses números? O que na página indica isso?',
    'Compare os dois ataques na red zone e explique sua conclusão.',
    'Compare a produção dos dois ataques pelo EPA. Explique, com suas palavras, o que os valores mostram.',
    'Como você usaria esta distribuição para contextualizar NYJ e TEN? O que ela permite dizer?',
    'Se quisesse conferir como um desses números foi calculado, onde procuraria?'
]
assert participant.count('## Tarefa ') == 6
assert all(participant.count(task) == 1 for task in tasks)
assert 'Use esta página para responder às perguntas. Você pode explorar qualquer parte dela. Se não encontrar algo ou não entender uma informação, diga isso.' in participant
assert not any(answer in participant for answer in ('2/10', '4/12', '1/5', '2/3', '1/1', '100%', '66,7%', '2026', 'W1', 'pontos esperados', 'maior taxa observada'))
assert 'Quem teve maior taxa? Quem marcou mais touchdowns? O que o 100% de TEN permite concluir?' in (HERE / 'MODERATOR.md').read_text()
assert 'Agora consulte somente o passe e compare os dois ataques.' in (HERE / 'MODERATOR.md').read_text()
walk = json.loads((HERE / 'evidence/technical-walkthrough.json').read_bytes())
assert walk['kind'] == 'AGENT_TECHNICAL_WALKTHROUGH' and walk['humanParticipants'] == 0
assert {a['task'] for a in walk['actions']} == {1, 2, 3, 4, 5, 6}
assert walk['restored']['foundation'] == 'general' and walk['restored']['hash'] == '' and walk['restored']['openDetails'] == 0

report = dict(kind='PRE_COLLECTION_TECHNICAL_CHECK_ONLY', clientDate='2026-10-24', clientTimezone='America/Fortaleza', base=BASE,
    referenceCleanAtExactHead=True, humanSessionsRegistered=0, newInterfaceChanges=0, changedPaths=sorted(changed),
    historicalFilesUnchanged=len(historical), fullReaderValidated=True, pin=PIN, wireBytes=len(wire), wireExactlyMatchesArtifact=True,
    twoProductions=True, sixEpaObservations=sum(len(p['epa']) for p in document['productions']), thirdMarks=22, redZoneCampaigns=4,
    leaguePoints=[32, 31], calendarIdentityAndAtomicScoreVerified=True, walkthroughAllSixTasks=True,
    participantMaterialReviewedWithoutAnswerKey=True, taskWordingMatchesRequest=True, listeners=listeners,
    existingReferencePublicBuildHashes=public, buildsRerun=False, applicationTestsRerun=False, fiveLegacyExpectedFailuresUnchanged=True)
(HERE / 'checks/technical.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print('Preparation check PASS: exact source/HTTP, six destinations, neutral materials, historical files and five listeners unchanged. Human sessions: 0.')
