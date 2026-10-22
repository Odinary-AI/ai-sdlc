#!/usr/bin/env python3
"""Serve an explicitly selected, immutable guide snapshot on loopback only."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import signal
import time
from urllib.parse import quote


TYPES = {
    '.html': 'text/html; charset=utf-8', '.htm': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
    '.txt': 'text/plain; charset=utf-8', '.md': 'text/plain; charset=utf-8',
}
MAX_BYTES = 32 * 1024 * 1024


def snapshot(root, paths):
    """Read only named regular files; requests never resolve filesystem paths."""
    result = {}
    total = 0
    for name in paths:
        path = Path(name)
        if (path.is_absolute() or not path.parts or '..' in path.parts
                or any(part.startswith('.') for part in path.parts)
                or path.suffix.lower() not in TYPES):
            raise ValueError('只允许根内显式静态文件，不接受隐藏路径、目录或越界')
        cursor = root
        for part in path.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError('不接受符号链接或其子路径')
        if not cursor.resolve().is_relative_to(root) or not cursor.is_file():
            raise ValueError('预览文件不存在或越界')
        key = quote(path.as_posix(), safe='/')
        if key in result:
            continue
        with cursor.open('rb') as stream:
            body = stream.read(MAX_BYTES - total + 1)
        total += len(body)
        if total > MAX_BYTES:
            raise ValueError('预览快照总大小超过32 MiB；缩小所选资源范围')
        result[key] = (body, TYPES[path.suffix.lower()], hashlib.sha256(body).hexdigest())
    return result


def make_server(files, page):
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'GuidePreview'

        def log_message(self, *args):
            pass  # Do not log capability URLs or request-controlled data.

        def do_GET(self):
            origin = 'http://' + self.server.authority
            if (self.headers.get('Host') != self.server.authority
                    or self.headers.get('Origin') not in (None, origin)
                    or self.headers.get('Sec-Fetch-Site') == 'cross-site'):
                self.send_error(403)
                return
            prefix = '/' + token + '/'
            # Exact URL matching rejects traversal, alternate encodings and queries.
            key = self.path[len(prefix):] if self.path.startswith(prefix) else None
            if key not in files:
                self.send_error(404)
                return
            body, content_type, digest = files[key]
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; script-src 'self' 'unsafe-inline'; "
                             "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                             "font-src 'self'; connect-src 'none'; frame-ancestors 'none'; "
                             "base-uri 'none'; form-action 'none'")
            self.send_header('ETag', '"' + digest + '"')
            self.end_headers()
            self.wfile.write(body)

    class Server(HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(1)
            return connection, address

    server = Server(('127.0.0.1', 0), Handler)
    server.timeout = 0.2
    server.authority = '127.0.0.1:' + str(server.server_port)
    server.preview_url = 'http://' + server.authority + '/' + token + '/' + quote(Path(page).as_posix(), safe='/')
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--page', required=True, help='根内HTML相对路径；只服务明确选择的文件')
    parser.add_argument('--asset', action='append', default=[], help='必要静态资源相对路径，可重复；不递归发现')
    parser.add_argument('--seconds', type=int, default=600, help='自动退出期限，1–3600秒，默认600')
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 3600 or Path(args.page).suffix.lower() not in ('.html', '.htm'):
        raise ValueError('page必须为HTML，seconds须在1–3600之间')
    files = snapshot(args.root.resolve(), [args.page, *args.asset])
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        with make_server(files, args.page) as server:
            print(json.dumps({'url': server.preview_url, 'expires_in_seconds': args.seconds,
                              'files': {key: {'sha256': value[2], 'bytes': len(value[0])}
                                        for key, value in files.items()}}, ensure_ascii=False), flush=True)
            deadline = time.monotonic() + args.seconds
            while not stopped and time.monotonic() < deadline:
                server.handle_request()
        print(json.dumps({'status': 'stopped'}), flush=True)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc))
