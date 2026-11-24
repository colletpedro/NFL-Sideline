#!/usr/bin/env python3
"""Verify the 17 E2 cases through the running local Vite proxy; no external requests.

Requires the local API on 18081, UI on 18083 and an isolated result store.
With --replay, only GETs are issued, for example after restarting the API.
"""
import argparse
import hashlib
import http.client
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / 'editorial/evaluations/2026-10-06-visual-e2'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(path):
    return {p.name: sha(p) for p in path.iterdir() if p.is_file()}


def run(results, output, replay=None):
    results = results.resolve(strict=True)
    output = output.resolve()
    if 'public' in results.parts or 'public' in output.parts or output.exists():
        raise ValueError('Use an isolated internal result store and a new report path')
    manifest = read(BATCH / 'manifest.json')['documents']
    previous = {item['gameId']: item for item in read(replay)['cases']} if replay else {}
    report = {'transport': 'REAL_HTTP_THROUGH_VITE_PROXY', 'readOnlyReplay': bool(replay),
              'independentEditorialEvaluation': False, 'cases': [], 'requests': [], 'legacy': []}

    def request(method, path, status=200, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', 18083, timeout=15)
        try:
            conn.request(method, '/__editorial/' + path, headers=headers or {
                'X-Local-Editorial': '1', 'Origin': 'http://127.0.0.1:18083'})
            response = conn.getresponse()
            body = response.read()
            assert response.status == status, (method, path, response.status, body)
            report['requests'].append({'method': method, 'path': path, 'status': response.status})
            return json.loads(body)
        finally:
            conn.close()

    before = {p.name: files(p) for p in results.iterdir() if p.is_dir()}
    catalog = request('GET', '')
    assert {d['gameId'] for d in manifest}.issubset({c['gameId'] for c in catalog})
    for entry in manifest:
        game = entry['gameId']
        if replay:
            response = request('GET', game + '/' + previous[game]['attemptId'])
        else:
            response = request('POST', game, 201)
        attempt = response['attemptId']
        path = game + '/' + attempt
        assert request('GET', path) == response
        view = request('GET', path + '/insights')
        local = results / attempt
        assert view['document'] == read(BATCH / entry['document'])
        assert view['visualIdentity'] == entry['visualIdentity'] == sha(local / 'insights.json')
        assert view['resultIdentity'] == response['resultIdentity'] == entry['resultIdentity']
        assert any(x['attemptId'] == attempt for x in request('GET', game + '/attempts')['attempts'])
        if replay:
            assert previous[game]['hashes'] == files(local)
        report['cases'].append({'gameId': game, 'attemptId': attempt,
                                'resultIdentity': response['resultIdentity'],
                                'visualIdentity': view['visualIdentity'], 'hashes': files(local)})
    for directory in sorted(results.iterdir()):
        if not directory.is_dir() or not (directory / 'complete.json').exists():
            continue
        if read(directory / 'result.json')['artifactVersion'] != 3:
            continue
        response = read(directory / 'complete.json')['response']
        path = response['gameId'] + '/' + response['attemptId']
        assert request('GET', path) == response
        assert request('GET', path + '/insights', 409)['error'] == 'VISUAL_DOCUMENT_NOT_AVAILABLE'
        report['legacy'].append({'gameId': response['gameId'], 'attemptId': response['attemptId'],
                                  'hashes': files(directory)})
    if not replay:
        request('POST', manifest[0]['gameId'], 403,
                {'X-Local-Editorial': '1', 'Origin': 'https://example.invalid'})
    request('GET', manifest[0]['gameId'] + '/not-a-uuid/insights', 403)
    after = {p.name: files(p) for p in results.iterdir() if p.is_dir()}
    assert all(after[name] == hashes for name, hashes in before.items())
    if replay:
        assert before == after
    report['status'] = 'PASS'
    with output.open('x') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(f"PASS: {len(report['cases'])} cases, {len(report['legacy'])} v3, "
          f"{len(report['requests'])} HTTP requests, replay={bool(replay)}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--replay', type=Path)
    args = parser.parse_args()
    run(args.results, args.output, args.replay)
