@echo off
chcp 65001 > nul
cd /d "C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW"

:: Kill any existing server on port 8765
python -c "import os, signal, psutil; [os.kill(c.pid, signal.SIGTERM) for c in psutil.net_connections(kind='inet') if c.laddr.port == 8765 and c.status == psutil.CONN_LISTEN]" 2>nul

:: Write a PID file for the stop script
echo Starting World Cup 2026 Dashboard Server...
start "WC2026 Server" /MIN python engine/server.py

timeout /t 2 /nobreak > nul

echo.
echo Dashboard:  http://localhost:8765/index.html
echo Status API: http://localhost:8765/api/status
echo.
echo To stop, run stop_dashboard.bat or double-click it.
echo.
pause
