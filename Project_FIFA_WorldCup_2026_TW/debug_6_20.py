from engine.wiki_scraper import fetch_wiki_html
import re
html = fetch_wiki_html()
idx = html.find('6月20日')
chunk = html[idx:idx+20000]
# Find all footballbox divs in this section
boxes = re.split(r'<div itemscope="" itemtype="http&#58;//schema.org/SportsEvent" class="footballbox">', chunk)
print('boxes', len(boxes))
for b in boxes[:10]:
    t = re.search(r'<div class="ftime">(\d{2}:\d{2})\s*<a href="/wiki/UTC[^"]+"[^>]*>([^<]+)</a>', b)
    home = re.search(r'<th class="fhome"[^>]*>.*?>([^<]+)</a>', b, re.S)
    away = re.search(r'<th class="faway"[^>]*>.*?>([^<]+)</a>', b, re.S)
    teams = []
    if home:
        teams.append(home.group(1).strip())
    if away:
        teams.append(away.group(1).strip())
    print('time', t.groups() if t else None, 'teams', teams)
