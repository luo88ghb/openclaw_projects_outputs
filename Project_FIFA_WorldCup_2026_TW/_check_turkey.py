import json, re
from pathlib import Path
text = Path('kickoffclock.txt').read_text(encoding='utf-8')
m = re.search(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', text, re.DOTALL)
raw = json.loads(m.group(1).replace('"$undefined"', 'null'))
for r in raw:
    if 'Turkey' in (r.get('teamA',''), r.get('teamB','')) or 'Türkiye' in (r.get('teamA',''), r.get('teamB','')):
        print(r)
