import json
import os

source = r'C:\Users\danny\Downloads\Qwen_Zeni_Ready.json'
target = r'C:\Users\danny\Downloads\Zeni_Pure_Connect_v5.json'

if not os.path.exists(source):
    print(f"Error: Source {source} not found")
    exit(1)

with open(source, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 羅哥要求隱藏的節點清單 (不刪除，只設為 mode: 4)
hide_ids = [206, 208, 199, 213, 212, 229, 228, 232, 231, 230, 203, 116, 247, 82, 173, 243]

# 精確修改
for node in data['nodes']:
    if node['id'] in hide_ids:
        node['mode'] = 4  # 設為忽略
    if node['id'] == 168:
        node['widgets_values'][0] = "High Priority: Preserve facial identity, eyes, and hair from Image 1. Body pose from Image 2. Clothing from Image 1. Beach background from Image 2."

with open(target, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Successfully generated: {target}")
print(f"Node count: {len(data['nodes'])}")
print(f"Link count: {len(data['links'])}")
