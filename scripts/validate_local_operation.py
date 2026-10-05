#!/usr/bin/env python3
"""Real loopback HTTP checks against a prebuilt JAR; no credentials or external requests."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
JAVA = '/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home/bin/java'
JAR = ROOT / 'core-api/target/core-api-0.1.0.jar'
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'en_US.UTF-8'}


def read(p):
    return json.loads(p.read_text())


def save(p, value):
    with p.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def run(output):
    output = output.resolve()
    if not output.is_relative_to(ROOT / 'editorial') or 'public' in output.parts:
        raise ValueError('Use a new internal editorial output directory')
    output.mkdir()
    contexts = output / 'contexts'; contexts.mkdir()
    storage = output / 'results'; storage.mkdir()
    cli = output / 'cli'; cli.mkdir()
    exchanges = output / 'http'; exchanges.mkdir()
    old = ROOT / 'editorial/coverage-clarity-v1/batch-01'
    ids = []
    for directory in sorted(old.iterdir()):
        if directory.is_dir() and (directory / 'context.json').exists():
            source = directory / 'context.json'
            game = read(source)['game']['game_id']
            shutil.copy2(source, contexts / (game + '.json'))
            ids.append(game)
    assert len(ids) == 21
    report = {'transport': 'REAL_LOOPBACK_HTTP', 'jarSha256': hashlib.sha256(JAR.read_bytes()).hexdigest(),
              'independentEvaluation': False, 'cases': [], 'requests': [], 'processes': []}
    process = None
    log = None
    port = None

    def stop():
        nonlocal process, log
        if process is not None:
            process.terminate()
            try:
                code = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill(); code = process.wait(timeout=5)
            report['processes'][-1].update({'exitCode': code, 'stopped': process.poll() is not None})
            process = None
        if log is not None:
            log.close(); log = None

    def start():
        nonlocal process, log, port
        name = 'server-' + str(len(report['processes']) + 1) + '.log'
        log = (output / name).open('x')
        process = subprocess.Popen([JAVA, '-jar', str(JAR), 'editorial-local-serve', str(contexts), str(storage), '0'],
                                   cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
        report['processes'].append({'pid': process.pid, 'log': name, 'stopped': False})
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            text = (output / name).read_text()
            match = re.search(r'LOCAL_ANALYSIS_READY http://127\.0\.0\.1:(\d+)', text)
            if match:
                port = int(match.group(1)); report['processes'][-1]['port'] = port
                return
            if process.poll() is not None:
                raise RuntimeError('Server failed to bind/start: ' + text.strip())
            time.sleep(.1)
        raise TimeoutError('Server readiness timeout')

    def request(method, path, expected, label, headers=None, body=None):
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            payload = json.loads(response.read())
            record = {'method': method, 'path': path, 'status': response.status,
                      'headers': dict(response.getheaders()), 'body': payload}
            save(exchanges / (label + '.json'), record)
            assert response.status == expected, (label, response.status, payload)
            assert record['headers']['Cache-control'] == 'no-store'
            assert not any(k.lower().startswith('access-control-allow') for k in record['headers'])
            report['requests'].append({'label': label, 'status': response.status})
            if expected >= 400:
                assert set(payload) == {'error'} and re.fullmatch('[A-Z_]+', payload['error'])
            return record
        finally:
            conn.close()

    try:
        start()
        responses = []
        for game in ids:
            dest = cli / game
            completed = subprocess.run([JAVA, '-jar', str(JAR), 'editorial-local', str(contexts / (game + '.json')), str(dest)],
                                       cwd=ROOT, env=ENV, capture_output=True, timeout=45)
            assert completed.returncode == 0
            prefix = '/api/v1/local-analysis/' + game
            created = request('POST', prefix, 201, game + '-post')
            value = created['body']; responses.append(value)
            assert value['mode'] == 'LOCAL_RULES_DEVELOPMENT' and value['publicationApproved'] is False
            assert set(value['analysis']) == {'fator_chave', 'vantagem_tatica', 'alerta_vermelho', 'veredito'}
            location = created['headers']['Location']
            assert location == prefix + '/' + value['attemptId']
            assert request('GET', location, 200, game + '-get')['body'] == value
            assert value['analysis'] == read(dest / 'rendered.json')
            assert value['resultIdentity'] == read(dest / 'result.json')['resultIdentity']
            for file in ['claims.json', 'selection.json']:
                assert read(dest / file) == read(old / game / file)
                assert read(dest / file) == read(storage / value['attemptId'] / file)
            before = read(old / game / 'rendered.json')
            changed = [key for key in before if before[key] != value['analysis'][key]]
            assert changed == (['alerta_vermelho'] if game == '2026_03_LV_NO' else [])
            report['cases'].append({'gameId': game, 'cliHttpParity': True, 'selectionUnchanged': True, 'changedBlocks': changed})
        game = '2026_03_BAL_DAL'; prefix = '/api/v1/local-analysis/' + game
        with ThreadPoolExecutor(max_workers=4) as pool:
            repeated = list(pool.map(lambda i: request('POST', prefix, 201, 'concurrent-' + str(i))['body'], range(4)))
        assert len({v['attemptId'] for v in repeated}) == 4
        assert len({v['resultIdentity'] for v in repeated}) == 1
        report['concurrentAttempts'] = 4
        request('POST', prefix, 400, 'origin-rejected', {'Origin': 'http://localhost:5173'})
        request('POST', prefix, 400, 'host-rejected', {'Host': 'localhost:' + str(port)})
        request('POST', prefix, 400, 'body-rejected', body='{}')
        request('POST', prefix + '?x=1', 400, 'query-rejected')
        request('POST', '/api/v1/local-analysis/%2e%2e', 400, 'encoding-rejected')
        request('POST', '/api/v1/local-analysis/missing', 404, 'unknown-game')
        request('GET', prefix, 405, 'method-rejected')
        request('GET', prefix + '/00000000-0000-0000-0000-000000000000', 404, 'unknown-result')
        duplicate = subprocess.run([JAVA, '-jar', str(JAR), 'editorial-local-serve', str(contexts), str(storage), '0'],
                                   cwd=ROOT, env=ENV, capture_output=True, timeout=15)
        assert duplicate.returncode != 0
        report['secondOwnerRejected'] = True
        stop(); start()
        for value in responses:
            route = '/api/v1/local-analysis/' + value['gameId'] + '/' + value['attemptId']
            assert request('GET', route, 200, value['gameId'] + '-after-restart')['body'] == value
        report['persistedAfterRestart'] = len(responses)
        report['status'] = 'PASSED'
    except Exception as error:
        report['status'] = 'FAILED'
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        stop()
        save(output / 'verification.json', report)
    print(json.dumps({'status': report['status'], 'cases': len(report['cases']), 'requests': len(report['requests'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    run(parser.parse_args().output)
