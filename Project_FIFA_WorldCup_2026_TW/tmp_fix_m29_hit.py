import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Fix M29: actual result USA 2-0 Australia; prediction was 1-1 (draw, wrong winner)
# Telegram previously claimed +1.0 because it was checking winner only incorrectly.
# The source of truth is this JSON; set hit to false (scoreline did not match).
for m in data["matches"]:
    if m["match_id"] == 29:
        m["hit"] = False

with open(DATA_DIR / "matches_104.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("M29 hit set to False in matches_104.json")
