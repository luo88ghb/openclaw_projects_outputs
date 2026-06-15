import codecs
import re

path = r'C:\Users\danny\.openclaw\workspace\Zeni_Engine_v9_Pro.py'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

text = text.replace('人物原圖背景描述 (图1背景)', '人物原圖背景描述 (圖1背景)')
text = text.replace('目標背景描述 (图2背景)', '目標背景描述 (增添修改)')

# Replace the specific block of p3 text
old_p3 = '图2背景为柔和的橄榄绿色调，墙面平整无纹理，营造出简约而宁静的视觉空间。光线均匀柔和，无明显阴影或强烈反差，凸显出整体环境的沉静与高级感。色调统一，无杂乱元素，突出主体人物的视觉焦点，同时赋予画面一种现代、克制的时尚氛围。整体背景设计服务于主题表达，无多余装饰，强调纯净与高级质感。'
text = text.replace(old_p3, '')

text = re.sub(r'st\.session_state\.p1 = st\.text_area\("人物原圖背景描述 \(图1背景\)", st\.session_state\.p1, height=100\)', 'st.session_state.p1 = st.text_area("人物原圖背景描述 (圖1背景)", st.session_state.p1, height=100)', text)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)
print("UI Text updated successfully.")