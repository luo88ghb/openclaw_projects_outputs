import json, re
from pathlib import Path
text = Path('kickoffclock.txt').read_text(encoding='utf-8')
m = re.search(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', text, re.DOTALL)
raw = json.loads(m.group(1).replace('"$undefined"', 'null'))
print('matches', len(raw))
for r in raw[:5]:
    print(r)
