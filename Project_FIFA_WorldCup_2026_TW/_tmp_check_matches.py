import json, sys
with open('data/matches_104.json','r',encoding='utf-8') as f:
    data=json.load(f)
for m in data['matches'][:16]:
    parts=[str(m['match_id']),m['date'],m['time_taiwan'],m.get('group','') or '-',m['home_team'],str(m.get('home_score','null'))+':'+str(m.get('away_score','null')),m['away_team'],'status='+m.get('status','')]
    sys.stdout.buffer.write((' '.join(parts)+'\n').encode('utf-8'))
