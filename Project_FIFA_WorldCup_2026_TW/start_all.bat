@echo off
chcp 65001 > nul
cd /d "C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW"

:: Telegram bot credentials (must be set for notifications to work)
set TELEGRAM_BOT_TOKEN=8237046348:AAFQuJavHmL_dWu_ot3hciym6UiP7_UTneA
set TELEGRAM_CHAT_ID=8257517978

:: Daily summary notifications (1 = on, 0 = off)
set DAILY_PRE_NOTIFY=1
set DAILY_POST_NOTIFY=1

:: Kill any existing server / scheduler to avoid duplicate processes
python -c "import os, signal, psutil; [os.kill(p.info['pid'], signal.SIGTERM) for p in psutil.process_iter(['pid','cmdline']) for cmd in (' '.join(p.info['cmdline'] or []),) if 'engine/server.py' in cmd or 'engine/scheduler.py' in cmd if p.info['pid'] != os.getpid()]" 2>nul

:: Also release port 8765 as a fallback
python -c "import os, signal, psutil; [os.kill(c.pid, signal.SIGTERM) for c in psutil.net_connections(kind='inet') if c.laddr.port == 8765 and c.status == psutil.CONN_LISTEN]" 2>nul

timeout /t 2 /nobreak > nul

echo Starting World Cup 2026 Dashboard Server...
start "WC2026 Server" /MIN python engine/server.py

timeout /t 2 /nobreak > nul

echo Starting Time-Correction Scheduler...
start "WC2026 Scheduler" /MIN python engine/scheduler.py

echo.
echo Dashboard:  http://localhost:8765/index.html
echo SSE stream: http://localhost:8765/update-stream
echo Status API: http://localhost:8765/api/status
echo.
echo To stop everything, run stop_all.bat (stops both server and scheduler).
echo.
pause
