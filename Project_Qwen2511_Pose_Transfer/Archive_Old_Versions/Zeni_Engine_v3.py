import sys
import os

# 強制將 Anaconda 的 site-packages 加入路徑最前面
anaconda_path = r"C:\Users\danny\anaconda3\Lib\site-packages"
if anaconda_path not in sys.path:
    sys.path.insert(0, anaconda_path)

# 強制開啟高速下載模式
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

import streamlit as st
import torch
from PIL import Image
from diffusers import QwenImageEditPlusPipeline

# --- 1. 介面與視覺 ---
st.set_page_config(page_title="Zeni-Core Image Engine v3.1 (16GB VRAM Optimized)", layout="wide")
st.markdown("<style>.main { background-color: #0d1117; color: #00f2ff; }</style>", unsafe_allow_html=True)

@st.cache_resource
def load_zeni_diffuser():
    model_id = "Qwen/Qwen-Image-Edit-2511"
    
    # 16GB VRAM 救星配置
    st.write("🐢 正在啟動『顯存節約模式』...")
    
    pipeline = QwenImageEditPlusPipeline.from_pretrained(
        model_id, 
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        # 不在這裡直接 .to('cuda')，而是使用後面的 offload
    )
    
    # 核心優化：模型 CPU 卸載
    # 這會讓模型在運算時才把當前需要的零件丟進顯存，算完就丟回 RAM
    pipeline.enable_model_cpu_offload()
    
    # 顯存優化：VAE 切片運算，防止生成大圖時顯存爆炸
    pipeline.enable_vae_slicing()
    
    # 顯存優化：Tiling 運算
    pipeline.enable_vae_tiling()
    
    return pipeline

st.markdown('### 🐢 傑尼引擎 V3.1：16GB 顯存優化版')
st.sidebar.warning("⚡ 已啟動零件輪替技術 (CPU Offload)，適合 16GB VRAM 環境。")

col1, col2 = st.columns(2)
with col1:
    subj = st.file_uploader("👤 人物原圖", type=['png', 'jpg', 'jpeg'], key="subj")
    if subj: st.image(subj, width=400)
with col2:
    pose = st.file_uploader("💃 姿勢參考", type=['png', 'jpg', 'jpeg'], key="pose")
    if pose: st.image(pose, width=400)

prompt = st.text_input("📝 指令", value="Maintain identity of Image 1, use pose of Image 2.")

if st.button("🔥 執行深度融合 (低顯存模式)"):
    if subj and pose:
        with st.status("🐢 正在運算中...", expanded=True) as status:
            pipeline = load_zeni_diffuser()
            
            st.write("影像預處理...")
            img1 = Image.open(subj).convert("RGB")
            img2 = Image.open(pose).convert("RGB")
            
            inputs = {
                "image": [img1, img2],
                "prompt": prompt,
                "generator": torch.manual_seed(42),
                "true_cfg_scale": 3.5, # 稍微降低一點點增加穩定性
                "negative_prompt": "low quality, blurry, distorted, messy background",
                "num_inference_steps": 25, # 步數設為 25，在 CPU Offload 下平衡速度與品質
                "guidance_scale": 1.0,
                "num_images_per_prompt": 1,
            }

            st.write("核心噴圖中... 顯存零件切換中...")
            with torch.inference_mode():
                output = pipeline(**inputs)
                output_image = output.images[0]
            
            st.image(output_image, caption="融合結果", use_container_width=True)
            
            save_path = "output_zeni_v3_optimized.png"
            output_image.save(save_path)
            status.update(label="✅ 融合成功！", state="complete")
            st.success(f"結果已存至: {os.path.abspath(save_path)}")
    else:
        st.error("🐢 資料不足，無法啟動。")
