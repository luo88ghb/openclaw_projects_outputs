import json
with open('debug_footballboxes.json','r',encoding='utf-8') as f:
    boxes=json.load(f)
with open('debug_first_boxes.json','w',encoding='utf-8') as f:
    json.dump(boxes[:5], f, ensure_ascii=False, indent=2)
print('written')
