import json, sys
d=json.load(open('debug_not_found.json', encoding='utf-8'))
for b in d:
    sys.stdout.buffer.write((str(b)+'\n').encode('utf-8'))
