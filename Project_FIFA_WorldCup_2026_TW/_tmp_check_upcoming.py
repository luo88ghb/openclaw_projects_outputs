import json
from datetime import datetime
with open('data/matches_104.json','r',encoding='utf-8') as f:
    matches=json.load(f)['matches']
now=datetime(2026,6,16,20,0)
up=[]
for m in matches:
    if m.get('status')=='finished':
        continue
    dt=datetime.strptime(f"{m['date']} {m['time_taiwan']}",'%Y-%m-%d %H:%M')
    delta=(dt-now).total_seconds()/60
    if 0<=delta<=30:
        up.append((m,delta))
print('即將開賽:',len(up))
for m,d in up:
    print(f"{m['match_id']} {m['date']} {m['time_taiwan']} {m['home_team']} vs {m['away_team']} {m['stage']} {m.get('group','')} 還剩{int(d)}分")
