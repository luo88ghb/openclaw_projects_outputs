import json
with open('data/matches_104.json', encoding='utf-8') as f:
    data = json.load(f)
# 顯示 #30-#35 場次
for m in data['matches']:
    if 30 <= m['match_id'] <= 35:
        print(f"#{m['match_id']:2d} | {m['home_team']} vs {m['away_team']} | {m['date']} {m['time_taiwan']} | {m.get('stage', '')} {m.get('group', '')}")