import json
with open('debug_tw_times.json','r',encoding='utf-8') as f:
    boxes=json.load(f)
diffs=[]
for b in boxes:
    mid=b.get('match_id')
    if mid is not None and b.get('tw') and b.get('current_time_taiwan') and b['tw'][11:16]!=b['current_time_taiwan']:
        diffs.append({'match_id':mid, 'wiki_date':b['date'], 'wiki_time':b['time'], 'wiki_tw':b['tw'], 'db_date':b['current_date'], 'db_time':b['current_time_taiwan'], 'home':b['home'], 'away':b['away']})
with open('debug_diffs.json','w',encoding='utf-8') as f:
    json.dump(diffs, f, ensure_ascii=False, indent=2)
print('diffs', len(diffs))
