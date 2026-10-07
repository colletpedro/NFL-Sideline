#!/usr/bin/env python3
"""E4-only loopback fault harness. No retries, no external destinations.

Run the owned Java server on 18085 and this harness on the free 18081.
Control file contains normal, delay, or drop-once. Logs stay in the run directory.
Never run this in place of another task's API.
"""
import argparse
import http.client
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    run = args.run_directory.resolve(strict=True)
    if 'public' in run.parts:
        parser.error('Use a private evaluation directory')
    control = run / 'transport-mode.txt'
    log = run / 'transport.jsonl'
    if not control.exists():
        control.write_text('normal\n')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            self.forward()

        def do_POST(self):
            self.forward()

        def forward(self):
            # Keep the local API boundary: the Vite proxy removes Origin only
            # after checking the browser request. The fault harness must not
            # make cross-origin or body-bearing requests acceptable instead.
            if self.headers.get('Host') != '127.0.0.1:18081' or self.headers.get('Origin') is not None:
                self.send_error(403)
                return
            lengths = self.headers.get_all('Content-Length', [])
            if self.headers.get('Transfer-Encoding') is not None or len(lengths) > 1 or lengths and lengths[0] != '0':
                self.send_error(400)
                return
            if not re.fullmatch(r'/api/v1/local-analysis/(?:[A-Za-z0-9_/-]*)', self.path):
                self.send_error(400)
                return
            mode = control.read_text().strip()
            connection = http.client.HTTPConnection('127.0.0.1', 18085, timeout=15)
            event = {'method': self.command, 'path': self.path, 'mode': mode}
            try:
                connection.request(self.command, self.path)
                response = connection.getresponse()
                body = response.read()
                event['backendStatus'] = response.status
                if self.command == 'POST' and mode == 'delay':
                    time.sleep(2)  # deterministic race window; never a human reading time
                if self.command == 'POST' and mode == 'drop-once' and response.status == 201:
                    control.write_text('normal\n')
                    event['responseDropped'] = True
                    self.close_connection = True
                    return
                self.send_response(response.status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                event['backendUnavailable'] = True
                try:
                    body = b'{"error":"LOCAL_API_UNAVAILABLE"}'
                    self.send_response(503)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except OSError:
                    pass
            finally:
                connection.close()
                with log.open('a') as output:
                    output.write(json.dumps(event) + '\n')

    server = ThreadingHTTPServer(('127.0.0.1', 18081), Handler)
    print('E4_TRANSPORT_READY 127.0.0.1:18081 -> 127.0.0.1:18085', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
