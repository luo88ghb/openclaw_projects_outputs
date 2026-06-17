#!/usr/bin/env pwsh
#Requires -Version 5.1
# 安全清理 port 8765
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

function Write-Status($Level, $Message, $Color) {
    Write-Host ('[{0}] {1}' -f $Level, $Message) -ForegroundColor $Color
}

try {
    $conns = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 }
    if (-not $conns) {
        Write-Status -Level 'OK' -Message 'port 8765 meiyou process' -Color Green
        exit 0
    }
    $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $procIds) {
        try {
            $proc = Get-Process -Id $procId -ErrorAction Stop
            Write-Status -Level 'STOP' -Message ('guanbi process {0} ({1})' -f $proc.Id, $proc.ProcessName) -Color Yellow
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Status -Level 'OK' -Message ('process {0} yiguanbi' -f $procId) -Color Green
        } catch {
            Write-Status -Level 'WARN' -Message ('wufa guanbi process {0}: {1}' -f $procId, $_.Exception.Message) -Color Red
        }
    }
    Start-Sleep -Seconds 2
    $remain = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 }
    if (-not $remain) {
        Write-Status -Level 'OK' -Message 'port 8765 yishifang' -Color Green
    } else {
        Write-Status -Level 'WARN' -Message 'port 8765 rengbei zhanyong' -Color Red
    }
} catch {
    Write-Status -Level 'ERROR' -Message ('qingli port 8765 shibai: {0}' -f $_.Exception.Message) -Color Red
    exit 1
}
