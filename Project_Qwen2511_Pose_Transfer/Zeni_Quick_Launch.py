import subprocess
import requests
import sys
import os
import time
import webbrowser

# ================= 配置區 =================
COMFYUI_URL = "http://127.0.0.1:8188"
ZENI_APP_PATH = r"C:\Users\danny\.openclaw\workspace\projects\Project_Qwen2511_Pose_Transfer\app.py"
# =========================================

def log(msg):
    """簡單日誌輸出"""
    print(f"[Zeni] {msg}")
    sys.stdout.flush()

def check_comfyui_quick():
    """快速檢查 ComfyUI"""
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
        return response.status_code == 200
    except:
        return False

def main():
    print("=" * 50)
    print("Zeni-Precision Quick Launcher")
    print("=" * 50)
    print()
    
    # 檢查 ComfyUI（快速模式）
    log("Checking ComfyUI...")
    if check_comfyui_quick():
        log("ComfyUI detected!")
    else:
        log("Could not auto-detect ComfyUI")
        log("")
        log("If ComfyUI is running in browser, type 'yes' to continue")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print()
            log("Exiting. Please start ComfyUI first:")
            log("  run_nvidia_gpu.bat")
            input("Press Enter to exit...")
            sys.exit(1)
    
    # 啟動 Zeni 界面
    print()
    log("Starting Zeni-Precision interface...")
    
    if not os.path.exists(ZENI_APP_PATH):
        log(f"ERROR: File not found: {ZENI_APP_PATH}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    try:
        subprocess.Popen(
            ["streamlit", "run", ZENI_APP_PATH, "--server.port", "8501"],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        time.sleep(3)
        log("Streamlit started. Browser should open automatically.")
        # Note: Streamlit auto-opens browser, we don't need to call webbrowser.open()
        
    except Exception as e:
        log(f"Failed to start: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # 完成
    print()
    print("=" * 50)
    log("Done! Zeni-Precision is running")
    print("=" * 50)
    print()
    print("URLs:")
    print("  ComfyUI: http://127.0.0.1:8188")
    print("  Zeni UI: http://localhost:8501")
    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
