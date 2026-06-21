import json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

text = Path('kickoffclock_uruguay.txt').read_text(encoding='utf-8')
m = re.search(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', text, re.DOTALL)
raw = json.loads(m.group(1).replace('"$undefined"', 'null'))
for r in raw:
    if any(x in [r['teamA'], r['teamB']] for x in ['Uruguay','Saudi Arabia','Iran','New Zealand']):
        dt = datetime.strptime(r['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        print(r['teamA'], 'v', r['teamB'], 'UTC', r['date'], 'TPE', dt.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M'))
