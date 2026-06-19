@echo off
chcp 65001 > nul

:: Try graceful shutdown via API first
curl.exe -s --max-time 3 -X POST http://localhost:8765/api/shutdown > nul 2>&1
if %errorlevel% == 0 (
    echo Dashboard server shutdown request sent.
)

:: Also kill any process listening on port 8765 (covers scheduler and fallback)
python -c "import os, signal, psutil; [os.kill(c.pid, signal.SIGTERM) for c in psutil.net_connections(kind='inet') if c.laddr.port == 8765 and c.status == psutil.CONN_LISTEN]" 2>nul

:: Kill scheduler by script name
python -c "import os, signal, psutil, sys; [os.kill(p.pid, signal.SIGTERM) for p in psutil.process_iter(['pid', 'name', 'cmdline']) if p.info['name'] == 'python.exe' and p.info['cmdline'] and any('scheduler.py' in arg for arg in p.info['cmdline'])]" 2>nul

timeout /t 2 /nobreak > nul
echo Dashboard server and scheduler stopped (or were not running).
pause
