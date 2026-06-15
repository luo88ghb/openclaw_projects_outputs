import codecs

path = r'C:\Users\danny\.openclaw\workspace\Zeni_Engine_v9_Pro.py'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

text = text.replace('人物原圖背景描述 (图1背景)', '人物原圖背景描述 (圖1背景)')
text = text.replace('st.session_state.p1 = st.text_area("人物原圖背景描述 (图1背景)", st.session_state.p1, height=100)', 'st.session_state.p1 = st.text_area("人物原圖背景描述 (圖1背景)", st.session_state.p1, height=100)')

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)
print("UI Text updated successfully.")