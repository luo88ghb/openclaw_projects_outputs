@echo off
chcp 65001 >nul
REM 完全停止 2026 世界盃儀表板相關程序

echo [Stop] 正在停止 port 8765 上的 server...
python -c "import os, signal, psutil; [os.kill(c.pid, signal.SIGTERM) for c in psutil.net_connections(kind='inet') if c.laddr.port == 8765]" 2>nul

echo [Stop] 正在停止所有相關 Python 程序...
for /f "tokens=2" %%i in ('tasklist ^| findstr "python"') do (
    taskkill /PID %%i /F /FI "WINDOWTITLE eq WC2026 Server" >nul 2>&1
    taskkill /PID %%i /F /FI "WINDOWTITLE eq WC2026 Scheduler" >nul 2>&1
)

echo [Stop] 完成。
pause
