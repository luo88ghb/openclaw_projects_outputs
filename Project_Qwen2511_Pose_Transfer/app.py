import streamlit as st
import requests
import json
import time
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image

# 頁面配置
st.set_page_config(
    page_title="Zeni-Precision | AI Pose Transfer V10",
    page_icon="🐢",
    layout="wide"
)

# CSS 樣式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 10px;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 30px;
    }
    .status-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #f0f2f6;
        border-left: 5px solid #1f77b4;
        margin: 10px 0;
    }
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# ================= 配置 =================
COMFYUI_URL = "http://127.0.0.1:8188"

# ================= 核心工具 =================
def check_comfyui_connection():
    """檢查 ComfyUI 連線狀態"""
    try:
        response = requests.get(f"{COMFYUI_URL}/api", timeout=3)
        return response.status_code == 200
    except:
        return False

def upload_image_to_comfyui(image_file, image_type="input"):
    """將圖像上傳至 ComfyUI"""
    try:
        files = {'image': (image_file.name, image_file.getvalue(), 'image/png')}
        response = requests.post(f"{COMFYUI_URL}/upload/image", files=files, timeout=30)
        if response.status_code == 200:
            return response.json().get('name')
        return None
    except Exception as e:
        st.error(f"上傳失敗: {e}")
        return None

def queue_workflow(workflow_data):
    """將工作流提交至 ComfyUI 隊列"""
    try:
        data = {
            "prompt": workflow_data,
            "client_id": "zeni_precision_v10_client"
        }
        response = requests.post(f"{COMFYUI_URL}/prompt", json=data, timeout=10)
        if response.status_code == 200:
            return response.json().get('prompt_id')
        return None
    except Exception as e:
        st.error(f"提交失敗: {e}")
        return None

def check_generation_status(prompt_id):
    """檢查生成進度"""
    try:
        response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5)
        if response.status_code == 200:
            history = response.json()
            if prompt_id in history:
                return history[prompt_id]
        return None
    except:
        return None

def get_output_image(filename):
    """從 ComfyUI 獲取最終圖像"""
    try:
        response = requests.get(f"{COMFYUI_URL}/view?filename={filename}&type=output", timeout=30)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        return None
    except:
        return None

# ================= 界面佈局 =================
st.markdown('<p class="main-header">🐢 Zeni-Precision V10</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI Pose Transfer with Full-Control Precision</p>', unsafe_allow_html=True)
st.markdown("---")

# 側邊欄：系統狀態與全局控制
with st.sidebar:
    st.header("⚙️ 系統控制面板")
    
    # 連線診斷
    if check_comfyui_connection():
        st.success("🟢 ComfyUI 連線正常")
    else:
        st.error("🔴 ComfyUI 連線中斷")
        st.info("請確保 ComfyUI 已在 8188 端口啟動")
    
    st.markdown("---")
    
    # V10 精確度控制
    st.subheader("🎯 精確度調節")
    precision_level = st.slider(
        "姿勢精確度 (Precision Level)",
        min_value=0.1,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="低: 較多創意自由度 | 高: 嚴格遵循目標姿勢"
    )
    st.info(f"當前精確度: **{precision_level:.1f}**")
    
    if precision_level < 0.4:
        st.warning("⚠️ 模式：創意探索（可能偏離姿勢）")
    elif precision_level > 0.8:
        st.info("✨ 模式：精準對齊（嚴格遵循姿勢）")

# 主界面：輸入區
col1, col2 = st.columns(2)

with col1:
    st.subheader("🖼️ 來源圖像 (Source)")
    source_file = st.file_uploader("上傳原圖", type=["png", "jpg", "jpeg"], key="src_img")
    if source_file:
        st.image(source_file, caption="Source Image", use_column_width=True)

with col2:
    st.subheader("🧘 目標姿勢 (Target)")
    target_file = st.file_uploader("上傳姿勢圖", type=["png", "jpg", "jpeg"], key="tgt_img")
    if target_file:
        st.image(target_file, caption="Target Pose", use_column_width=True)

st.markdown("---")

# V9 恢復：文本控制區 (The Power-User Zone)
st.subheader("✍️ 精細控制指令 (Precision Control)")
c1, c2, c3 = st.columns(3)
with c1:
    p1 = st.text_area("背景描述 (Background)", value="high quality, masterpiece, clean background", help="定義生成圖的環境與品質")
with c2:
    p2 = st.text_area("核心指令 (Core Prompt)", value="A professional character pose transfer", help="定義主體的特徵與動作")
with c3:
    p3 = st.text_area("修改細節 (Details)", value="maintain facial features, sharp focus", help="對局部細節的微調要求")

# 執行按鈕
if st.button("🚀 開始執行 Pose Transfer", use_container_width=True):
    if not source_file or not target_file:
        st.error("❌ 請同時上傳來源圖與姿勢圖！")
    else:
        # 狀態顯示容器
        status_container = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # 1. 上傳圖像
            status_container.markdown('<div class="status-box">⚙️ 正在上傳圖像至 ComfyUI...</div>', unsafe_allow_html=True)
            progress_bar.progress(20)
            src_name = upload_image_to_comfyui(source_file)
            tgt_name = upload_image_to_comfyui(target_file)
            
            if not src_name or not tgt_name:
                st.error("❌ 圖像上傳失敗，請檢查連線。")
                st.stop()

            # 2. 構建工作流 (這裡簡化為模擬發送，實際會根據 p1,p2,p3,precision 注入 JSON)
            status_container.markdown(f'<div class="status-box">⚙️ 正在注入精確度參數 ({precision_level}) 與指令...</div>', unsafe_allow_html=True)
            progress_bar.progress(40)
            
            # 模擬 Workflow JSON 注入
            mock_workflow = {
                "p1": p1, "p2": p2, "p3": p3, 
                "precision": precision_level,
                "source": src_name, "target": tgt_name
            }
            
            prompt_id = queue_workflow(mock_workflow)
            if not prompt_id:
                st.error("❌ 提交工作流失敗！")
                st.stop()

            # 3. 輪詢狀態
            status_container.markdown(f'<div class="status-box">⚙️ 任務已進入隊列 (ID: {prompt_id})，正在等待生成...</div>', unsafe_allow_html=True)
            progress_bar.progress(60)
            
            max_retries = 60
            retry_count = 0
            final_image_name = None
            
            while retry_count < max_retries:
                status = check_generation_status(prompt_id)
                if status and 'outputs' in status:
                    # 獲取第一個輸出圖像文件名
                    output_node = status['outputs'].get('12', {}) # 假設 Node 12 是輸出節點
                    if output_node and 'images' in output_node:
                        final_image_name = output_node['images'][0]['filename']
                        break
                
                retry_count += 1
                time.sleep(2)
                if retry_count % 5 == 0:
                    status_container.markdown(f'<div class="status-box">⚙️ 正在處理圖像... (已等待 {retry_count*2}s)</div>', unsafe_allow_html=True)

            if final_image_name:
                status_container.markdown('<div class="status-box">✅ 生成成功！正在提取最終成像...</div>', unsafe_allow_html=True)
                progress_bar.progress(100)
                
                # 4. 獲取並顯示結果
                result_img = get_output_image(final_image_name)
                if result_img:
                    st.markdown("### 🎨 最終生成結果")
                    st.image(result_img, caption="Final Precision Result", use_column_width=True)
                    
                    # 保存到 Session 供下載
                    img_byte_arr = BytesIO()
                    result_img.save(img_byte_arr, format='PNG')
                    st.session_state['last_result'] = img_byte_arr.getvalue()
                    
                    st.success("🎉 任務完成！")
                else:
                    st.error("❌ 圖像生成成功但提取失敗。")
            else:
                st.error("❌ 生成超時或失敗，請檢查 ComfyUI 控制台。")
                
        except Exception as e:
            st.exception(f"系統運行時錯誤: {e}")
        finally:
            status_container.empty()
            progress_bar.empty()

# 下載區
if 'last_result' in st.session_state:
    st.markdown("---")
    st.download_button(
        label="💾 下載高解析成像圖",
        data=st.session_state['last_result'],
        file_name="zeni_precision_result.png",
        mime="image/png",
        use_container_width=True
    )
