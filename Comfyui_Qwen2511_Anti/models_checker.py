import os
import sys
import requests
from pathlib import Path

# 預設 ComfyUI 模型根目錄
DEFAULT_MODELS_DIR = r"D:\AI\ComfyUI_windows_portable\ComfyUI\models"

# 6 個姿勢遷移必要模型定義
MODELS_CONFIG = {
    "unet": {
        "name": "Qwen UNet 基底模型 (fp8mixed)",
        "sub_dir": "diffusion_models/[ Qwen ]",
        "filename": "qwen_image_edit_2511_fp8mixed.safetensors",
        "url": "https://huggingface.co/f5aiteam/Qwen-Image-Edit-2511/resolve/main/qwen_image_edit_2511_fp8mixed.safetensors"
    },
    "clip": {
        "name": "Qwen 2.5 VL CLIP 文本編碼器",
        "sub_dir": "text_encoders",
        "filename": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "url": "https://huggingface.co/f5aiteam/Qwen-Image-Edit-2511/resolve/main/qwen_2.5_vl_7b_fp8_scaled.safetensors"
    },
    "vae": {
        "name": "Qwen 影像 VAE 模型",
        "sub_dir": "vae",
        "filename": "qwen_image_vae.safetensors",
        "url": "https://huggingface.co/f5aiteam/Qwen-Image-Edit-2511/resolve/main/qwen_image_vae.safetensors"
    },
    "lora_lightning": {
        "name": "Qwen Image Edit 4步蒸餾 LoRA",
        "sub_dir": "loras/[ Qwen ]",
        "filename": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
        "url": "https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning/resolve/main/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
    },
    "lora_anypose_base": {
        "name": "AnyPose 姿勢轉移 Base LoRA",
        "sub_dir": "loras/[ Qwen ]",
        "filename": "2511-AnyPose-base-000006250.safetensors",
        "url": "https://huggingface.co/lilylilith/AnyPose/resolve/main/2511-AnyPose-base-000006250.safetensors"
    },
    "lora_anypose_helper": {
        "name": "AnyPose 姿勢轉移 Helper LoRA",
        "sub_dir": "loras/[ Qwen ]",
        "filename": "2511-AnyPose-helper-00006000.safetensors",
        "url": "https://huggingface.co/lilylilith/AnyPose/resolve/main/2511-AnyPose-helper-00006000.safetensors"
    }
}

def get_target_path(model_key, base_dir=DEFAULT_MODELS_DIR):
    config = MODELS_CONFIG[model_key]
    # 使用 Path 合併路徑並處理 Windows 的斜線
    return Path(base_dir) / config["sub_dir"].replace("/", os.sep).replace("\\", os.sep) / config["filename"]

def check_models(base_dir=DEFAULT_MODELS_DIR):
    """檢查所有模型是否存在"""
    results = {}
    for key, config in MODELS_CONFIG.items():
        target_path = get_target_path(key, base_dir)
        exists = target_path.exists()
        size_mb = 0
        if exists:
            size_mb = target_path.stat().st_size / (1024 * 1024)
        results[key] = {
            "name": config["name"],
            "filename": config["filename"],
            "path": str(target_path),
            "exists": exists,
            "size_mb": size_mb,
            "url": config["url"]
        }
    return results

def download_model(model_key, base_dir=DEFAULT_MODELS_DIR, progress_callback=None):
    """下載指定模型"""
    config = MODELS_CONFIG[model_key]
    target_path = get_target_path(model_key, base_dir)
    
    # 建立父資料夾
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    url = config["url"]
    temp_path = target_path.with_suffix(".download")
    
    headers = {}
    # 支援續傳
    if temp_path.exists():
        downloaded_bytes = temp_path.stat().st_size
        headers["Range"] = f"bytes={downloaded_bytes}-"
    else:
        downloaded_bytes = 0

    response = requests.get(url, headers=headers, stream=True, timeout=30)
    
    if response.status_code == 416:
        # Range Not Satisfiable，代表已下載完成或大小有異
        if temp_path.exists():
            os.replace(temp_path, target_path)
        return True
    
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0)) + downloaded_bytes
    mode = "ab" if downloaded_bytes > 0 else "wb"
    
    with open(temp_path, mode) as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded_bytes += len(chunk)
                if progress_callback:
                    progress_callback(downloaded_bytes, total_size)
                else:
                    # CLI 簡單進度顯示
                    percent = (downloaded_bytes / total_size) * 100 if total_size > 0 else 0
                    sys.stdout.write(f"\rDownloading {config['filename']}: {percent:.2f}% ({downloaded_bytes/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB)")
                    sys.stdout.flush()
    
    if progress_callback:
        progress_callback(total_size, total_size)
    print("\nDownload finished.")
    
    # 下載完成後重新命名為 safetensors
    if temp_path.exists():
        os.replace(temp_path, target_path)
    return True

if __name__ == "__main__":
    # 解決 Windows 控制台 cp950 編碼問題，強設定為 utf-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("=== Comfyui_Qwen2511_Anti 模型檢查工具 ===")
    print(f"掃描模型根路徑: {DEFAULT_MODELS_DIR}\n")
    
    scan_results = check_models()
    all_ok = True
    missing_keys = []
    
    for key, info in scan_results.items():
        status = f"已存在 ({info['size_mb']:.1f} MB)" if info["exists"] else "缺失"
        # 終端機安全輸出
        try:
            status_emoji = "🟢 " + status if info["exists"] else "🔴 " + status
            print(f"- {info['name']} ({info['filename']}): {status_emoji}")
        except UnicodeEncodeError:
            status_text = "[O] " + status if info["exists"] else "[X] " + status
            print(f"- {info['name']} ({info['filename']}): {status_text}")
        if not info["exists"]:
            all_ok = False
            missing_keys.append(key)
            
    if all_ok:
        try:
            print("\n🎉 所有必要模型皆已齊備！")
        except UnicodeEncodeError:
            print("\n[OK] 所有必要模型皆已齊備！")
    else:
        try:
            print("\n⚠️ 偵測到模型缺失。")
        except UnicodeEncodeError:
            print("\n[!] 偵測到模型缺失。")
        choice = input("是否要開始下載缺失的模型？(y/N): ").strip().lower()
        if choice == 'y':
            for key in missing_keys:
                print(f"\n開始下載: {scan_results[key]['name']}")
                try:
                    download_model(key)
                except Exception as e:
                    try:
                        print(f"\n❌ 下載失敗: {str(e)}")
                    except UnicodeEncodeError:
                        print(f"\n[Error] 下載失敗: {str(e)}")
        else:
            print("已取消下載。")
