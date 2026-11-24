#!/usr/bin/env python3
"""Serve one internal inspection HTML on loopback, without exposing adjacent artifacts."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('page', type=Path)
parser.add_argument('--port', type=int, default=18082)
args = parser.parse_args()
page = args.page.resolve(strict=True)
assert page.suffix == '.html' and 'editorial' in page.parts
content = page.read_bytes()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/', '/inspection.html'):
            self.send_error(404)
            return
        data = content
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)


server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
print('INSPECTION_READY http://127.0.0.1:' + str(server.server_port), flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
