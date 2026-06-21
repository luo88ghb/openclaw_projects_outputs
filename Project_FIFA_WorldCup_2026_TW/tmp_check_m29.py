import json, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
with open(BASE / 'data/matches_104.json','r',encoding='utf-8') as f:
    d=json.load(f)
mids={29,32,40}
for m in d['matches']:
    if m['match_id'] in mids:
        print(f"M{m['match_id']} {m['date']} {m['time_taiwan']} home={m['home_team']} away={m['away_team']} status={m.get('status')} home_score={m.get('home_score')} away_score={m.get('away_score')} hit={m.get('hit')}")
        pred=m.get('prediction')
        if pred:
            print('  pred:', pred)
