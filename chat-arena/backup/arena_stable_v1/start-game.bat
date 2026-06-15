@echo off
chcp 65001 > nul
title 🐢 vs 🎨 推論猜謎對決 - 遊戲伺服器
color 0A

echo ========================================
echo    🐢 vs 🎨 推論猜謎對決
echo    遊戲伺服器啟動中...
echo ========================================
echo.

cd /d "%~dp0"
cd "C:\Users\danny\.openclaw\workspace\chat-arena"

REM Check if node_modules exists, if not install
if not exist "node_modules" (
    echo 📦 首次運行，正在安裝依賴...
    npm install
    echo.
)

echo 🌐 啟動遊戲伺服器...
echo.
echo 📍 網頁界面：http://localhost:3001
echo 📍 API 端點：http://localhost:3001/api/state
echo.
echo 按 Ctrl+C 停止伺服器
echo ========================================
echo.

node game-server.js

pause