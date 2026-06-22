import json
from datetime import datetime

with open('data/matches_104.json','r',encoding='utf-8') as f:
    data=json.load(f)

print('Total matches:', len(data['matches']))
samples = [m for m in data['matches'] if m['match_id'] in [27,32,36,73,75,82,97]]
for m in samples:
    dt = datetime.strptime(f"{m['date']} {m['time_taiwan']}", '%Y-%m-%d %H:%M')
    print(f"#{m['match_id']} {m['date']} {m['time_taiwan']} {m['home_team']} vs {m['away_team']} {m['city']}")
