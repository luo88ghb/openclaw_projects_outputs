"""Smoke test for the local World Cup dashboard server."""
import json
import urllib.request

URL = "http://localhost:8765/data/matches_104.json"

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=10) as resp:
    payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("matches", payload)
    print("matches count", len(data))
    print("finished", sum(1 for m in data if m.get("status") == "finished"))
    print("first 3 matches:")
    for m in data[:3]:
        print(m["match_id"], m["date"], m["time_taiwan"], m["home_team"], m.get("home_score"), "-", m.get("away_score"), m["away_team"], m.get("status"))
