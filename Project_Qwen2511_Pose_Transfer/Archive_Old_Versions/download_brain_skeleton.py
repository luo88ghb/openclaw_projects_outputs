import os
import requests
from pathlib import Path

# --- 設定 ---
MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct" # 使用相容的基礎骨架
BASE_URL = f"https://huggingface.co/{MODEL_ID}/resolve/main/"
FILES = [
    "config.json",
    "generation_config.json",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "tokenizer.json"
]

TARGET_DIR = Path(r"C:\Users\danny\.openclaw\workspace\Zeni_Brain_Ready")
SOURCE_WEIGHTS = r"D:\AI\ComfyUI_windows_portable\ComfyUI\models\diffusion_models\[ Qwen ]\qwen_image_edit_2511_fp8mixed.safetensors"

def download_skeleton():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🐢 傑尼正在從賽博空間下載大腦骨架...")

    for file_name in FILES:
        url = BASE_URL + file_name
        target_path = TARGET_DIR / file_name
        
        if not target_path.exists():
            print(f"正在下載: {file_name}...")
            response = requests.get(url)
            if response.status_code == 200:
                with open(target_path, "wb") as f:
                    f.write(response.content)
                print(f"✅ {file_name} 下載成功")
            else:
                print(f"❌ {file_name} 下載失敗: {response.status_code}")
        else:
            print(f"⏩ {file_name} 已存在，跳過")

    # 建立權重連結
    target_link = TARGET_DIR / "model.safetensors"
    if not target_link.exists():
        print(f"🔗 正在建立權重連結...")
        try:
            # 使用 Windows cmd 的 mklink 指令來避免權限問題
            cmd = f'mklink "{target_link}" "{SOURCE_WEIGHTS}"'
            os.system(cmd)
            print("✅ 權重對接完成！")
        except Exception as e:
            print(f"❌ 連結失敗: {e}")
    
    print("\n🐢 大腦組裝完成！現在傑尼已經擁有完整的身分證與肌肉了。")
    print(f"大腦位置: {TARGET_DIR}")

if __name__ == "__main__":
    download_skeleton()
