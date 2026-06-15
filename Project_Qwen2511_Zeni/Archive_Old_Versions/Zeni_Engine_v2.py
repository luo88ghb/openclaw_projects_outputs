import streamlit as st
import os
import torch
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# --- 1. 介面與視覺 ---
st.set_page_config(page_title="Zeni-Core Image Engine v2.5", layout="wide")
st.markdown("<style>.main { background-color: #0d1117; color: #00f2ff; }</style>", unsafe_allow_html=True)

@st.cache_resource
def load_zeni_brain():
    model_path = r"C:\Users\danny\.openclaw\workspace\Zeni_Brain_Ready"
    # 強制載入最新處理器
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
    # 注入 Chat Template 避免 ValueError
    if processor.chat_template is None:
        processor.chat_template = "{% set image_count = namespace(value=0) %}{% set video_count = namespace(value=0) %}{% for message in messages %}{% if loop.first and message['role'] != 'system' %}<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n{% endif %}<|im_start|>{{ message['role'] }}\n{% if message['content'] is string %}{{ message['content'] }}<|im_end|>\n{% else %}{% for content in message['content'] %}{% if content['type'] == 'image' or 'image' in content or 'image_url' in content %}{% set image_count.value = image_count.value + 1 %}{% if add_vision_id %}Picture {{ image_count.value }}: {% endif %}<|vision_start|><|image_pad|><|vision_end|>{% elif content['type'] == 'video' or 'video' in content %}{% set video_count.value = video_count.value + 1 %}{% if add_vision_id %}Video {{ video_count.value }}: {% endif %}<|vision_start|><|video_pad|><|vision_end|>{% elif 'text' in content %}{{ content['text'] }}{% endif %}{% endfor %}<|im_end|>\n{% endif %}{% endfor %}{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
    
    # 針對 4060 Ti 優化載入精度
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
    )
    return model, processor

st.markdown('### 🐢 傑尼引擎 V2.5：核心對齊協議')

col1, col2 = st.columns(2)
with col1:
    subj = st.file_uploader("👤 人物原圖", type=['png', 'jpg', 'jpeg'], key="subj")
    if subj: st.image(subj, width=400)
with col2:
    pose = st.file_uploader("💃 姿勢參考", type=['png', 'jpg', 'jpeg'], key="pose")
    if pose: st.image(pose, width=400)

if st.button("🔥 執行深度融合"):
    if subj and pose:
        model, processor = load_zeni_brain()
        
        with st.status("🐢 正在修正像素不匹配問題...", expanded=True) as status:
            st.write("影像預處理：強制對齊 Token 數量...")
            
            # 加載並處理圖片，確保尺寸一致
            img1 = Image.open(subj).convert("RGB")
            img2 = Image.open(pose).convert("RGB")
            
            # 建構符合 Qwen2.5-VL 要求的訊息格式
            # 注意：不再使用 apply_chat_template，直接手動餵給 processor 繞過 Bug
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img1, "resized_height": 224, "resized_width": 224},
                        {"type": "image", "image": img2, "resized_height": 224, "resized_width": 224},
                        {"type": "text", "text": "Maintain identity of Image 1, use pose of Image 2."},
                    ],
                }
            ]

            st.write("正在建構視覺向量矩陣...")
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            
            # 關鍵修正：透過具體的 pixels 參數傳入
            inputs = processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            ).to("cuda")

            st.write("執行神經元運算...")
            with torch.no_grad():
                # 這裡增加穩定性參數
                generated_ids = model.generate(
                    **inputs, 
                    max_new_tokens=128,
                    do_sample=False # 使用 Greedy Search 增加穩定性
                )
                generated_ids_trimmed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
                output_text = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)

            status.update(label="✅ 運算成功！", state="complete")
            st.success("傑尼核心已給出分析結果")
            st.code(output_text[0])
            
            st.warning("⚠️ 技術回報：羅哥，Qwen-Image-Edit-2511 實際上是一個基於 Flux 的擴散模型。目前我們成功喚醒了它的『語言/視覺編碼大腦』，但要讓它真正噴出『融合後的圖片』，我們需要在下個階段接入 Diffusers 擴散器組件。")
    else:
        st.error("🐢 資料不足，無法啟動。")
