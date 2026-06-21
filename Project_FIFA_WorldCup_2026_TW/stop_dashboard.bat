@echo off
chcp 65001 > nul

:: 停止 WC2026 Scheduler
python -c "import os, signal, psutil; [os.kill(p.info['pid'], signal.SIGTERM) for p in psutil.process_iter(['pid','cmdline']) for cmd in (' '.join(p.info['cmdline'] or []),) if 'engine/scheduler.py' in cmd and p.info['pid'] != os.getpid()]" 2>nul

:: 停止 WC2026 Server
python -c "import os, signal, psutil; [os.kill(p.info['pid'], signal.SIGTERM) for p in psutil.process_iter(['pid','cmdline']) for cmd in (' '.join(p.info['cmdline'] or []),) if 'engine/server.py' in cmd and p.info['pid'] != os.getpid()]" 2>nul

timeout /t 2 /nobreak > nul
echo Dashboard server and scheduler stopped (or were not running).
pause
