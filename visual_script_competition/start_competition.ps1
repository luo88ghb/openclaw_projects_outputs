#!/usr/bin/env pwsh
# start_competition.ps1 – 啟動視覺氛圍劇本比賽
# 1. 進入競賽資料夾
Set-Location -Path "C:/Users/danny/.openclaw/workspace/visual_script_competition"

# 2. 若尚未安裝依賴，先安裝 (假設有 package.json)
if (Test-Path "package.json") {
    Write-Host "安裝 npm 依賴..."
    npm install
}

# 3. 啟動比賽伺服器 (假設 server.js 實作比賽邏輯)
Write-Host "啟動比賽伺服器..."
# 使用 nohup 讓程式持續執行，並把輸出寫入 log
nohup node server.js > server.log 2>&1 &
$pid = $!
Write-Host "伺服器已在背景執行，PID=$pid"

# 4. 開啟 GUI 瀏覽器觀看狀態（viewer.html）
$viewer = "file://" + (Resolve-Path "viewer.html")
Start-Process $viewer

Write-Host "比賽已啟動，請在瀏覽器中檢視 $viewer"
