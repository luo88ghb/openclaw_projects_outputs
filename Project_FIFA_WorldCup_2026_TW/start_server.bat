@echo off
chcp 65001 >nul
REM 一鍵啟動 2026 世界盃儀表板（會先自動殺掉舊程序）

set TELEGRAM_BOT_TOKEN=8237046348:AAFQuJavHmL_dWu_ot3hciym6UiP7_UTneA
set TELEGRAM_CHAT_ID=8257517978

:: Daily summary notifications (1 = on, 0 = off)
set DAILY_PRE_NOTIFY=1
set DAILY_POST_NOTIFY=1

cd /d "C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW"

echo [Start] 檢查並關閉既有 server...
python -c "import os, signal, psutil; [os.kill(c.pid, signal.SIGTERM) for c in psutil.net_connections(kind='inet') if c.laddr.port == 8765]" 2>nul

timeout /t 1 /nobreak >nul

echo [Start] 啟動 Dashboard Server...
start "WC2026 Server" python engine\server.py

timeout /t 2 /nobreak >nul

echo [Start] 啟動 Time-Correction Scheduler...
start "WC2026 Scheduler" python engine\scheduler.py

echo.
echo ============================================
echo  Dashboard:  http://localhost:8765/index.html
echo  SSE stream: http://localhost:8765/update-stream
echo ============================================
echo.
pause
