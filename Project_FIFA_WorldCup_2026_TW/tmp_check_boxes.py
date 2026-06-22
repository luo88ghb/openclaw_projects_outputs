import json, sys
boxes=json.load(open('debug_footballboxes.json', encoding='utf-8'))
for b in boxes:
    if b['i'] in (73,74,75):
        sys.stdout.buffer.write(('i='+str(b['i'])+' '+b['date']+' '+repr(b['time'])+' '+b['home']+' vs '+b['away']+'\n').encode('utf-8'))
