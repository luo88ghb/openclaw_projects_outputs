import sys
import os
import streamlit as st
import requests
import json
import time
import websocket
import uuid
import datetime
from PIL import Image, ImageFilter
import io
import random

# --- 1. 配置與環境 ---
anaconda_site_packages = r"C:\Users\danny\anaconda3\Lib\site-packages"
if anaconda_site_packages not in sys.path:
    sys.path.insert(0, anaconda_site_packages)

COMFY_SERVER = "127.0.0.1:8188"
CLIENT_ID = str(uuid.uuid4())
WORKSPACE = r"C:\Users\danny\.openclaw\workspace"
RESULTS_DIR = os.path.join(WORKSPACE, "Zeni_Results")
os.makedirs(RESULTS_DIR, exist_ok=True)

st.set_page_config(page_title="Qwen-2511 姿勢遷移", layout="wide")
st.markdown("<style>.main { background-color: #0d1117; color: #00f2ff; }</style>", unsafe_allow_html=True)

# --- 2. 輔助工具與預設值 ---
DEFAULT_PROMPTS = {
    "p1": "图1背景：街道两旁是日式商业街，店铺招牌多为中文与日文混合，黄色遮阳篷下是玻璃橱窗，店内灯光明亮。人行道铺有灰色地砖，有行人穿梭，远处可见红绿灯与电线杆。街道上方悬挂着广告牌与指示牌，建筑外墙为浅色，有绿植点缀。整体氛围是都市街头的日常繁忙，光线明亮，略带午后阳光感。",
    "p2": "让图像1中的人物摆出与图像2中人物完全相同的姿势。绝对不能更改图像1中人物的风格和衣服，发型，脸部。新的姿势应与我们要复制的姿势像素级精确一致。手臂、头部和腿的位置应与我们要复制的姿势相同。调整视角和拍摄角度，使其与图像2完全一致。头部倾斜和视线姿势应与图像2中的人物匹配。保留图2背景",
    "p3": "图2背景为柔和的橄榄绿色调，墙面平整无纹理，营造出简约而宁静的视觉空间。光线均匀柔和，无明显阴影或强烈反差，凸显出整体环境的沉静与高级感。色调统一，无杂乱元素，突出主体人物的视觉焦点，同时赋予画面一种现代、克制的时尚氛围。整体背景设计服务于主题表达，无多余装饰，强调纯净与高级质感。"
}

for k, v in DEFAULT_PROMPTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_prompts():
    for k, v in DEFAULT_PROMPTS.items():
        st.session_state[k] = v

def create_padded_image_with_blur(image_bytes, target_size=(512, 512)):
    """將原圖等比例縮放放入目標框，並將多餘空間用模糊背景填滿"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_w, img_h = img.size
    target_w, target_h = target_size
    
    # 縮放原圖至框內最大
    scale = min(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)
    
    # 製作模糊背景
    scale_fill = max(target_w / img_w, target_h / img_h)
    bg_w = int(img_w * scale_fill)
    bg_h = int(img_h * scale_fill)
    bg_img = img.resize((bg_w, bg_h), Image.LANCZOS)
    
    # 裁切中間區塊
    left = (bg_w - target_w) / 2
    top = (bg_h - target_h) / 2
    bg_img = bg_img.crop((left, top, left + target_w, top + target_h))
    
    # 應用模糊濾鏡
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=20))
    
    # 將清晰原圖貼到正中間
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    bg_img.paste(img_resized, (paste_x, paste_y))
    
    return bg_img

# --- 3. ComfyUI 網路工具函數 ---
def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    res = requests.post(f"http://{COMFY_SERVER}/prompt", data=data)
    if res.status_code != 200:
        error_info = res.json()
        raise Exception(f"ComfyUI 報錯: {error_info.get('error', {}).get('message', '未知錯誤')}\n詳情: {error_info}")
    return res.json()['prompt_id']

def upload_image(file, name):
    files = {"image": (name, file)}
    res = requests.post(f"http://{COMFY_SERVER}/upload/image", files=files)
    return res.json()

def get_history(prompt_id):
    res = requests.get(f"http://{COMFY_SERVER}/history/{prompt_id}").json()
    return res.get(prompt_id, {})

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    res = requests.get(f"http://{COMFY_SERVER}/view", params=data)
    return res.content

# --- 4. 側邊欄：核心監控 ---
with st.sidebar:
    st.header("📋 核心監控")
    core_alive = False
    try:
        requests.get(f"http://{COMFY_SERVER}/system_stats", timeout=0.5)
        core_alive = True
    except: pass
    st.markdown(f"{'🟢' if core_alive else '🔴'} **ComfyUI 核心引擎**")
    
    if st.button("🔄 刷新連線狀態"):
        st.rerun()

# --- 5. 頂端標題區 ---
st.markdown("<h1 style='text-align: center;'>Qwen-2511 姿勢遷移</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #00f2ff;'>傑尼引擎 V9.4：Jojo 實戰架構版 (UI 優化)</h3>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

# --- 6. 核心操作區塊 (1:1:2.5 版面配置) ---
col_src, col_pose, col_res = st.columns([1, 1, 2.5])

with col_src:
    st.markdown("#### 👤 人物原圖")
    subj_file = st.file_uploader("拖放圖片至此處", type=['png', 'jpg', 'jpeg'], key="subj")
    if subj_file:
        display_img = create_padded_image_with_blur(subj_file.getvalue(), (512, 512))
        st.image(display_img, caption="原圖預覽 (點擊右上角 Full view)", use_column_width=True)

with col_pose:
    st.markdown("#### 💃 姿勢參考")
    pose_file = st.file_uploader("拖放圖片至此處", type=['png', 'jpg', 'jpeg'], key="pose")
    if pose_file:
        display_img = create_padded_image_with_blur(pose_file.getvalue(), (512, 512))
        st.image(display_img, caption="姿勢預覽 (點擊右上角 Full view)", use_column_width=True)

with col_res:
    st.markdown("#### ✨ 融合結果")
    result_placeholder = st.empty()
    if 'last_result' in st.session_state:
        result_placeholder.image(st.session_state['last_result'], caption="✨ 最新融合產出 (點擊右上角 Full view)", use_column_width=True)
    else:
        result_placeholder.info("尚未產出，等待運算中...")
        
    st.markdown("<br/>", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        run_btn = st.button("🔥 啟動融合運算")
    with btn_col2:
        if st.button("📂 開啟輸出資料夾"):
            os.startfile(RESULTS_DIR)

# --- 7. 進階設定區 (Advanced Settings) ---
st.markdown("<br/>", unsafe_allow_html=True)
with st.expander("⚙️ 進階設定 (Advanced Settings)", expanded=False):
    # Prompt section
    st.markdown("##### 📝 提示詞設定")
    if st.button("🔄 恢復預設提示詞"):
        reset_prompts()
        st.rerun()
    
    st.session_state.p1 = st.text_area("人物原圖背景描述 (图1背景)", st.session_state.p1, height=100)
    st.session_state.p2 = st.text_area("核心控制指令", st.session_state.p2, height=100)
    st.session_state.p3 = st.text_area("目標背景描述 (图2背景)", st.session_state.p3, height=100)

    st.markdown("---")
    
    # Parameters section
    st.markdown("##### 🎛️ 參數設定")
    c1, c2 = st.columns(2)
    with c1:
        use_random_seed = st.checkbox("🎲 隨機種子 (Randomize seed)", value=True)
        seed_val = st.number_input("種子 (Seed)", value=0, disabled=use_random_seed)
        cfg_val = st.slider("引導係數 (True guidance scale)", min_value=1.0, max_value=10.0, value=1.0, step=0.1)
    with c2:
        steps_val = st.slider("運算步數 (Number of inference steps)", min_value=1, max_value=40, value=4, step=1)
        longest_edge = st.slider("輸出解析度最長邊 (Longest Edge Resolution)", min_value=512, max_value=2048, value=1024, step=128)
        st.caption("提示: Jojo 工作流會根據原圖比例自動縮放，此數值決定產出圖片的最長邊大小。")

# --- 8. 執行運算邏輯 ---
if run_btn:
    if not core_alive:
        st.error("❌ 錯誤：ComfyUI 核心引擎未啟動。請確認後端已開啟！")
    elif not subj_file or not pose_file:
        st.warning("⚠️ 警告：素材不完整！請同時上傳「人物原圖」與「姿勢參考」後再執行。")
    else:
        log_placeholder = st.empty()
        status_box = st.status("🚀 正在執行 Jojo 實戰任務...", expanded=True)
        
        try:
            status_box.write("📤 正在同步素材至伺服器...")
            subj_name = f"zeni_subj_{int(time.time())}.png"
            pose_name = f"zeni_pose_{int(time.time())}.png"
            upload_image(subj_file.getvalue(), subj_name)
            upload_image(pose_file.getvalue(), pose_name)
            
            workflow_path = os.path.join(WORKSPACE, "Jojo_workflow_api.json")
            if not os.path.exists(workflow_path):
                raise Exception(f"找不到工作流定義檔: {workflow_path}")
                
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            
            # 動態注入圖片
            workflow["101"]["inputs"]["image"] = subj_name
            workflow["102"]["inputs"]["image"] = pose_name
            
            # 動態注入提示詞
            workflow["10"]["inputs"]["text"] = st.session_state.p1
            workflow["11"]["inputs"]["text"] = st.session_state.p2
            workflow["12"]["inputs"]["text"] = st.session_state.p3
            
            # 動態注入參數
            actual_seed = random.randint(0, 2147483647) if use_random_seed else int(seed_val)
            workflow["25"]["inputs"]["seed"] = actual_seed
            workflow["25"]["inputs"]["steps"] = int(steps_val)
            workflow["25"]["inputs"]["cfg"] = float(cfg_val)
            workflow["14"]["inputs"]["scale_to_length"] = int(longest_edge)
            workflow["15"]["inputs"]["scale_to_length"] = int(longest_edge)
            
            status_box.write(f"🛰️ 正在發送任務 (Seed: {actual_seed}, Steps: {int(steps_val)})...")
            try:
                prompt_id = queue_prompt(workflow)
            except Exception as pe:
                st.error(f"❌ 工作流驗證失敗！\n\n{str(pe)}")
                status_box.update(label="❌ 任務因工作流錯誤終止", state="error")
                st.stop()
            
            status_box.write(f"🆔 任務 ID: {prompt_id}，正在即時監聽日誌...")
            ws = websocket.create_connection(f"ws://{COMFY_SERVER}/ws?clientId={CLIENT_ID}")
            real_logs = []
            
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        node = message['data']['node']
                        if node is None: break
                        node_class = workflow.get(str(node), {}).get('class_type', '未知節點')
                        real_logs.append(f"⚙️ 正在處理: {node_class} (ID: {node})...")
                        log_placeholder.code("\n".join(real_logs[-10:]))
                    if message['type'] == 'progress':
                        v = message['data']['value']
                        m = message['data']['max']
                        status_box.write(f"⏳ 採樣進度: {int(v/m*100)}%")
                else: continue
            
            status_box.write("📥 運算完成，正在抓取結果...")
            history = get_history(prompt_id)
            if not history:
                raise Exception("無法取得運算歷史紀錄。")
            
            success = False
            for node_id in history.get('outputs', {}):
                node_output = history['outputs'][node_id]
                if 'images' in node_output:
                    for img_info in node_output['images']:
                        img_bytes = get_image(img_info['filename'], img_info['subfolder'], img_info['type'])
                        
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"Zeni_Fusion_{timestamp}.png"
                        save_path = os.path.join(RESULTS_DIR, filename)
                        with open(save_path, "wb") as f:
                            f.write(img_bytes)
                        
                        # 存入 session state 並更新畫面
                        st.session_state['last_result'] = img_bytes
                        result_placeholder.image(img_bytes, caption=f"✨ 融合產出 ({filename})", use_column_width=True)
                        st.balloons()
                        success = True
            
            if success:
                status_box.update(label="✅ 任務圓滿完成！", state="complete")
            else:
                status_box.update(label="⚠️ 任務完成，但未找到輸出圖片。", state="warning")
            
        except Exception as e:
            st.error(f"☢️ 運算過程發生致命錯誤：\n{str(e)}")
            status_box.update(label="❌ 任務執行失敗", state="error")
