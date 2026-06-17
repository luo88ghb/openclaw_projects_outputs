#!/usr/bin/env pwsh
#Requires -Version 5.1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

function Write-Status($Level, $Message, $Color) {
    Write-Host ('[{0}] {1}' -f $Level, $Message) -ForegroundColor $Color
}

try {
    $conns = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 }
    if (-not $conns) {
        Write-Status -Level 'OK' -Message 'port 8765 not in use' -Color Green
        exit 0
    }
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        try {
            $proc = Get-Process -Id $pid -ErrorAction Stop
            Write-Status -Level 'STOP' -Message ('killing process {0} ({1})' -f $proc.Id, $proc.ProcessName) -Color Yellow
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Status -Level 'OK' -Message ('process {0} killed' -f $pid) -Color Green
        } catch {
            Write-Status -Level 'WARN' -Message ('cannot kill process {0}: {1}' -f $pid, $_.Exception.Message) -Color Red
        }
    }
    Start-Sleep -Seconds 2
    $remain = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 }
    if (-not $remain) {
        Write-Status -Level 'OK' -Message 'port 8765 fully released' -Color Green
    } else {
        Write-Status -Level 'WARN' -Message 'port 8765 still in use' -Color Red
    }
} catch {
    Write-Status -Level 'ERROR' -Message ('unexpected error: {0}' -f $_.Exception.Message) -Color Red
    exit 1
}
