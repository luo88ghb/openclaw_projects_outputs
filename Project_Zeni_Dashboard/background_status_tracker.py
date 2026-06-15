#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zeni AI Dashboard - Background Work Status Tracker
顯示 Zeni AI 執行後台工作的動態符号系統 🐢

功能：
1. ⏱️ 追蹤 Cron Job 執行狀態 (Daily_Token_Report, OpenClaw Version Check, etc.)
2. 🔍 監控 Python Scripts 持續運行狀態 (如 session_status API polling)
3. 📊 提供動態 symbol 給 Dashboard UI 使用
"""

import os
import json
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Dict, Tuple

# Project root workspace path
WORKSPACE_PATH = Path("C:/Users/danny/.openclaw/workspace")
PROJECT_DIR = WORKSPACE_PATH / "Project_Zeni_Dashboard"
STATUS_FILE = PROJECT_DIR / ".background_status.json"

# Dynamic Status Symbols (Emoji)
SYMBOLS = {
    # 執行中 Icons
    "running": {"main": ⚙️, "cron": 🔄, "api_poll": 📡},
    # 等待中 Icons
    "pending": {"main": ☕, "cron": ⏰, "api_poll": 💤},
    # 成功/完成 Icons
    "completed": {"main": ✅, "cron": ✔️, "api_poll": ⚡},
    # 失敗/Error Icons
    "failed": {"main": ❌, "cron": ⚠️, "api_poll": 🥴},
    # 休眠狀態
    "sleeping": {"main": 💤, "cron": 🔋, "api_poll": 🧘}
}

# Active Background Jobs (Cron + Scripts)
ACTIVE_JOBS = [
    {
        "name": "Daily_Token_Report_2300",
        "type": "cron_job",
        "schedule": "每日 23:00",
        "last_run": None,
        "status": "pending",
        "duration_minutes": 15
    },
    {
        "name": "Task_Progress_Report_Heartbeat",
        "type": "cron_job", 
        "schedule": "每 7 分鐘 heartbeat",
        "last_run": None,
        "status": "running",
        "duration_minutes": 30,
        "interval": 420000  # 每 7 分鐘
    },
    {
        "name": "OpenClaw_Version_Check_1200", 
        "type": "cron_job",
        "schedule": "每日中午 12:00",
        "last_run": None,
        "status": "pending",
        "duration_minutes": 20
    },
    {
        "name": "SQLite_Backup_Schedule",
        "type": "cron_job",
        "schedule": "每日 05:30", 
        "last_run": None,
        "status": "sleeping"
    },
]

# Active Monitoring Jobs (Scripts)
MONITORING_JOBS = [
    {
        "name": "session_status_api_poller",
        "type": "python_script",
        "script_path": WORKSPACE_PATH / ".openclaw/workflows/session_status.py",
        "status": "running",
        "duration_minutes": 15,
        "consecutive_updates": 3,
        "update_interval_seconds": 60
    },
]


def load_status():
    """載入背景工作狀態"""
    if STATUS_FILE.exists():
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            status = json.load(f)
            print("✅ Loaded background status from file")
            return status
    else:
        # Initial empty state  
        save_status()
        return {"jobs": [], "timestamp": datetime.datetime.now().isoformat()}


def save_status():
    """保存背景工作狀態"""
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(ACTIVE_JOBS + MONITORING_JOBS, f, ensure_ascii=False, default=str)


def update_job_status(job_name: str, status: str):
    """更新特定 Job 狀態"""
    for job in ACTIVE_JOBS + MONITORING_JOBS:
        if job["name"] == job_name:
            job["status"] = status
            # Update timestamp
            job["last_run"] = datetime.datetime.now().isoformat() if status == "completed" else None
            return True
    
    return False


def get_zenicon(status: str) -> str:
    """根據狀態回傳動態 symbol"""
    icon_type = "main"  # Default icon type
    if status == "cron": 
        icon_type = "cron"
    elif status == "api_poll":
        icon_type = "api_poll"
    
    return SYMBOLS[status]["main"] if hasattr(SYMBOLS[status], "main") else SYMBOLS["pending"]["main"]


def check_job_health():
    """檢查 Job 健康狀態"""
    results = []
    
    now = datetime.datetime.now()
    
    # Check last heartbeat (7 minutes)  
    for job in ACTIVE_JOBS:
        if job["type"] == "cron_job" and job.get("schedule", "").find("心跳") != -1: 
            last_run_str = job.get("last_run", "")
            if last_run_str:
                last_run = datetime.datetime.fromisoformat(last_run_str)
                elapsed = (now - last_run).total_seconds() / 60
        
        if elapsed < 30  # Within heartbeats
            update_job_status(job["name"], "running")
            
    # Check monitoring api poller status
    for job in MONITORING_JOBS:
             name = job["name"]
             script_path = job.get("script_path", None)
             
             if script_path and os.path.exists(script_path):
                 try:
                     with open(script_path, 'r', encoding='utf-8') as f:
                         content = f.read()
                         if "running" in content or "polling" in content.lower():
                             update_job_status(name, "running")
                         elif "completed" in content.lower():
                             update_job_status(name, "completed")
                 except Exception as e:
                     print(f"❌ Error checking job health: {e}")
                     
    return results


def get_dashboard_summary() -> Tuple[str, list]:
    """生成 Dashboard 用的簡要摘要"""
    
    # Get status symbol for main display
    now = datetime.datetime.now()
    if ACTIVE_JOBS[1]["status"] == "running": 
        zenicon = ⚙️  # Active heartbeat running
        status_text = f"背景工作中：{ACTIVE_JOBS[0]['name']} (最後執行：{ACTIVE_JOBS[0].get('last_run', '待定')[:19]})" 
    else:  
        zenicon = ☕  # Idle/waiting  
        status_text = "Zeni AI 已閒置中，等待指令..."

    return {
        "zenicon": zenicon,
        "status": status_text,
        "jobs_count": sum(1 for j in ACTIVE_JOBS if j.get("duration_minutes", 0) > 0),
        "last_heartbeat": datetime.datetime.now().strftime("%H:%M"),
        "active_jobs": [j["name"] for j in ACTIVE_JOBS if j.get("status") in ["running", "completed"]]
    }


def show_status():
    """顯示當前工作狀態詳情"""
    
    print("=" * 60)
    summary = get_dashboard_summary()
    print(f"🐢 {summary['zenicon']} Zeni AI 背景工作狀態：{summary['status']}")
    print(f"⏰ 最後心跳時刻：{summary['last_heartbeat']}")
    
    print("\n📋 Active Jobs:")
    for job in ACTIVE_JOBS:
        status = job.get("status", "unknown")
        print(f"   {job['name']}: {SYMBOLS[status]['cron']} {job['schedule']}")

        
def check_job_status(job_name):
    """查詢特定 Job 狀態"""
    for job in ACTIVE_JOBS + MONITORING_JOBS:
       if job["name"] == job_name:  
            status = job.get("status", "unknown")
            icon = SYMBOLS[status]["cron" if job["type"] == "cron_job" else "main"] 
            return {
                "job": job_name,
                "status": status.upper(), 
                "icon": icon,
                "last_run": job.get("last_run", "No data yet")[:16],
                "schedule": job.get("schedule", None)
             } 
    return None


if __name__ == "__main__":  
    show_status()
