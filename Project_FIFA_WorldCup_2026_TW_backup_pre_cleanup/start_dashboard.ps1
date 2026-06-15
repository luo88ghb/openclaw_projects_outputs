# 啟動 2026 世界盃台灣時間儀表板與 API 服務
$projectDir = "C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW"
Set-Location $projectDir

# 使用虛擬環境（如果存在）
$venvPath = Join-Path $projectDir ".venv\Scripts\python.exe"
if (Test-Path $venvPath) {
    $python = $venvPath
} else {
    $python = "python"
}

# 啟動 Dashboard（前台）
Write-Host "啟動 Dashboard: http://localhost:8765/index.html" -ForegroundColor Green
Start-Process -NoNewWindow -FilePath $python -ArgumentList "engine/server.py"

# 啟動 API Server（前台）
Write-Host "啟動 API Server: http://localhost:8766" -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath $python -ArgumentList "engine/api_server.py"

Write-Host "兩個服務已啟動。按任意鍵關閉..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 結束進程
Get-Process python | Where-Object { $_.CommandLine -match "server.py|api_server.py" } | Stop-Process
