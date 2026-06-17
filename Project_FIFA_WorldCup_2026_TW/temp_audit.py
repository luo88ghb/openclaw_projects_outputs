import json
d=json.load(open('data/matches_104.json','r',encoding='utf-8'))
for m in d['matches']:
    if '附加賽勝者' in m['home_team'] or '附加賽勝者' in m['away_team'] or (m['match_id']<=20 and m['status']=='finished'):
        print(f"{m['match_id']:3d} | {m['date']} | {m['group'] or '-'} | {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']} | {m['status']}")
