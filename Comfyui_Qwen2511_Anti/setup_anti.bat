@echo off
echo ========================================================
echo 🛠️ Qwen-2511 Pose Transfer (Anti Edition) Setup Script
echo ========================================================

echo 📦 Step 1: Creating Conda Environment (comfy)...
call conda create -n comfy python=3.10 -y

echo 📦 Step 2: Installing Python dependencies...
call conda activate comfy
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install streamlit requests websocket-client Pillow huggingface_hub tqdm

echo ✅ Setup Complete. Please run start_anti_engine.bat to launch Streamlit UI.
pause
