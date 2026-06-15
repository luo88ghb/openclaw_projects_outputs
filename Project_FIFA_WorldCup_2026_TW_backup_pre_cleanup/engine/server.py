"""
Simple HTTP server for World Cup 2026 dashboard.
Serves dashboard/ and data/ directories.
"""
import http.server
import socketserver
import os
import signal
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
DATA_DIR = BASE_DIR / "data"
PORT = 8765


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def translate_path(self, path):
        # Map /data/* and /predictions/* to project root subdirs
        rel = path.lstrip('/')
        if rel.startswith('data/'):
            target = DATA_DIR / rel[len('data/'):]
            if target.exists():
                return str(target)
        if rel.startswith('predictions/'):
            predictions_dir = BASE_DIR / "predictions"
            target = predictions_dir / rel[len('predictions/'):]
            if target.exists():
                return str(target)
        return super().translate_path(path)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        # Suppress verbose logs; keep startup line in run()
        pass


def kill_existing_server(port=PORT):
    """Terminate any process already listening on the target port."""
    try:
        import psutil
    except ImportError:
        psutil = None

    if psutil is None:
        return

    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            try:
                os.kill(conn.pid, signal.SIGTERM)
            except Exception:
                pass


def run():
    os.chdir(BASE_DIR)
    kill_existing_server(PORT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"World Cup 2026 Dashboard running at http://localhost:{PORT}/index.html", flush=True)
        sys.stdout.flush()
        httpd.serve_forever()


if __name__ == "__main__":
    run()
