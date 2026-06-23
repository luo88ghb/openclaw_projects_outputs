"""
Extended API server for dashboard predictions and auto-update endpoints.
"""
import http.server
import json
import os
import socketserver
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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
        import urllib.parse
        try:
            if self.path.startswith("/api/predictions/"):
                stage = urllib.parse.unquote(self.path.split("/")[-1])
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
            elif self.path == "/api/feedback":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                match_id = query.get("match_id", [None])[0]
                data = load_feedback(match_id)
                self._send_json(data)
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
            elif self.path == "/api/feedback":
                body = self._read_body()
                payload = json.loads(body) if body else {}
                result = save_feedback(payload)
                self._send_json(result, 200 if result.get("ok") else 400)
                return
            self._send_json({"error": "not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


def load_feedback(match_id=None):
    path = DATA_DIR / "user_model_feedback.json"
    if not path.exists():
        return {} if match_id else {"meta": {"schema": "v1"}, "feedback": []}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if match_id is None:
        return data
    # Return mapping model -> feedback for the given match
    out = {}
    for entry in data.get("feedback", []):
        if str(entry.get("match_id")) == str(match_id):
            out[entry.get("model")] = entry.get("feedback")
    return out


def save_feedback(payload):
    path = DATA_DIR / "user_model_feedback.json"
    try:
        match_id = payload.get("match_id")
        model = str(payload.get("model", "")).lower()
        feedback = payload.get("feedback")
        if match_id is None or model not in ("l1", "l2") or feedback is None:
            return {"ok": False, "error": "match_id, model in [l1,l2], feedback required"}
        try:
            feedback = float(feedback)
        except (TypeError, ValueError):
            return {"ok": False, "error": "feedback must be a number"}
        if feedback not in (1.0, 0.5, -0.5, -1.0):
            return {"ok": False, "error": "feedback must be one of 1, 0.5, -0.5, -1"}
        if not path.exists():
            data = {"meta": {"schema": "v1"}, "feedback": []}
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        entries = data.setdefault("feedback", [])
        # remove old entry for same match/model
        entries[:] = [
            e for e in entries
            if not (str(e.get("match_id")) == str(match_id) and str(e.get("model", "")).lower() == model)
        ]
        from datetime import datetime, timezone
        entries.append({
            "match_id": int(match_id),
            "model": model,
            "feedback": feedback,
            "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat()
        })
        data["meta"]["last_updated"] = entries[-1]["timestamp"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"ok": True, "match_id": int(match_id), "model": model, "feedback": feedback}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run():
    os.chdir(BASE_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), APIHandler) as httpd:
        print(f"World Cup 2026 API running at http://localhost:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    run()
