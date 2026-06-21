import json
with open('data/matches_104.json','r',encoding='utf-8') as f:
    data=json.load(f)
for m in data['matches']:
    if m['match_id']==29:
        print(json.dumps(m, ensure_ascii=False, indent=2))
