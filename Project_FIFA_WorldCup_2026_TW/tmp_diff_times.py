import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

with open(DATA_DIR / "matches_104.json.bak_wiki_times", "r", encoding="utf-8") as f:
    old = json.load(f)["matches"]
with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
    new = json.load(f)["matches"]

for o, n in zip(old, new):
    if o["date"] != n["date"] or o["time_taiwan"] != n["time_taiwan"]:
        print(f"#{o['match_id']} {o['date']} {o['time_taiwan']} -> {n['date']} {n['time_taiwan']}  ({n['home_team']} vs {n['away_team']})")

print("\nTotal old matches:", len(old))
print("Total new matches:", len(new))
