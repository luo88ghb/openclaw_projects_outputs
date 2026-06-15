import codecs
import re

path = r'C:\Users\danny\.openclaw\workspace\Zeni_Engine_v9_Pro.py'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

text = re.sub(r'st\.session_state\.p1 = st\.text_area\(.*?\)', 'st.session_state.p1 = st.text_area("人物原圖背景描述 (圖1背景)", st.session_state.p1, height=100)', text)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)
print("UI Text updated successfully.")