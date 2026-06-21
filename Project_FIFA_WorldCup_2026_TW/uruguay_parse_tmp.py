import json
import re
from pathlib import Path

text = Path('uruguay.txt').read_text(encoding='utf-8')
m = re.search(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', text, re.DOTALL)
raw = json.loads(m.group(1).replace('"$undefined"', 'null'))
for r in raw:
    if r['teamA'] != 'TBD' and r['teamB'] != 'TBD':
        print(r['date'], r['teamA'], 'vs', r['teamB'])
