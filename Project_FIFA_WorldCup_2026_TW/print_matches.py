import json, sys
n = int(sys.argv[2]) if len(sys.argv) > 2 else 999
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
for m in data['matches'][:n]:
    print(f"{m['match_id']:>3} {m['date']} {m['time_taiwan']} {m['home_team']} vs {m['away_team']}")
