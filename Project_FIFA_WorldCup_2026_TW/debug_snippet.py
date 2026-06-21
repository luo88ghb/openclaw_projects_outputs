import json
with open('debug_wiki_full.html','r',encoding='utf-8') as f:
    html=f.read()
idx=html.find('class="footballbox')
with open('debug_snippet.json','w',encoding='utf-8') as f:
    json.dump(html[idx:idx+500], f, ensure_ascii=False)
print('written')
