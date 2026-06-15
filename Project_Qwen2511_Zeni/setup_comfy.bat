@echo off
echo ========================================================
echo 🛠️ Qwen-2511 Pose Transfer (Zeni Edition) Setup Script
echo ========================================================

:: Ensure conda is initialized for this shell
call "%UserProfile%\anaconda3\Scripts\conda.exe" init cmd

echo 📦 Step 1: Creating Conda Environment...
call "%UserProfile%\anaconda3\Scripts\conda.exe" create -n comfy python=3.10 -y


echo 📦 Step 2: Installing Core Dependencies...
call "%UserProfile%\anaconda3\Scripts\conda.exe" activate comfy
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install streamlit requests websocket-client Pillow


echo 📦 Step 3: Installing ComfyUI & comfy-cli...
pip install comfy-cli


echo ✅ Setup Complete. Please run start_zeni_core.bat to launch.
pause