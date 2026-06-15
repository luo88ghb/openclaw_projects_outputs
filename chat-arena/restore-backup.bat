@echo off
chcp 65001 > nul
title 回復備份 - game-server.js
color 0E

echo ========================================
echo    回復備份工具
echo ========================================
echo.

cd /d "%~dp0"

echo 可用的備份檔案：
echo.

set FOUND=0
if exist "game-server.js.pre-fix-backup-20260507" (
    echo   [1] game-server.js.pre-fix-backup-20260507  (第一次修復前)
    set FOUND=1
)
if exist "game-server.js.pre-fix2-backup-20260507" (
    echo   [2] game-server.js.pre-fix2-backup-20260507 (第二次修復前)
    set FOUND=1
)
if exist "game-server.js.v5-backup-20260430-001204" (
    echo   [3] game-server.js.v5-backup-20260430-001204 (v5 備份)
    set FOUND=1
)

if %FOUND%==0 (
    echo ❌ 找不到任何備份檔案！
    pause
    exit /b 1
)

echo.
set /p CHOICE=選擇要回復的備份 (1/2/3): 

if "%CHOICE%"=="1" set BACKUP_FILE=game-server.js.pre-fix-backup-20260507
if "%CHOICE%"=="2" set BACKUP_FILE=game-server.js.pre-fix2-backup-20260507
if "%CHOICE%"=="3" set BACKUP_FILE=game-server.js.v5-backup-20260430-001204

if not defined BACKUP_FILE (
    echo ❌ 無效的選擇。
    pause
    exit /b 1
)

echo.
echo ⚠️  將以 %BACKUP_FILE% 覆蓋目前的 game-server.js！
set /p CONFIRM=確認回復？(Y/N): 

if /i "%CONFIRM%"=="Y" (
    copy /Y "%BACKUP_FILE%" "game-server.js"
    echo.
    echo ✅ 已成功回復！
) else (
    echo.
    echo ⏹️ 已取消回復。
)

echo.
pause
