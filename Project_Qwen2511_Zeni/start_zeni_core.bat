@echo off
echo ========================================================
echo 🚀 Qwen-2511 Pose Transfer (Zeni Edition) Core Launcher
echo ========================================================
:: Verify that the comfy environment exists
if not exist "%UserProfile%\anaconda3\envs\comfy\python.exe" (
    echo ❌ ComfyUI Environment not found. Please run setup_comfy.bat first.
    pause
    exit /b
)
:: Activate the comfy environment
call "%UserProfile%\anaconda3\Scripts\conda.exe" activate comfy
echo 🛰️ Starting ComfyUI Core via comfy-cli...
"%UserProfile%\anaconda3\envs\comfy\python.exe" -m comfy_cli start --port 8188 --cpu-offload
if %ERRORLEVEL% EQU 0 (
    echo ✅ Core Engine started successfully on http://127.0.0.1:8188
) else (
    echo 🔴 Failed to start Core Engine.
)
pause