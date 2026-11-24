"""HTTP bytes of the new projection and all preserved team/matchup documents."""
import http.client
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
config = json.loads((HERE/'source-config.json').read_bytes())
root = Path(config['path'])
pin = config['expectedBundleId']
requests = []


def get(path, headers, expected=200, method='GET'):
    c = http.client.HTTPConnection('127.0.0.1', 18108, timeout=15)
    c.request(method, path, headers=headers)
    r = c.getresponse(); b = r.read(); h = dict(r.getheaders()); c.close()
    assert r.status == expected, (path, r.status, b[:120])
    requests.append(dict(path=path, method=method, status=r.status))
    return b, h


headers = {'X-Local-Redzone-Epa': '1', 'X-Redzone-Epa-Collection': pin}
b, h = get('/__redzone-epa/', headers)
assert b == (root/'redzone-epa.json').read_bytes()
assert h['X-Redzone-Epa-Collection'] == pin and h['Cache-Control'] == 'no-store'
assert h['X-Content-Type-Options'] == 'nosniff'
for path, hs, code, method in [('/__redzone-epa/', {}, 403, 'GET'),
    ('/__redzone-epa/', headers, 403, 'POST'),
    ('/__redzone-epa/?path=/tmp/other', headers, 403, 'GET'),
    ('/__redzone-epa/../other', headers, 403, 'GET'),
    ('/__redzone-epa/', headers|{'Host': 'localhost:18108'}, 403, 'GET'),
    ('/__redzone-epa/', headers|{'Origin': 'http://127.0.0.1:18107'}, 403, 'GET'),
    ('/__redzone-epa/', headers|{'Content-Length': '1'}, 403, 'GET'),
    ('/__redzone-epa/', headers|{'X-Redzone-Epa-Collection': 'changed'}, 409, 'GET')]:
    get(path, hs, code, method)
for name in ['Host', 'Origin', 'X-Local-Redzone-Epa', 'X-Redzone-Epa-Collection']:
    c = http.client.HTTPConnection('127.0.0.1', 18108, timeout=15)
    c.putrequest('GET', '/__redzone-epa/', skip_host=True)
    all_headers = {'Host':'127.0.0.1:18108','Origin':'http://127.0.0.1:18108',**headers}
    for k,v in all_headers.items():c.putheader(k,v)
    c.putheader(name, all_headers[name]);c.endheaders();r=c.getresponse();r.read();c.close()
    assert r.status == 403
    requests.append(dict(duplicate=name,status=403))

team_root = Path('/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle')
for source, prefix, hs, entries, id_field in [
    (team_root,'/__team-w12/',{'X-Local-Team-W12':'1','X-Team-Collection':'sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef'},'teams','team'),
    (root/'source','/__matchup-w12/',{'X-Local-Matchup-W12':'1','X-Matchup-Collection':'sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc'},'games','gameId')]:
    index = json.loads((source/'index.json').read_bytes())
    b, _ = get(prefix, hs); assert b == (source/'index.json').read_bytes()
    for entry in index[entries]:
        b, _ = get(prefix+entry[id_field], hs)
        assert b == (source/entry['path']).read_bytes()
(HERE/'checks/http.json').write_text(json.dumps(dict(newPin=pin,requests=requests,exactPreservedDocuments=64,newPayloadExact=True),indent=2)+'\n')
print('PASS',len(requests),'HTTP checks; new projection exact, 64 old documents unchanged')
