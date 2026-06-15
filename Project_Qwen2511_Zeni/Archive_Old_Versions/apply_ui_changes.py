import codecs

path = r'C:\Users\danny\.openclaw\workspace\Zeni_Engine_v9_Pro.py'

with codecs.open(path, 'r', 'utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Update p1 label
    if 'st.session_state.p1 = st.text_area' in line:
        lines[i] = '    st.session_state.p1 = st.text_area("人物原圖背景描述 (圖1背景)", st.session_state.p1, height=100)\n'
    
    # Update p3 label
    if 'st.session_state.p3 = st.text_area' in line:
        lines[i] = '    st.session_state.p3 = st.text_area("目標背景描述 (增添修改)", st.session_state.p3, height=100)\n'
        
    # Clear p3 default prompt text
    if '"p3":' in line and '图2背景为' in line:
        lines[i] = '    "p3": ""\n'

with codecs.open(path, 'w', 'utf-8') as f:
    f.writelines(lines)

print("UI labels and default texts updated.")