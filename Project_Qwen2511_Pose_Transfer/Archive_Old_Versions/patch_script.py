import sys, os

file_path = r'C:\Users\danny\.openclaw\workspace\Zeni_Engine_v9_Pro.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

part1_old = '''    # 將清晰原圖貼到正中間
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    bg_img.paste(img_resized, (paste_x, paste_y))
    
    return bg_img

# --- 3. ComfyUI 網路工具函數 ---'''

part1_new = '''    # 將清晰原圖貼到正中間
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    bg_img.paste(img_resized, (paste_x, paste_y))
    
    return bg_img

def analyze_image_features(image_bytes):
    import base64
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
         return "（系統提示：未偵測到 GEMINI_API_KEY，此為模擬特徵）圖1背景：這是一張具有強烈賽博龐克風格的城市街景，背景充滿著五顏六色的霓虹燈招牌，光線昏暗，帶有藍紫色調。人行道上有積水反射著霓虹燈光，整體氛圍充滿未來科技感。"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
    encoded_img = base64.b64encode(image_bytes).decode('utf-8')
    payload = {
        "contents": [{
            "parts": [
                {"text": "請詳細描述這張圖片中人物的背景特徵、光影、氛圍與風格。請以「圖1背景：」作為開頭，字數控制在150字以內。請直接給出結果，不要多做說明。"},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": encoded_img
                }}
            ]
        }]
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            return f"（特徵反推失敗，API 錯誤：{resp.status_code}）"
    except Exception as e:
        return f"（特徵反推失敗，發生例外狀況：{str(e)}）"

@st.dialog("⚠️ 啟動前確認")
def confirm_run():
    st.write("是否要使用目前的提示詞？")
    st.info(f"{st.session_state.p1}")
    
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("是的，繼續下一步", type="primary", use_container_width=True):
            st.session_state.start_actual_run = True
            st.rerun()
    with col_n:
        if st.button("取消", use_container_width=True):
            st.rerun()

# --- 3. ComfyUI 網路工具函數 ---'''

part2_old = '''with col_src:
    st.markdown("#### 👤 人物原圖")
    subj_file = st.file_uploader("拖放圖片至此處", type=['png', 'jpg', 'jpeg'], key="subj")
    if subj_file:
        display_img = create_padded_image_with_blur(subj_file.getvalue(), (512, 512))
        st.image(display_img, caption="原圖預覽 (點擊右上角 Full view)", use_column_width=True)

with col_pose:'''

part2_new = '''with col_src:
    st.markdown("#### 👤 人物原圖")
    subj_file = st.file_uploader("拖放圖片至此處", type=['png', 'jpg', 'jpeg'], key="subj")
    if subj_file:
        display_img = create_padded_image_with_blur(subj_file.getvalue(), (512, 512))
        st.image(display_img, caption="原圖預覽 (點擊右上角 Full view)", use_column_width=True)
        if st.button("🔍 智能反推原圖特徵 (Nano Banana Pro)", use_container_width=True):
            with st.spinner("Nano Banana Pro 視覺大腦分析中..."):
                new_prompt = analyze_image_features(subj_file.getvalue())
                st.session_state.p1 = new_prompt
                st.rerun()

with col_pose:'''

part3_old = '''# --- 8. 執行運算邏輯 ---
if run_btn:
    if not core_alive:
        st.error("❌ 錯誤：ComfyUI 核心引擎未啟動。請確認後端已開啟！")
    elif not subj_file or not pose_file:
        st.warning("⚠️ 警告：素材不完整！請同時上傳「人物原圖」與「姿勢參考」後再執行。")
    else:
        log_placeholder = st.empty()
        status_box = st.status("🚀 正在執行 Jojo 實戰任務...", expanded=True)
        
        try:'''

part3_new = '''# --- 8. 執行運算邏輯 ---
if run_btn:
    if not core_alive:
        st.error("❌ 錯誤：ComfyUI 核心引擎未啟動。請確認後端已開啟！")
    elif not subj_file or not pose_file:
        st.warning("⚠️ 警告：素材不完整！請同時上傳「人物原圖」與「姿勢參考」後再執行。")
    else:
        confirm_run()

if st.session_state.get('start_actual_run', False):
    st.session_state.start_actual_run = False
    
    log_placeholder = st.empty()
    status_box = st.status("🚀 正在執行 Jojo 實戰任務...", expanded=True)
    
    try:'''

if part1_old not in content:
    print('Failed to find part 1')
if part2_old not in content:
    print('Failed to find part 2')
if part3_old not in content:
    print('Failed to find part 3')

content = content.replace(part1_old, part1_new)
content = content.replace(part2_old, part2_new)
content = content.replace(part3_old, part3_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Success')