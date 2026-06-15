@echo off
chcp 65001 > nul
title 🐢 推論猜謎對決 - 遊戲引擎 v4.1
color 0A

echo ========================================
echo    🐢 推論猜謎對決
echo    遊戲引擎 v4.1 啟動中...
echo ========================================
echo.

cd /d "%~dp0"
cd "C:\Users\danny\.openclaw\workspace\chat-arena"

REM 設置環境變數
set OPENCLAW_TOKEN=
set GATEWAY_HOST=127.0.0.1
set GATEWAY_PORT=18789

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
echo 🔧 診斷資訊：
echo    Gateway Host: %GATEWAY_HOST%
echo    Gateway Port: %GATEWAY_PORT%
echo    Token: （從配置文件讀取）
echo.
echo 按 Ctrl+C 停止伺服器
echo ========================================
echo.

node game-server.js

pause
