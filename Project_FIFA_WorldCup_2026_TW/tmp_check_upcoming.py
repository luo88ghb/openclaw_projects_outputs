import json
from datetime import datetime, timedelta

with open('data/matches_104.json', 'r', encoding='utf-8') as f:
    matches = json.load(f)['matches']

# 2026-06-17 16:00 Asia/Taipei
now = datetime(2026, 6, 17, 16, 0)
upcoming = []
for m in matches:
    if m.get('status') == 'finished':
        continue
    dt = datetime.strptime(f"{m['date']} {m['time_taiwan']}", '%Y-%m-%d %H:%M')
    delta = (dt - now).total_seconds() / 60
    if 0 <= delta <= 30:
        upcoming.append((m, delta))

if not upcoming:
    print(f'No matches in the next 30 minutes.')
else:
    for m, delta in upcoming:
        print(f"#{m['match_id']} {m['date']} {m['time_taiwan']} {delta:.1f}min | {m['home_team']} vs {m['away_team']} | {m['stage']}")
