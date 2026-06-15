import codecs
import re

path = r'C:\Users\danny\.openclaw\workspace\Zeni_Engine_v9_Pro.py'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

text = text.replace('人物原圖背景描述 (图1背景)', '人物原圖背景描述 (圖1背景)')
text = text.replace('目標背景描述 (图2背景)', '目標背景描述 (增添修改)')

# Replace p3 default text using regex to match the exact key-value pair safely
text = re.sub(r'"p3":\s*"[^"]+"', '"p3": ""', text)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)
print("UI Text updated successfully.")
