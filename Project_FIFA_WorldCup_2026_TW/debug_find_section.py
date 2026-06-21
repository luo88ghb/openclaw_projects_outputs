from engine.wiki_scraper import fetch_wiki_html
html = fetch_wiki_html()
needle = 'id="A組"'
idx = html.find(needle)
print('idx', idx)
if idx != -1:
    with open('debug_a_section.html','w',encoding='utf-8') as f:
        f.write(html[idx:idx+30000])
    print('written')
else:
    print('not found')
