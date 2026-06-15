@echo off
title Zeni-Precision Launcher v3.0
chcp 65001 >nul
echo ============================================
echo    Zeni-Precision System Launcher
echo    [ComfyUI Portable Mode]
echo ============================================
echo.
echo [INFO] Steps to be executed:
echo        1. Check if ComfyUI is running
echo        2. Launch ComfyUI (if needed)
echo        3. Launch Zeni-Precision interface
echo        4. Open browser automatically
echo.
echo [INFO] Please do not close this window
echo        It displays all status messages
echo ============================================
echo.
timeout /t 3 /nobreak >nul
echo [Zeni-Launcher] Starting Python launcher...
echo.
python "C:\Users\danny\.openclaw\workspace\projects\Project_Qwen2511_Pose_Transfer\Zeni_Launch_Auto.py"
echo.
pause
