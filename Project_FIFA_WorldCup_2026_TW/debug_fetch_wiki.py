import urllib.request
url='https://zh.wikipedia.org/zh-tw/2026%E5%B9%B4%E5%9C%8B%E9%9A%9B%E8%B6%B3%E5%8D%94%E4%B8%96%E7%95%8C%E7%9B%83'
req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
html=urllib.request.urlopen(req).read().decode('utf-8')
with open('debug_wiki_full.html','w',encoding='utf-8') as f:
    f.write(html)
print('saved', len(html))
