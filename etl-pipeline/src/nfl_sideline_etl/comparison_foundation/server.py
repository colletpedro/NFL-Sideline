"""Separate loopback GET boundary. Binds one exact port, serves frozen bytes."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re

from ..situational import safe, digest
from .package import read


def snapshot(config):
    config = json.loads(safe(config).read_bytes())
    if set(config) != {'configVersion', 'path', 'expectedBundleId', 'port', 'strictPort'} or config['configVersion'] != 'broadcast-comparison-config-v1':
        raise ValueError('Explicit comparison config required')
    if config['strictPort'] is not True or type(config['port']) is not int or not 1024 <= config['port'] <= 65535:
        raise ValueError('Strict loopback port required')
    if not re.fullmatch('sha256:[0-9a-f]{64}', config['expectedBundleId']):
        raise ValueError('Exact bundle pin required')
    root = safe(Path(config['path']))
    _, marker = read(root, config['expectedBundleId'])
    # Read once more, verify bytes against the validated pin, then keep immutable bytes.
    payload = (root/'comparison.json').read_bytes()
    if digest(payload) != marker['bundleId']:
        raise ValueError('Package changed after validation')
    return config, payload


def make_server(config, payload):
    port = config['port']
    host = f'127.0.0.1:{port}'
    origin = 'http://'+host

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'

        def handle_request(self):
            allowed = (self.command == 'GET' and self.path == '/__comparison/' and
                       self.headers.get_all('Host') == [host] and
                       self.headers.get_all('X-Local-Comparison') == ['1'] and
                       self.headers.get_all('Origin', []) in ([], [origin]) and
                       self.headers.get_all('Content-Length', []) in ([], ['0']) and
                       not self.headers.get_all('Transfer-Encoding') and not self.headers.get_all('Expect'))
            body = payload if allowed else b'{"error":"TRANSPORT_REFUSED"}\n'
            self.send_response(200 if allowed else 403)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if allowed:
                self.send_header('X-Comparison-Bundle', config['expectedBundleId'])
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_HEAD = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_TRACE = do_CONNECT = handle_request

        def log_message(self, *_args):
            pass

    # No port increment, wildcard bind or fallback. Address conflict raises OSError.
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def serve(config):
    config, payload = snapshot(config)  # Startup fails closed before opening a socket.
    with make_server(config, payload) as server:
        print(json.dumps(dict(url=f"http://127.0.0.1:{config['port']}/__comparison/", bundleId=config['expectedBundleId'], strictPort=True)), flush=True)
        server.serve_forever()
