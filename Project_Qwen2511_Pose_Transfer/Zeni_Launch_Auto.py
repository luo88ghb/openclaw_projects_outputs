import subprocess
import requests
import sys
import os
import time
import webbrowser
from pathlib import Path

# ================= 配置區 =================
COMFYUI_BAT_PATH = r"D:\AI\ComfyUI_windows_portable\run_nvidia_gpu.bat"
COMFYUI_URL = "http://127.0.0.1:8188"
ZENI_APP_PATH = r"C:\Users\danny\.openclaw\workspace\projects\Project_Qwen2511_Pose_Transfer\app.py"
# =========================================

def log_step(step_num, total_steps, message):
    """統一輸出格式，強制使用 UTF-8 編碼避免亂碼"""
    try:
        # 嘗試設定 stdout 為 UTF-8 模式
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except:
        pass
    
    output = f"[Zeni-Launcher] Step {step_num}/{total_steps}: {message}"
    print(output)
    sys.stdout.flush()

def check_comfyui_status():
    """檢查 ComfyUI API 是否響應"""
    try:
        response = requests.get(f"{COMFYUI_URL}/api", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_comfyui_with_bat():
    """使用原始 bat 檔啟動 ComfyUI（GUI 模式）"""
    log_step(2, 4, "Launching ComfyUI via run_nvidia_gpu.bat")
    log_step(2, 4, f"Path: {COMFYUI_BAT_PATH}")
    
    try:
        # 使用 CREATE_NEW_CONSOLE 讓 ComfyUI 在新視窗運行
        # 不阻塞主程序
        process = subprocess.Popen(
            [COMFYUI_BAT_PATH],
            shell=True,
            cwd=os.path.dirname(COMFYUI_BAT_PATH),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        log_step(2, 4, "ComfyUI launch command sent")
        log_step(2, 4, "Waiting for API response (this may take 60-120 seconds)...")
        
        # 輪詢等待 API 響應，最長等待 120 秒
        max_retries = 60  # 60 * 2 = 120 seconds
        for i in range(max_retries):
            time.sleep(2)
            if check_comfyui_status():
                log_step(2, 4, f"ComfyUI API is online (Port: 8188)")
                return True
            
            # 每 10 秒顯示一次進度
            if (i + 1) % 5 == 0:
                elapsed = (i + 1) * 2
                print(f"[Zeni-Launcher] Still waiting... ({elapsed}/{max_retries*2}s)")
                print(f"[Zeni-Launcher] ComfyUI is loading models, please be patient...")
                sys.stdout.flush()
        
        log_step(2, 4, "Timeout waiting for API response")
        return False
        
    except Exception as e:
        log_step(2, 4, f"Launch failed: {str(e)}")
        return False

def launch_zeni_interface():
    """啟動 Streamlit Zeni 界面"""
    log_step(3, 4, "Launching Zeni-Precision interface...")
    
    # 檢查 app.py 是否存在
    if not os.path.exists(ZENI_APP_PATH):
        log_step(3, 4, f"ERROR: Interface file not found: {ZENI_APP_PATH}")
        log_step(3, 4, "Please ensure app.py is in the correct location")
        return False
    
    try:
        # 啟動 Streamlit，使用新視窗
        cmd = ["streamlit", "run", ZENI_APP_PATH, "--server.port", "8501"]
        log_step(3, 4, f"Command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        log_step(3, 4, "Streamlit starting... (waiting 5 seconds)")
        time.sleep(5)
        
        # 自動打開瀏覽器
        webbrowser.open("http://localhost:8501")
        log_step(3, 4, "Browser opened: http://localhost:8501")
        return True
        
    except Exception as e:
        log_step(3, 4, f"Interface launch failed: {str(e)}")
        return False

def main():
    # 設置 UTF-8 編碼
    import codecs
    if sys.platform == 'win32':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    print("=" * 60)
    print("Zeni-Precision: One-Click System Launcher v3.0")
    print("[ComfyUI Portable Mode - Extended Wait]")
    print("=" * 60)
    print()
    
    # 步驟 1: 檢查 ComfyUI 是否已在運行
    log_step(1, 4, "Checking if ComfyUI is already running...")
    if check_comfyui_status():
        log_step(1, 4, "ComfyUI is already running")
    else:
        log_step(1, 4, "ComfyUI not detected, will launch...")
    
    # 步驟 2: 啟動 ComfyUI（如果尚未運行）
    if check_comfyui_status():
        log_step(2, 4, "ComfyUI already running, skipping launch")
    else:
        if not start_comfyui_with_bat():
            print()
            print("=" * 60)
            print("ERROR: Failed to start ComfyUI")
            print(f"Please check: {COMFYUI_BAT_PATH}")
            print("=" * 60)
            input("\nPress Enter to exit...")
            sys.exit(1)
    
    # 步驟 3: 啟動 Zeni 界面
    if not launch_zeni_interface():
        print()
        print("=" * 60)
        print("ERROR: Failed to launch Zeni interface")
        print("=" * 60)
        input("Press Enter to exit...")
        sys.exit(1)
    
    # 步驟 4: 完成
    print()
    print("=" * 60)
    log_step(4, 4, "All components running!")
    print("=" * 60)
    print()
    print("Status:")
    print("  ComfyUI API: http://127.0.0.1:8188 (GUI mode)")
    print("  Zeni UI:     http://localhost:8501")
    print()
    print("NOTE: Do not close this window, it maintains the backend service")
    print()
    
    # 保持視窗開啟
    input("Press Enter to exit and close all services...")

if __name__ == "__main__":
    main()
