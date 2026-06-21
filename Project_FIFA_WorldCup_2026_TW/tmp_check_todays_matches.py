import json
from datetime import datetime
from pathlib import Path
with open(Path(__file__).resolve().parent / 'data/matches_104.json','r',encoding='utf-8') as f:
    d=json.load(f)
today='2026-06-20'
for m in d['matches']:
    if m['date']==today:
        print(f"M{m['match_id']:3d} {m['time_taiwan']} {m['home_team']} vs {m['away_team']} {m.get('city')} status={m.get('status')}")
