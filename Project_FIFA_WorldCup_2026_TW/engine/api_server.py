"""
Extended API server for dashboard predictions and auto-update endpoints.
"""
import http.server
import json
import os
import socketserver
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"
PORT = 8766


class APIHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8")

    def do_GET(self):
        try:
            if self.path.startswith("/api/predictions/"):
                stage = self.path.split("/")[-1]
                path = PREDICTIONS_DIR / "predictions_db.json"
                if not path.exists():
                    self._send_json({"error": "no predictions db"}, 404)
                    return
                with open(path, "r", encoding="utf-8") as f:
                    db = json.load(f)
                result = db.get("stage_predictions", {}).get(stage, {})
                self._send_json({"stage": stage, "data": result})
                return
            elif self.path == "/api/teams":
                with open(DATA_DIR / "teams.json", "r", encoding="utf-8") as f:
                    self._send_json(json.load(f))
                return
            elif self.path == "/api/matches":
                with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
                    self._send_json(json.load(f))
                return
            self._send_json({"error": "not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        try:
            if self.path == "/api/update":
                # Run auto_update.py in background
                script = BASE_DIR / "engine" / "auto_update.py"
                subprocess.Popen([sys.executable, str(script)], cwd=str(BASE_DIR))
                self._send_json({"status": "update triggered"})
                return
            elif self.path.startswith("/api/predict_match/"):
                match_id = int(self.path.split("/")[-1])
                from worldcup_engine import WorldCupEngine
                engine = WorldCupEngine()
                pred = engine.predict_match(match_id)
                self._send_json(pred)
                return
            self._send_json({"error": "not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


def run():
    os.chdir(BASE_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), APIHandler) as httpd:
        print(f"World Cup 2026 API running at http://localhost:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    run()
