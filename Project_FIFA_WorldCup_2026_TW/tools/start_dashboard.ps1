#!/usr/bin/env pwsh
#Requires -Version 5.1
# 一鍵啟動 2026 世界盃儀表板
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$BaseDir = Split-Path -Parent $PSScriptRoot
$ServerScript = Join-Path (Join-Path $BaseDir 'engine') 'server.py'
$SchedulerScript = Join-Path (Join-Path $BaseDir 'engine') 'scheduler.py'

function Write-Status($Level, $Message, $Color) {
    Write-Host ('[{0}] {1}' -f $Level, $Message) -ForegroundColor $Color
}

try {
    # Step 1: clear port 8765
    try {
        $conns = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 }
        if ($conns) {
            Write-Status -Level 'INFO' -Message 'port 8765 bei zhanyong, xian guanbi jincheng' -Color Yellow
            $conns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
                try { Stop-Process -Id $_ -Force -ErrorAction Stop } catch {}
            }
            Start-Sleep -Seconds 2
        }
    } catch {
        Write-Status -Level 'WARN' -Message ('qingli port 8765 cuowu: {0}' -f $_.Exception.Message) -Color Red
    }

    # Step 2: check files
    if (-not (Test-Path $ServerScript)) {
        Write-Status -Level 'ERROR' -Message ('server script bucunzai: {0}' -f $ServerScript) -Color Red
        exit 1
    }
    if (-not (Test-Path $SchedulerScript)) {
        Write-Status -Level 'WARN' -Message ('scheduler script bucunzai: {0}, tiaoguo' -f $SchedulerScript) -Color Yellow
    }

    # Step 3: start server
    try {
        Start-Process -FilePath 'python' -ArgumentList (''' + $ServerScript + ''') -WindowStyle Hidden -WorkingDirectory $BaseDir -ErrorAction Stop
        Write-Status -Level 'OK' -Message 'Dashboard server yiqidong' -Color Green
    } catch {
        Write-Status -Level 'ERROR' -Message ('qidong server shibai: {0}' -f $_.Exception.Message) -Color Red
        exit 1
    }

    # Step 4: start scheduler
    if (Test-Path $SchedulerScript) {
        Start-Sleep -Seconds 2
        try {
            Start-Process -FilePath 'python' -ArgumentList (''' + $SchedulerScript + ''') -WindowStyle Hidden -WorkingDirectory $BaseDir -ErrorAction Stop
            Write-Status -Level 'OK' -Message 'Scheduler yiqidong' -Color Green
        } catch {
            Write-Status -Level 'WARN' -Message ('qidong scheduler shibai: {0}' -f $_.Exception.Message) -Color Red
        }
    }

    # Step 5: verify
    Start-Sleep -Seconds 3
    $verify = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
    if ($verify) {
        Write-Status -Level 'OK' -Message 'port 8765 jianting zhengchang' -Color Green
        Write-Status -Level 'GO' -Message ('Dashboard: http://localhost:8765/index.html') -Color Cyan
    } else {
        Write-Status -Level 'WARN' -Message 'port 8765 weijianting, qing shougong jiancha' -Color Red
    }

    Write-Status -Level 'OK' -Message 'start_dashboard wancheng' -Color Green
} catch {
    Write-Status -Level 'ERROR' -Message ('weiyuqi cuowu: {0}' -f $_.Exception.Message) -Color Red
    exit 1
}
