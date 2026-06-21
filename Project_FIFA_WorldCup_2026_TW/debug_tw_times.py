import json
from datetime import datetime, timezone, timedelta
TZ={'UTC+3':3,'UTC+2':2,'UTC+1':1,'UTC-3':-3,'UTC-4':-4,'UTC-5':-5,'UTC-6':-6,'UTC-7':-7,'UTC-8':-8,'UTC-9':-9,'UTC+8':8,'UTC+9':9}
def parse_wiki_box(date_str, time_str):
    date_iso = date_str.split('(')[1].split(')')[0]
    import re
    # support unicode minus sign
    m = re.search(r'(\d{1,2}:\d{2})(UTC[\u002b\u2212\-]?\d{1,2})', time_str)
    if not m: return None
    t, tz = m.group(1), m.group(2)
    # normalize sign
    if tz[3] in ('+','-'): sign=tz[3]; val=tz[4:]
    elif tz[3]=='\u2212': sign='-'; val=tz[4:]
    else: return None
    offset = int(sign+val)
    dt = datetime.strptime(f'{date_iso} {t}', '%Y-%m-%d %H:%M')
    dt_utc = dt - timedelta(hours=offset)
    dt_tw = dt_utc.astimezone(timezone(timedelta(hours=8)))
    return dt_tw.strftime('%Y-%m-%d %H:%M')

with open('debug_footballboxes.json','r',encoding='utf-8') as f:
    boxes=json.load(f)
out=[]
for b in boxes:
    tw = parse_wiki_box(b['date'], b['time'])
    b['tw'] = tw
    out.append(b)
with open('debug_tw_times.json','w',encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('written', len(out))
