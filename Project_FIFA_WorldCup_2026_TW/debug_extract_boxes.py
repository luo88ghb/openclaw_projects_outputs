import re, json
from bs4 import BeautifulSoup

with open('debug_wiki_full.html','r',encoding='utf-8') as f:
    html=f.read()

soup=BeautifulSoup(html,'html.parser')
tables=soup.find_all('table', class_='footballbox')
print('bs4 footballbox tables', len(tables))
# Try outer <div class="footballbox">
divs=soup.find_all('div', class_='footballbox')
print('bs4 footballbox divs', len(divs))
boxes=[]
for i,d in enumerate(divs):
    fdate=d.find('div', class_='fdate')
    ftime=d.find('div', class_='ftime')
    fhome=d.find('th', class_='fhome')
    faway=d.find('th', class_='faway')
    fscore=d.find('th', class_='fscore')
    if not (fdate and ftime and fhome and faway and fscore):
        print('skip', i, bool(fdate), bool(ftime), bool(fhome), bool(faway), bool(fscore))
        continue
    date=fdate.get_text(strip=True)
    time=ftime.get_text(strip=True)
    home=fhome.get_text(strip=True)
    away=faway.get_text(strip=True)
    score=fscore.get_text(strip=True)
    boxes.append({'i':i,'date':date,'time':time,'home':home,'away':away,'score':score})
with open('debug_footballboxes.json','w',encoding='utf-8') as f:
    json.dump(boxes, f, ensure_ascii=False, indent=2)
print('boxes', len(boxes))
