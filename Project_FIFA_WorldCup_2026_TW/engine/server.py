"""
HTTP + SSE server for World Cup 2026 dashboard.
Serves dashboard/ and data/ directories, plus an SSE endpoint
for the scheduler to push live updates to browsers.
"""
import http.server
import socketserver
import os
import signal
import sys
import threading
import time
import urllib.parse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
DATA_DIR = BASE_DIR / "data"
PORT = 8765

# Shared event to wake SSE clients
_update_event = threading.Event()
_update_payload = "reload"
_httpd_instance = None


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

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/update-stream":
            self._serve_sse()
            return
        if parsed.path == "/notify-update":
            self._notify_update()
            return
        if parsed.path == "/api/status":
            self._serve_status()
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/notify-update":
            self._notify_update()
            return
        if parsed.path == "/api/shutdown":
            self._shutdown()
            return
        self.send_response(404)
        self.end_headers()

    def _serve_status(self):
        status = {
            "running": True,
            "port": PORT,
            "version": "v2.2.7",
            "pid": os.getpid(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        body = json.dumps(status, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _shutdown(self):
        global _httpd_instance
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(b"Server is shutting down...")
            self.wfile.flush()
        except Exception:
            pass
        # Trigger shutdown in a background thread so the response is sent first
        def _stop():
            time.sleep(0.3)
            try:
                if _httpd_instance is not None:
                    _httpd_instance.shutdown_requested = True
                    _httpd_instance.shutdown()
            except Exception as e:
                print(f"shutdown via httpd error: {e}", flush=True)
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception as e:
                print(f"shutdown via SIGTERM error: {e}", flush=True)
        threading.Thread(target=_stop, daemon=True).start()
        # Also stop the current handler's server_forever loop from inside if possible
        try:
            self.server.shutdown()
        except Exception:
            pass

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Send initial event
        self.wfile.write(b"event: connected\ndata: connected\n\n")
        self.wfile.flush()

        while True:
            # Wait for scheduler ping or 30s keepalive
            triggered = _update_event.wait(timeout=30)
            if triggered:
                payload = _update_payload
                _update_event.clear()
                try:
                    self.wfile.write(f"event: update\ndata: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except BrokenPipeError:
                    break
            else:
                # keepalive
                try:
                    self.wfile.write(b":keepalive\n\n")
                    self.wfile.flush()
                except BrokenPipeError:
                    break

    def _notify_update(self):
        global _update_payload
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        _update_payload = query.get("payload", ["reload"])[0]
        _update_event.set()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/notify-update":
            self._notify_update()
            return
        self.send_response(404)
        self.end_headers()

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
    global _httpd_instance
    os.chdir(BASE_DIR)
    kill_existing_server(PORT)
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        _httpd_instance = httpd
        print(f"World Cup 2026 Dashboard running at http://localhost:{PORT}/index.html", flush=True)
        print(f"SSE update stream at http://localhost:{PORT}/update-stream", flush=True)
        print(f"API status at http://localhost:{PORT}/api/status", flush=True)
        print(f"Shutdown via POST http://localhost:{PORT}/api/shutdown", flush=True)
        sys.stdout.flush()
        httpd.shutdown_requested = False
        try:
            httpd.serve_forever()
        except OSError:
            if not getattr(httpd, 'shutdown_requested', False):
                raise
        finally:
            _httpd_instance = None


if __name__ == "__main__":
    run()
