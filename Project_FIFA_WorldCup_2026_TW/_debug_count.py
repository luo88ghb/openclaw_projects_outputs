from pathlib import Path
import re
text = Path('kickoffclock.txt').read_text(encoding='utf-8')
for needle in ['Türkiye','Curaçao','Turkey','Curacao']:
    print(needle.encode('utf-8'), text.count(needle))
