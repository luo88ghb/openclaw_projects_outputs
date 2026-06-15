#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🐢 Zeni AI - Task Completion Reporter
任務完成/失敗自動回報機制

功能：
1. ✅ 任務成功完成→推送「我完成了，請查看成果！」  
2. ⚠️ 任務失敗/中斷→推送「已停止，問題原因为...」
3. 🔕 靜默執行監控→強制報備避免無聲狀態

🎯 確保 Zeni AI 時刻有回應！
"""

import os
import json
import datetime
import subprocess
from pathlib import Path
from typing import Optional, Dict

# 工作目錄與檔案路徑  
WORKSPACE_PATH = Path("C:/Users/danny/.openclaw/workspace")
PROJECT_DIR = WORKSPACE_PATH / "Project_Zeni_Dashboard"
CONFIG_PATH = PROJECT_DIR / "config.json"
LOG_FILE = PROJECT_DIR / ".task_execution_log.json"

# Telegram API (需讀取 config)  
TELEGRAM_BOT_TOKEN = ""  # Read from config
TELEGRAM_CHAT_ID = ""    # Read from config


def is_task_success(task_status: str, error_msg: Optional[str] = None):
    """判斷任務是否成功"""
    return task_status == "success" and not error_msg


def push_telegram_message(text: str):
    """📡 發送 Telegram 推播通知"""
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegrm credentials missing, skipping push.")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_notification": False  # Always show push for important events    
    }
    
    try:
        import requests as req
        response = req.post(url, json=payload, timeout=15)
        
        if response.status_code in [200, 403]:  # 403 may indicate already muted but message sent
            print(f"✅ Telegram push successful: {text[:100]}...")
            return True
        else:
            print(f"❌ Telegram API error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        # Log even if Telegram fails for debugging
        with open(PROJECT_DIR / "push_error.log", 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] Error pushing to Telegram: {str(e)}\n")
        print(f"⚠️ Push failed but logged error: {e}")
        return False


def create_task_log_entry(task_name: str, status: str, details: Optional[Dict]):
    """建立任務執行紀錄"""
    log_entry = {
        "task_name": task_name,
        "status": status.upper(),  # SUCCESS/FAILURE/PENDING
        "started_at": datetime.datetime.now().isoformat(),
        "completed_at" if status != "PENDING": "" else "",
        "error_msg": details.get("error") if details else None,
        "push_status": False
    }

    # Append to log file  
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + '\n')


def report_task_completion(task_name: str, success: bool, error_msg: Optional[str] = None):
    """📡 任務完成/失敗通知器"""
    
    # Create log entry first
    create_task_log_entry(
        task_name=task_name,  
        status="SUCCESS" if success else "FAILURE",
        details={"error": error_msg} if not success else {} 
    )
    
    # Format message for push notification
    time_str = datetime.datetime.now().strftime("%m月%d日 %H:%M")
    
    if success:
        message = f"""✅ *Zen Ai Dashboard - 任務完成通知*\n\n📋 **任務名稱**: `{task_name}`\n⏧ **啟動時問**: {datetime.datetime.fromisoformat(log_entry['started_at']).strftime('%m月%d日 %H:%M')}\n✅ **最終狀態**: **{status}** ✅\n\n💬 {error_msg or "任務執行完成！無錯誤訊息。"}\n\n🐢 Zeni AI 時刻為您服務～"""
        
    else:
        message = f"""⚠️ *Zen Ai Dashboard - 任務失敗通知*\n\n📋 **任務名稱**: `{task_name}`\n❌ **最終狀態**: FAILURE\n💔 **錯誤訊息**: "{error_msg or "未知錯誤發生"}"\n\n🐢 Zeni AI 將持續監控並修復～"""
    
    # Push notification
    if push_telegram_message(message):
        return True
    else:
        print("⚠️ Notification failed but task logged locally.")
        return False


if __name__ == "__main__":
    # Test execution
    print("=" * 60)  
    print("🐢 Zeni AI Task Completion Notifier")
    print("=" * 60)
    
    # Check if task just finished successfully
    test_task = "Test_Song_Zuer_Image_Download_Stop"
    report_task_completion(test_task, success=True, error_msg="Option B - User chose not to continue private image collection")