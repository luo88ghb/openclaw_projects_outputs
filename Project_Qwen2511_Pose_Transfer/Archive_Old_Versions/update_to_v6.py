import json
import os

source = r'C:\Users\danny\Downloads\Qwen_Zeni_Ready.json'
target = r'C:\Users\danny\Downloads\Zeni_Identity_Locked_v6.json'

with open(source, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 繼續忽略冗餘
hide_ids = [206, 208, 199, 213, 212, 229, 228, 232, 231, 230, 203, 116, 247, 82, 173, 243]

for node in data['nodes']:
    if node['id'] in hide_ids:
        node['mode'] = 4
    if node['id'] == 168:
        # 使用權重更高的排他性指令
        node['widgets_values'][0] = "[Identity Lock] MUST keep the EXACT facial identity and facial features from Image 1. REJECT any facial traits from Image 2. Apply ONLY the body pose of Image 2. Retain the floral pattern dress from Image 1. Background: Beach from Image 2."

with open(target, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Iteration V6 successful: {target}")
