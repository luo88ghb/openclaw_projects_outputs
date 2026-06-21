import json
from pathlib import Path
import re
text = Path('kickoffclock.txt').read_text(encoding='utf-8')
m = re.search(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', text, re.DOTALL)
raw = json.loads(m.group(1).replace('"$undefined"', 'null'))
for r in raw:
    if 'Turkey' in (r['teamA'],r['teamB']) or 'Curacao' in (r['teamA'],r['teamB']):
        print(r)
