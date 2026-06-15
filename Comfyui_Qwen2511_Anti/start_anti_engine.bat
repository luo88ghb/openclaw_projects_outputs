@echo off
echo ========================================================
echo 🚀 Qwen-2511 Pose Transfer (Anti Edition) UI Launcher
echo ========================================================

:: 檢查 comfy Conda 環境是否存在
if not exist "C:\Users\danny\anaconda3\envs\comfy\Scripts\python.exe" (
    echo ❌ 找不到 Conda 'comfy' 環境。請先執行 setup_anti.bat！
    pause
    exit /b
)

echo ⚙️ 正在啟用 comfy Conda 環境...
call conda activate comfy

echo 🖥️ 正在啟動 Streamlit 跑圖引擎...
streamlit run Anti_Engine.py

pause
