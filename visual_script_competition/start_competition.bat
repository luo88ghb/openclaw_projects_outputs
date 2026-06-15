@echo off
chcp 65001 >nul 2>&1
echo ================================================
echo Visual Script Competition - Launcher v0.6
echo ================================================
echo.

REM Force kill any existing node processes for this project
echo [Step 0] Cleaning up old processes...
taskkill /F /IM node.exe >nul 2>&1
timeout /t 1 >nul
echo [OK] All Node processes terminated
echo.

REM Navigate to project directory
cd /d "%~dp0"
echo [DEBUG] Working directory: %cd%
echo.

REM Ensure required files exist
echo [Step 1] Checking files...
if not exist "server.js" (
    echo [ERROR] server.js not found!
    pause
    exit /b 1
)
if not exist "viewer.html" (
    echo [ERROR] viewer.html not found!
    pause
    exit /b 1
)
echo [OK] All files present

REM Initialize data files if missing
echo.
echo [Step 2] Initializing data files...
if not exist "visual_scoreboard.json" (
    echo { "rounds": [], "cumulative": { "dini": 0, "xixia": 0 } } > "visual_scoreboard.json"
    echo [OK] visual_scoreboard.json created
) else (
    echo [OK] visual_scoreboard.json exists
)

if not exist "server.log" (
    echo [INIT] Log file created > "server.log"
    echo [OK] server.log created
) else (
    echo [OK] server.log exists
)

REM Check Node.js
echo.
echo [Step 3] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found!
    pause
    exit /b 1
)
echo [OK] Node.js OK

REM Start server with clear window title
echo.
echo [Step 4] Starting server on port 3000...
start "VisualArena_Server" cmd /k "cd /d \"%~dp0\" && node server.js"
echo [OK] Server started (check the new window)
echo.

REM Wait for server to initialize
echo [Step 5] Waiting for server initialization...
timeout /t 3 >nul
echo [OK] Wait complete

REM Open viewer in browser
echo.
echo [Step 6] Opening viewer.html...
start "" "%~dp0\viewer.html"
echo [OK] Viewer opened in browser
echo.

echo ================================================
echo SUCCESS! Check the server window for status.
echo The viewer should show "迪尼: 0 | 蝦蝦: 0"
echo ================================================
pause
exit /b 0