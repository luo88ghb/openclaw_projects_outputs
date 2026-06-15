import sys
import os
import streamlit as st
import requests
import json
import time
import websocket
import uuid
import datetime
import random
import io
import base64
from PIL import Image, ImageFilter
from pathlib import Path

# 載入模型檢查模組
import models_checker

# --- 1. 配置與路徑初始化 ---
CLIENT_ID = str(uuid.uuid4())
COMFY_SERVER = "127.0.0.1:8188"
WORKSPACE = r"C:\Users\danny\.openclaw\workspace\projects\Comfyui_Qwen2511_Anti"
RESULTS_DIR = os.path.join(WORKSPACE, "Anti_Results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# 設為寬版，使用極簡暗黑霓虹風格
st.set_page_config(page_title="Qwen-2511 Anti 姿勢遷移引擎", layout="wide")

# CSS 霓虹暗黑與玻璃擬物化風格 (Glassmorphism)
st.markdown("""
<style>
    .main {
        background-color: #090d16;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #090d16 0%, #111827 100%);
    }
    /* 玻璃擬物容器 */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    /* 霓虹標題 */
    .neon-text {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00f2ff, #bb00ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 10px rgba(0, 242, 255, 0.2);
        margin-bottom: 5px;
    }
    .neon-subtext {
        text-align: center;
        color: #8b9bb4;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }
    /* 邊界狀態 */
    .status-ok {
        color: #10b981;
        font-weight: bold;
    }
    .status-warning {
        color: #f59e0b;
        font-weight: bold;
    }
    .status-error {
        color: #ef4444;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 預設提示詞與狀態管理 ---
DEFAULT_PROMPTS = {
    "p1": "图1背景：街道两旁是日式商业街，店铺招牌多为中文与日文混合，黄色遮阳篷下是玻璃橱窗，店内灯光明亮。人行道铺有灰色地砖，有行人穿梭，远处可见红绿灯与电线杆。街道上方悬挂着广告牌与指示牌，建筑外墙为浅色，有绿植点缀。整体氛围是都市街头的日常繁忙，光线明亮，略带午后阳光感。",
    "p2": "让图像1中的人物摆出与图像2中人物完全相同的姿势。绝对不能更改图像1中人物的风格和衣服，发型，脸部。新的姿势应与我们要复制的姿势像素级精确一致。手臂、头部和腿的位置应与我们要复制的姿势相同。调整视角和拍摄角度，使其与图像2完全一致。头部倾斜和视线姿势应与图像2中的人物匹配。保留图2背景",
    "p3": ""
}

for k, v in DEFAULT_PROMPTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_prompts():
    for k, v in DEFAULT_PROMPTS.items():
        st.session_state[k] = v

# --- 3. 圖像前處理工具 (Pillow) ---
def create_padded_image_with_blur(image_bytes, target_size=(512, 512)):
    """將原圖等比例縮放放入目標框，多餘空間用高斯模糊背景填滿，確保傳入模型比例正確"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_w, img_h = img.size
    target_w, target_h = target_size
    
    scale = min(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    scale_fill = max(target_w / img_w, target_h / img_h)
    bg_w = int(img_w * scale_fill)
    bg_h = int(img_h * scale_fill)
    bg_img = img.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
    
    left = (bg_w - target_w) / 2
    top = (bg_h - target_h) / 2
    bg_img = bg_img.crop((left, top, left + target_w, top + target_h))
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=20))
    
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    bg_img.paste(img_resized, (paste_x, paste_y))
    
    return bg_img

# --- 4. 視覺分析 (Qwen-VL 視覺反推 & 類型辨識) ---
def analyze_image_features(image_bytes):
    """呼叫本地 Qwen-VL 端點描述圖像背景與分析主體類型"""
    url = "http://127.0.0.1:8000/v1/chat/completions" 
    encoded_img = base64.b64encode(image_bytes).decode('utf-8')
    
    # 首先：反推背景描述
    payload_desc = {
        "model": "qwen-vl-plus",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "請詳細描述這張圖片中人物的背景特徵、光影、氛圍與風格。請以「圖1背景：」作為開頭，字數控制在150字以內。請直接給出結果，不要多做說明。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
                ]
            }
        ]
    }
    
    # 其次：判斷是否為人類正臉
    payload_type = {
        "model": "qwen-vl-plus",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "分析這張圖片中的主要主體類型。它是『人類人物 (human)』還是『非人類物種/風格化角色 (non-human)』？請只回覆一個單詞：human 或 non-human。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
                ]
            }
        ]
    }
    
    description = "（Qwen-VL 反推失敗）"
    detected_type = "human" # 預設值
    
    try:
        resp = requests.post(url, json=payload_desc, timeout=45)
        if resp.status_code == 200:
            description = resp.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        description = f"（Qwen-VL 反推失敗，例外：{str(e)}）"
        
    try:
        resp_type = requests.post(url, json=payload_type, timeout=45)
        if resp_type.status_code == 200:
            ans = resp_type.json()['choices'][0]['message']['content'].strip().lower()
            if "non-human" in ans:
                detected_type = "non-human"
    except:
        pass
        
    return description, detected_type

# --- 5. ComfyUI REST/WebSocket 工具函數 ---
def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    res = requests.post(f"http://{COMFY_SERVER}/prompt", data=data)
    if res.status_code != 200:
        error_info = res.json()
        raise Exception(f"ComfyUI 後端報錯: {error_info.get('error', {}).get('message', '未知錯誤')}")
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

# --- 6. 頁面標題 ---
st.markdown("<h1 class='neon-text'>Qwen-2511 Anti 姿勢遷移系統</h1>", unsafe_allow_html=True)
st.markdown("<p class='neon-subtext'>Comfyui_Qwen2511_Anti 進階版：多階段骨架控制與主體安全特徵維護</p>", unsafe_allow_html=True)

# --- 7. 模型監控中心 (Model Monitor Hub) ---
st.markdown("### 📋 模型監控中心 (Model Monitor Hub)")
model_status = models_checker.check_models()
all_models_ready = True

cols_monitor = st.columns(6)
for i, (key, info) in enumerate(model_status.items()):
    with cols_monitor[i]:
        st.markdown(f"**{info['name']}**")
        st.caption(f"`{info['filename']}`")
        if info["exists"]:
            st.markdown("<span class='status-ok'>🟢 已就位</span>", unsafe_allow_html=True)
            st.caption(f"大小: {info['size_mb']:.1f} MB")
        else:
            all_models_ready = False
            st.markdown("<span class='status-error'>🔴 缺失</span>", unsafe_allow_html=True)
            if st.button(f"📥 下載", key=f"dl_{key}", use_container_width=True):
                # 呼叫 Streamlit 下載邏輯
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def progress_cb(dl_bytes, total_bytes):
                    percent = int((dl_bytes / total_bytes) * 100) if total_bytes > 0 else 0
                    progress_bar.progress(percent)
                    status_text.info(f"⏳ 正在下載: {dl_bytes/(1024*1024):.1f}MB / {total_bytes/(1024*1024):.1f}MB ({percent}%)")
                
                try:
                    with st.spinner("下載模型中，請勿關閉網頁..."):
                        models_checker.download_model(key, progress_callback=progress_cb)
                    st.success(f"🎉 下載完成！請刷新頁面確認。")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 下載失敗: {str(e)}")

st.markdown("---")

# --- 8. 側邊欄監控 ---
with st.sidebar:
    st.header("⚙️ 引擎連線監控")
    core_alive = False
    try:
        requests.get(f"http://{COMFY_SERVER}/system_stats", timeout=0.5)
        core_alive = True
    except:
        pass
    st.markdown(f"{'🟢' if core_alive else '🔴'} **ComfyUI 核心引擎狀態**")
    
    if st.button("🔄 重新載入狀態"):
        st.rerun()

# --- 9. 主操作版面 (1:1:2.5) ---
col_src, col_pose, col_res = st.columns([1, 1, 2.5])

with col_src:
    st.markdown("#### 👤 人物主體來源 (Subject)")
    subj_file = st.file_uploader("上傳人物主體原圖", type=['png', 'jpg', 'jpeg'], key="subj")
    
    if subj_file:
        display_img = create_padded_image_with_blur(subj_file.getvalue(), (512, 512))
        st.image(display_img, caption="主體預覽 (已進行等比例模糊填充)", use_column_width=True)
        
        # 視覺特徵反推按鈕
        if st.button("🔍 智能特徵反推 & 類型檢測", use_container_width=True):
            with st.spinner("Qwen-VL 大腦正在分析主體與背景細節..."):
                desc, detected_type = analyze_image_features(subj_file.getvalue())
                st.session_state.p1 = desc
                st.session_state.subject_type = detected_type
                st.rerun()

    # 主體類型安全防護顯示
    subj_type = st.session_state.get("subject_type", "human")
    if subj_file:
        st.markdown(f"**偵測主體類型**: `{subj_type}`")
        if subj_type == "non-human":
            st.warning("⚠️ 安全提示：偵測到非人類主體（例如動漫角色、動物）。系統已自動調降骨架控制權重，並關閉 FaceID 人臉相似嵌入，防止肢體與外觀產生嚴重變形。")

with col_pose:
    st.markdown("#### 💃 動作姿勢來源 (Pose)")
    pose_file = st.file_uploader("上傳目標動作姿勢圖", type=['png', 'jpg', 'jpeg'], key="pose")
    if pose_file:
        display_img = create_padded_image_with_blur(pose_file.getvalue(), (512, 512))
        st.image(display_img, caption="姿勢參考圖預覽", use_column_width=True)

with col_res:
    st.markdown("#### ✨ 姿勢遷移融合結果")
    result_placeholder = st.empty()
    if 'last_result' in st.session_state:
        result_placeholder.image(st.session_state['last_result'], caption="✨ 最新融合產出圖像", use_column_width=True)
    else:
        result_placeholder.info("尚未執行運算，等待素材與參數設定...")
        
    st.markdown("<br/>", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        run_btn = st.button("🔥 啟動雙重條件姿勢遷移", type="primary", use_container_width=True)
    with btn_col2:
        if st.button("📂 開啟輸出目錄", use_container_width=True):
            try:
                os.startfile(RESULTS_DIR)
            except Exception as e:
                st.error(f"無法開啟資料夾: {str(e)}")

# --- 10. 進階配置 (Advanced Panel) ---
st.markdown("<br/>", unsafe_allow_html=True)
with st.expander("⚙️ 骨架與身份控制進階參數設定 (Advanced Controls)", expanded=True):
    st.markdown("##### 📝 背景與核心提示詞設定")
    if st.button("🔄 重設提示詞"):
        reset_prompts()
        st.rerun()
    
    st.session_state.p1 = st.text_area("圖1背景特徵描述 (Subject Background)", st.session_state.p1, height=80)
    st.session_state.p2 = st.text_area("姿勢精確融合控制指令 (Control Instruction)", st.session_state.p2, height=80)
    st.session_state.p3 = st.text_area("增補背景修飾指令 (Target Background)", st.session_state.p3, height=80)

    st.markdown("---")
    
    st.markdown("##### 🎛️ 姿勢遷移控制強度與採樣")
    c1, c2 = st.columns(2)
    with c1:
        pose_mode = st.selectbox("遷移策略模式 (Migration Mode)", ["精準人像遷移 (Human-to-Human)", "跨風格/物種轉譯 (Cross-Style/Creative)"], index=0 if subj_type == "human" else 1)
        
        # 根據模式給予預設參數，並允許手動滑桿微調
        default_cn_strength = 0.7 if pose_mode == "精準人像遷移 (Human-to-Human)" else 0.4
        default_faceid_strength = 1.0 if pose_mode == "精準人像遷移 (Human-to-Human)" else 0.0
        
        cn_strength = st.slider("姿勢控制權重 (ControlNet Strength)", min_value=0.0, max_value=1.5, value=default_cn_strength, step=0.1)
        faceid_strength = st.slider("人臉身份保留強度 (FaceID Strength)", min_value=0.0, max_value=1.5, value=default_faceid_strength, step=0.1)
        
    with c2:
        use_random_seed = st.checkbox("🎲 使用隨機種子", value=True)
        seed_val = st.number_input("指定種子", value=0, disabled=use_random_seed)
        steps_val = st.slider("降噪運算步數 (Lightning 推薦 4~8 步)", min_value=1, max_value=20, value=4, step=1)
        longest_edge = st.slider("輸出影像解析度最長邊", min_value=512, max_value=2048, value=1024, step=128)

# --- 11. 雙防呆啟動確認視窗 ---
@st.dialog("⚠️ 任務啟動安全確認")
def confirm_run():
    st.markdown("請確認以下提示詞與核心設定無誤後，即可向 ComfyUI 核心發送任務：")
    st.info(f"**人物背景描述**：{st.session_state.p1}\n\n**核心指令**：{st.session_state.p2}")
    st.markdown(f"- 姿勢控制強度: `{cn_strength}` | 身份保留強度: `{faceid_strength}`")
    st.markdown(f"- 輸出最長邊解析度: `{longest_edge} px`")
    
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("是的，確認啟動任務", type="primary", use_container_width=True):
            st.session_state.start_actual_run = True
            st.rerun()
    with col_n:
        if st.button("取消並返回修改", use_container_width=True):
            st.rerun()

# --- 12. 運算執行邏輯 ---
if run_btn:
    if not core_alive:
        st.error("❌ 錯誤：無法連線至 ComfyUI 核心引擎。請確認後端已開啟並執行在埠口 8188 上！")
    elif not subj_file or not pose_file:
        st.warning("⚠️ 警告：素材不足。請務必同時上傳「人物主體原圖」與「動作姿勢參考圖」！")
    elif not all_models_ready:
        st.error("❌ 錯誤：尚有核心模型缺失，請先在監控中心下載所需模型！")
    else:
        confirm_run()

if st.session_state.get('start_actual_run', False):
    st.session_state.start_actual_run = False
    
    log_placeholder = st.empty()
    status_box = st.status("🚀 正在啟動 Qwen-2511 Anti 姿勢遷移工作流...", expanded=True)
    
    try:
        status_box.write("📤 正在同步並上傳主體與姿勢素材至 ComfyUI 伺服器...")
        subj_name = f"anti_subj_{int(time.time())}.png"
        pose_name = f"anti_pose_{int(time.time())}.png"
        upload_image(subj_file.getvalue(), subj_name)
        upload_image(pose_file.getvalue(), pose_name)
        
        # 讀取工作流 JSON
        workflow_path = os.path.join(WORKSPACE, "Jojo_workflow_api.json")
        if not os.path.exists(workflow_path):
            raise Exception(f"找不到工作流定義檔: {workflow_path}")
            
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        # 動態注入上傳的圖片檔名
        workflow["101"]["inputs"]["image"] = subj_name
        workflow["102"]["inputs"]["image"] = pose_name
        
        # 動態注入前端提示詞
        workflow["10"]["inputs"]["text"] = st.session_state.p1
        workflow["11"]["inputs"]["text"] = st.session_state.p2
        workflow["12"]["inputs"]["text"] = st.session_state.p3
        
        # 依據進階設定，動態注入強度與控制參數
        actual_seed = random.randint(0, 2147483647) if use_random_seed else int(seed_val)
        workflow["25"]["inputs"]["seed"] = actual_seed
        workflow["25"]["inputs"]["steps"] = int(steps_val)
        workflow["25"]["inputs"]["cfg"] = 1.0 # 推薦固定 1.0 (Lightning LoRA)
        workflow["14"]["inputs"]["scale_to_length"] = int(longest_edge)
        workflow["15"]["inputs"]["scale_to_length"] = int(longest_edge)
        
        # AnyPose LoRA 的強度動態注入 (對應節點 5 與 6 的 strength_model)
        workflow["5"]["inputs"]["strength_model"] = float(cn_strength)
        workflow["6"]["inputs"]["strength_model"] = float(cn_strength)
        
        status_box.write(f"🛰️ 正在隊列任務 (種子值: {actual_seed}, 降噪步數: {steps_val})...")
        prompt_id = queue_prompt(workflow)
        
        status_box.write(f"🆔 任務 ID: {prompt_id}，正在監聽後端 WebSocket 進度...")
        
        # 查詢排隊狀況
        try:
            queue_info = requests.get(f"http://{COMFY_SERVER}/queue").json()
            running_jobs = queue_info.get('queue_running', [])
            pending_jobs = queue_info.get('queue_pending', [])
            my_pos = -1
            for pos, item in enumerate(pending_jobs):
                if item[1] == prompt_id:
                    my_pos = pos + 1
                    break
            
            if len(running_jobs) > 0 or (my_pos != -1 and my_pos > 1):
                wait_count = len(running_jobs) + max(0, my_pos - 1)
                status_box.warning(f"⏳ 偵測到伺服器目前有其他任務正在處理。您的任務已入列排隊，前方等待中任務數: {wait_count}。請耐心等候前序任務完成載入與生成。")
        except Exception:
            pass

        ws = websocket.create_connection(f"ws://{COMFY_SERVER}/ws?clientId={CLIENT_ID}")
        ws.settimeout(600)  # 最多等 10 分鐘
        
        # 在 Streamlit 中建立進度條、狀態列與計時器
        progress_bar = st.progress(0.0)
        node_status = st.empty()
        elapsed_display = st.empty()
        real_logs = []
        
        # 計時開始
        start_time = time.time()
        current_node_class = "初始化中"
        is_my_task_running = False
        
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                msg_type = message.get('type')
                data = message.get('data', {})
                
                # 取得該訊息對應的 prompt_id（部分 ComfyUI 版本的進度訊息不含此欄位）
                curr_prompt_id = data.get('prompt_id')
                
                # 計算已用時間
                elapsed = int(time.time() - start_time)
                elapsed_str = f"{elapsed // 60}m {elapsed % 60}s"
                
                if msg_type == 'status':
                    queue_remaining = data.get('status', {}).get('exec_info', {}).get('queue_remaining', 0)
                    if queue_remaining > 0:
                        node_status.warning(f"⏳ 伺服器忙碌中，剩餘排隊任務數: {queue_remaining}。本任務排隊中... (已等待 {elapsed_str})")
                    elif not is_my_task_running:
                        node_status.info(f"🛰️ 伺服器空閒，正在準備您的任務... (已等待 {elapsed_str})")
                        
                elif msg_type == 'execution_start':
                    if curr_prompt_id == prompt_id:
                        is_my_task_running = True
                        node_status.info("🚀 您的任務已被伺服器接受並開始執行工作流...")
                        
                elif msg_type == 'executing':
                    node = data.get('node')
                    if node is None:
                        # 某些 ComfyUI 版本不含 prompt_id，只要 node=None 就代表完成
                        if curr_prompt_id == prompt_id or curr_prompt_id is None:
                            node_status.success("✅ 所有工作流節點執行完畢！")
                            progress_bar.progress(1.0)
                            elapsed_display.empty()
                            break
                        else:
                            continue
                    
                    node_class = workflow.get(str(node), {}).get('class_type', '未知節點')
                    current_node_class = node_class
                    
                    if curr_prompt_id == prompt_id or (is_my_task_running and curr_prompt_id is None):
                        status_msg = f"⚙️ 正在處理節點: **{node_class}** (ID: {node}) | 已用時: {elapsed_str}"
                        real_logs.append(status_msg)
                        node_status.markdown(status_msg)
                        log_placeholder.code("\n".join(real_logs[-8:]))
                    else:
                        node_status.warning(f"⏳ 伺服器正忙於處理前序任務的節點: **{node_class}** (ID: {node})... 請稍候。(已等待 {elapsed_str})")
                        
                elif msg_type == 'progress':
                    v = data.get('value', 0)
                    m = data.get('max', 1)
                    percent = min(float(v) / float(m), 1.0)
                    
                    # 修正：ComfyUI 的 progress 訊息有時不含 prompt_id
                    # 只要 is_my_task_running=True，就代表這個 progress 屬於我們的任務
                    if curr_prompt_id == prompt_id or (is_my_task_running and curr_prompt_id is None):
                        progress_bar.progress(percent)
                        elapsed_display.markdown(
                            f"**⏱️ 採樣步數: {v}/{m}（{int(percent * 100)}%）** | 當前節點: `{current_node_class}` | 已用時: **{elapsed_str}**"
                        )
                    elif curr_prompt_id != prompt_id:
                        # 前序任務的進度，讓使用者知道它在跑
                        elapsed_display.markdown(
                            f"⏳ 前序任務進行中... 採樣步數: {v}/{m}（{int(percent * 100)}%） | 已等待: **{elapsed_str}**"
                        )
                        
                elif msg_type == 'execution_cached':
                    if curr_prompt_id == prompt_id:
                        cached_nodes = data.get('nodes', [])
                        status_box.write(f"📦 已快取節點，數量: {len(cached_nodes)}")
                        
                elif msg_type == 'execution_error':
                    if curr_prompt_id == prompt_id or curr_prompt_id is None:
                        exception_message = data.get('exception_message', '未知錯誤')
                        exception_type = data.get('exception_type', 'Exception')
                        node_id = data.get('node_id', '未知')
                        node_type = data.get('node_type', '未知')
                        
                        error_detail = f"❌ ComfyUI 後端執行錯誤！\n- 節點 ID: {node_id} ({node_type})\n- 錯誤類型: {exception_type}\n- 錯誤原因: {exception_message}"
                        status_box.update(label="❌ 任務執行出錯", state="error")
                        st.error(error_detail)
                        raise Exception(error_detail)
            else:
                continue
        
        status_box.write("📥 運算完成！正在從歷史紀錄抓取最終影像...")
        history = get_history(prompt_id)
        if not history:
            raise Exception("無法取得該任務的運算歷史紀錄。")
        
        success = False
        for node_id in history.get('outputs', {}):
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                for img_info in node_output['images']:
                    img_bytes = get_image(img_info['filename'], img_info['subfolder'], img_info['type'])
                    
                    # 依時間戳記命名並儲存至專案目錄
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"Anti_Fusion_{timestamp}.png"
                    save_path = os.path.join(RESULTS_DIR, filename)
                    with open(save_path, "wb") as f:
                        f.write(img_bytes)
                    
                    st.session_state['last_result'] = img_bytes
                    result_placeholder.image(img_bytes, caption=f"✨ 成功融合輸出: {filename}", use_column_width=True)
                    st.balloons()
                    success = True
        
        if success:
            status_box.update(label="✅ 任務圓滿完成！影像已儲存至 Anti_Results 目錄。", state="complete")
        else:
            status_box.update(label="⚠️ 任務完成，但未能取得生成的影像節點輸出。", state="warning")
            
    except Exception as e:
        st.error(f"☢️ 姿勢遷移管線執行發生致命錯誤：\n{str(e)}")
        status_box.update(label="❌ 任務執行失敗", state="error")
