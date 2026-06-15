@echo off
title Zeni-Precision Quick Launcher
echo ============================================
echo    Zeni-Precision Quick Launcher
echo ============================================
echo.
echo Step 1: Ensure ComfyUI is running first!
echo         (Run run_nvidia_gpu.bat manually)
echo.
echo Step 2: This launcher will start Zeni UI
echo.
echo ============================================
echo.
timeout /t 2 >nul
python "%~dp0Zeni_Quick_Launch.py"
