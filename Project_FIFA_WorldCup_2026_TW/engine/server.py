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
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
DATA_DIR = BASE_DIR / "data"
PORT = 8765

# Shared event to wake SSE clients
_update_event = threading.Event()
_update_payload = "reload"
_httpd_instance = None


class EloProvider:
    """
    Provides team Elo ratings sourced from data/elo_ratings.json
    (fetched from worldcupelo.com).  Falls back to a static snapshot
    if the ratings file is missing.
    """

    # Static fallback snapshot from worldcupelo.com (June 2026)
    _FALLBACK = {
        "西班牙": 2171, "阿根廷": 2113, "法國": 2063, "英格蘭": 2042,
        "哥倫比亞": 1998, "巴西": 1979, "葡萄牙": 1976, "荷蘭": 1959,
        "克羅埃西亞": 1933, "厄瓜多": 1933, "挪威": 1922, "德國": 1910,
        "瑞士": 1897, "烏拉圭": 1890, "土耳其": 1880, "日本": 1879,
        "塞內加爾": 1869, "丹麥": 1864, "義大利": 1859, "比利時": 1849,
        "墨西哥": 1834, "巴拉圭": 1833, "奧地利": 1818, "摩洛哥": 1806,
        "加拿大": 1806, "烏克蘭": 1802, "蘇格蘭": 1790, "南韓": 1784,
        "俄羅斯": 1782, "澳大利亞": 1774, "塞爾維亞": 1769, "希臘": 1761,
        "伊朗": 1754, "美國": 1747, "巴拿馬": 1743, "奈及利亞": 1739,
        "波蘭": 1735, "烏茲別克": 1735, "捷克": 1731, "智利": 1731,
        "阿爾及利亞": 1728, "威爾斯": 1715, "委內瑞拉": 1715, "科索沃": 1714,
        "秘魯": 1708, "匈牙利": 1698, "斯洛維尼亞": 1695, "約旦": 1691,
        "愛爾蘭": 1688, "斯洛伐克": 1687, "玻利維亞": 1665, "阿爾巴尼亞": 1664,
        "瑞典": 1660, "埃及": 1660, "喬治亞": 1650, "羅馬尼亞": 1642,
        "剛果民主共和國": 1639, "象牙海岸": 1637, "哥斯大黎加": 1632,
        "以色列": 1631, "突尼西亞": 1614, "喀麥隆": 1606, "北愛爾蘭": 1602,
        "北馬其頓": 1592, "沙烏地阿拉伯": 1592, "馬利": 1589, "紐西蘭": 1586,
        "伊拉克": 1583, "波士尼亞與赫塞哥維納": 1571, "宏都拉斯": 1567,
        "冰島": 1566, "芬蘭": 1558, "奈及利亞": 1555, "迦納": 1550,
        "委內瑞拉": 1546
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _load_json_file(self, name):
        path = self.data_dir / name
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _normalize(self, name):
        return re.sub(r"\s+", "", name.strip().lower())

    def get_ratings(self):
        # 1. 嘗試載入 data/elo_ratings.json
        data = self._load_json_file("elo_ratings.json")
        if isinstance(data, dict) and data:
            return data
        # 2. 嘗試用 teams.json 中的 name_zh 索引 fallback
        teams = self._load_json_file("teams.json")
        result = {}
        for team in teams.get("teams", []):
            name = team.get("name_zh")
            if not name:
                continue
            for alias, rating in self._FALLBACK.items():
                if self._normalize(name) == self._normalize(alias):
                    result[name] = rating
                    break
        return result

    def get_rating(self, team_name):
        ratings = self.get_ratings()
        for key, value in ratings.items():
            if self._normalize(key) == self._normalize(team_name):
                return value
        # alias mapping for common Chinese names
        alias_map = {
            "澳洲": "澳大利亞",
            "美國": "美國",
            "捷克共和國": "捷克",
            "沙烏地阿拉伯": "沙烏地阿拉伯",
            "伊朗伊斯蘭共和國": "伊朗",
            "古拉索": "庫拉索",
            "南韓": "韓國",
        }
        mapped = alias_map.get(team_name, team_name)
        for key, value in ratings.items():
            if self._normalize(key) == self._normalize(mapped):
                return value
        return None


ELLO_PROVIDER = EloProvider(DATA_DIR)


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
        if parsed.path == "/api/elo_ratings":
            content = json.dumps(ELLO_PROVIDER.get_ratings(), ensure_ascii=False, indent=2)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            body = content.encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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
        if parsed.path == "/api/shutdown":
            self._shutdown()
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
