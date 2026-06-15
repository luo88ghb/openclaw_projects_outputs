@echo off
chcp 65001 >nul
REM Start the local World Cup 2026 dashboard server.
REM This script will auto-kill any previous server on port 8765.
set TELEGRAM_BOT_TOKEN=8237046348:AAFQuJavHmL_dWu_ot3hciym6UiP7_UTneA
set TELEGRAM_CHAT_ID=8257517978
cd /d C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW
python engine\server.py
