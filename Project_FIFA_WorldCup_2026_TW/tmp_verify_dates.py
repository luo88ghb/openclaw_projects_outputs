import json
from pathlib import Path
with open(Path(__file__).resolve().parent / 'data/matches_104.json','r',encoding='utf-8') as f:
    d=json.load(f)
for m in d['matches'][:12]:
    print(f"M{m['match_id']:3d} {m['date']} {m['time_taiwan']} {m['home_team']} vs {m['away_team']} {m.get('city')}")
