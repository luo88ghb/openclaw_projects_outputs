import json, re
from pathlib import Path
text = Path('kickoffclock_saudi-arabia.txt').read_text(encoding='utf-8')
m = re.search(r'"countryMatches":(\[\{.*?\}\])', text, re.DOTALL)
print('found', bool(m))
if m:
    data = json.loads(m.group(1).replace('"$undefined"', 'null'))
    for x in data:
        print(x)
