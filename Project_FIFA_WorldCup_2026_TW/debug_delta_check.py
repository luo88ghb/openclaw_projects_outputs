import json
from datetime import datetime
with open('debug_tw_times.json','r',encoding='utf-8') as f:
    boxes=json.load(f)
with open('data/matches_104.json','r',encoding='utf-8') as f:
    data=json.load(f)
def parse_tw(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M')
for b in boxes:
    if b.get('match_id') and b.get('tw'):
        wiki=parse_tw(b['tw'])
        db=datetime.strptime(f"{b['current_date']} {b['current_time_taiwan']}", '%Y-%m-%d %H:%M')
        delta_hours=(db-wiki).total_seconds()/3600
        if delta_hours not in (0,8):
            print('odd delta', b['match_id'], delta_hours)
