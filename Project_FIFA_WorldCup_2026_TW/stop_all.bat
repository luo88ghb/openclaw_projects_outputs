@echo off
chcp 65001 > nul
REM 完全停止 2026 世界盃儀表板：server + scheduler

echo [Stop] 正在停止 WC2026 Scheduler...
python -c "import os, signal, psutil; [os.kill(p.info['pid'], signal.SIGTERM) for p in psutil.process_iter(['pid','cmdline']) for cmd in (' '.join(p.info['cmdline'] or []),) if 'engine/scheduler.py' in cmd and p.info['pid'] != os.getpid()]" 2>nul

echo [Stop] 正在停止 WC2026 Server...
python -c "import os, signal, psutil; [os.kill(p.info['pid'], signal.SIGTERM) for p in psutil.process_iter(['pid','cmdline']) for cmd in (' '.join(p.info['cmdline'] or []),) if 'engine/server.py' in cmd and p.info['pid'] != os.getpid()]" 2>nul

:: 備援：強制終止所有相關 Python 程序（避免殘留）
timeout /t 1 /nobreak > nul
taskkill /F /FI "WINDOWTITLE eq WC2026 Server" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq WC2026 Scheduler" >nul 2>&1

echo [Stop] 完成。
pause
