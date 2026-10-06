#!/usr/bin/env python3
"""HTTP smoke checks for an already running loopback API + development UI. No env, DB or external calls."""
import argparse
import http.client
import json
from pathlib import Path


def verify():
    checks = []
    def request(port, method, path, expected, headers=None, body=None):
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            raw = response.read()
            assert response.status == expected, (method, path, response.status, expected)
            assert not response.getheader('Access-Control-Allow-Origin')
            checks.append({'port': port, 'method': method, 'path': path, 'status': response.status})
            return json.loads(raw) if response.getheader('Content-Type', '').startswith('application/json') else raw
        finally:
            conn.close()
    ui, api = 18083, 18081
    prefix = '/__editorial/'
    marker = {'X-Local-Editorial': '1'}
    same = {**marker, 'Origin': 'http://127.0.0.1:18083'}
    catalog = request(ui, 'GET', prefix, 200, marker)
    assert catalog and 'evidence' not in catalog[0]
    game = catalog[0]['gameId']
    request(ui, 'GET', '/', 200)
    request(ui, 'GET', prefix, 403)
    request(ui, 'GET', prefix, 403, {**marker, 'Origin': 'https://example.invalid'})
    request(ui, 'GET', prefix, 403, {**marker, 'Host': 'example.invalid:18083'})
    request(ui, 'POST', prefix+game, 403, marker)
    request(ui, 'POST', prefix+game, 403, {'Origin': same['Origin']})
    request(ui, 'POST', prefix+game, 403, {**marker, 'Origin': 'null'})
    request(ui, 'POST', prefix+game, 403, {**marker, 'Origin': 'https://example.invalid'})
    request(ui, 'POST', prefix+game, 403, same, '{}')
    request(ui, 'POST', prefix+game+'?x=1', 403, same)
    request(ui, 'POST', prefix+'%2e%2e', 403, same)
    request(ui, 'OPTIONS', prefix+game, 403, same)
    request(ui, 'GET', prefix+'missing/attempts', 404, marker)
    request(api, 'GET', '/api/v1/local-analysis/', 400, {'Origin': same['Origin']})
    direct = request(api, 'GET', '/api/v1/local-analysis/', 200)
    assert direct == catalog
    before = request(ui, 'GET', prefix+game+'/attempts', 200, marker)
    first = request(ui, 'POST', prefix+game, 201, same)
    second = request(ui, 'POST', prefix+game, 201, same)
    assert first['attemptId'] != second['attemptId']
    assert first['resultIdentity'] == second['resultIdentity']
    assert first['publicationApproved'] is False and first['mode'] == 'LOCAL_RULES_DEVELOPMENT'
    assert request(ui, 'GET', prefix+game+'/'+first['attemptId'], 200, marker) == first
    after = request(ui, 'GET', prefix+game+'/attempts', 200, marker)
    assert len(after['attempts']) == len(before['attempts']) + 2
    return {'transport': 'real HTTP on loopback', 'catalogCount': len(catalog), 'checks': checks,
            'attempts': [first['attemptId'], second['attemptId']], 'status': 'PASS'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New JSON file outside public data')
    args = parser.parse_args()
    if 'public' in args.output.resolve().parts:
        parser.error('Public output is forbidden')
    # Reserve output before any request; never overwrite existing evidence.
    with args.output.open('x', encoding='utf-8') as out:
        result = verify()
        json.dump(result, out, indent=2)
        out.write('\n')
    print(f"PASS: {len(result['checks'])} HTTP checks, {result['catalogCount']} contexts")
