import codecs

path = r'C:\Users\danny\.openclaw\workspace\Zeni_Engine_v9_Pro.py'
with codecs.open(path, 'r', 'utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'st.session_state.p1 = st.text_area' in line:
        lines[i] = '    st.session_state.p1 = st.text_area("人物原圖背景描述 (圖1背景)", st.session_state.p1, height=100)\n'

with codecs.open(path, 'w', 'utf-8') as f:
    f.writelines(lines)
print("P1 Text updated successfully.")