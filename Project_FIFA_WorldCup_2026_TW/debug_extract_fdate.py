from engine.wiki_scraper import fetch_wiki_html
from bs4 import BeautifulSoup
import json
html = fetch_wiki_html()
soup = BeautifulSoup(html, 'html.parser')
boxes = soup.find_all('div', class_='footballbox')
results=[]
for i, box in enumerate(boxes, 1):
    fdate = box.find('div', class_='fdate')
    ftime = box.find('div', class_='ftime')
    fhome = box.find('th', class_='fhome')
    faway = box.find('th', class_='faway')
    fscore = box.find('th', class_='fscore')
    date = fdate.get_text(strip=True) if fdate else ''
    time_ = ftime.get_text(strip=True) if ftime else ''
    home = fhome.get_text(strip=True) if fhome else ''
    away = faway.get_text(strip=True) if faway else ''
    score = fscore.get_text(strip=True) if fscore else ''
    results.append({'i':i,'date':date,'time':time_,'home':home,'score':score,'away':away})
with open('debug_footballboxes.json','w',encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('written', len(results))
