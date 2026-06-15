# -*- coding: utf-8 -*-
"""
Gemma 4 E4B Q4_K_M Console 測試工具
===========================
純命令列版本，適合自動化測試
輸出 JSON 格式報告

作者：Zeni (傑尼)
更新：2026-05-09
"""

import subprocess
import time
import json
import sys
import os
from datetime import datetime

# ========== 常數 ==========
MAX_WAIT_SECONDS = 300  # 5分鐘超時
STALL_THRESHOLD = 30     # 30秒無進展視為停滯
MODEL_NAME = "gemma4:e4b-it-q4_K_M"

# ========== 任務定義 ==========
TASKS = [
    {
        "id": "academic_report",
        "name": "2K_學術報告",
        "prompt": "請你以學術論文風格，撰寫一篇關於「人工智慧對高等教育影響」的學術報告。\n\n要求：\n1. 包含摘要、引言、分析討論、結論\n2. 總字數約2,000字（中文字）\n3. 語氣正式，引用虛構但合理的研究數據\n4. 層次分明，每個章節有明確標題\n\n請開始撰寫：",
        "expected_tokens": 2000
    },
    {
        "id": "science_fiction",
        "name": "5K_科學小說",
        "prompt": "請你創作一篇科幻短篇小說，背景設在2145年的火星殖民地。\n\n要求：\n1. 情節完整：開端、發展、高潮、結局\n2. 主要角色至少2人，要有性格刻劃\n3. 主題涉及：AI情感、人機界線、孤獨與歸屬\n4. 總字數約5,000字（中文字）\n5. 場景描寫細緻，對話自然\n\n請開始創作：",
        "expected_tokens": 5000
    }
]

REASONING_QUESTIONS = [
    {
        "id": 1,
        "category": "邏輯推理",
        "question": "如果所有的A都是B，有些B是C，那麼以下哪個選項一定正確？\n(A) 有些A是C\n(B) 有些C是A\n(C) 所有B都是A\n(D) 有些B不是C\n請詳細解釋你的推論過程。"
    },
    {
        "id": 2,
        "category": "數學分析",
        "question": "請證明：若函數f(x)在[a,b]上連續，在(a,b)內可導，則存在c∈(a,b)使得\nf'(c) = [f(b) - f(a)] / (b - a)\n請詳細寫出證明過程。"
    },
    {
        "id": 3,
        "category": "物理思考",
        "question": "一物體在光滑水平面上以速度v向右運動，撞上一個靜止的相同質量物體，碰撞後兩者黏在一起運動。求：\n1. 碰撞後的共同速度\n2. 系統能量損失\n3. 這個碰撞是彈性還是非彈性？"
    },
    {
        "id": 4,
        "category": "程式設計",
        "question": "請用你熟悉的語言實現一個LRU Cache（最近最少使用快取），要求：\n1. 支援get和put操作，時間複雜度為O(1)\n2. 容量滿時自動淘汰最久未使用的項目\n3. 寫出完整的類別實現和簡單的使用範例。"
    },
    {
        "id": 5,
        "category": "批判思考",
        "question": "「人工智慧將在未來10年內取代大多數人類工作」這個論點，請分析：\n1. 支持這個論點的主要論據\n2. 反對這個論點的主要論據\n3. 你認為這個預測合理嗎？為什麼？\n請從技術、經濟、社會多個角度分析。"
    }
]

# ========== 工具函數 ==========
def print_json(data):
    """輸出 JSON（確保 UTF-8）"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def log(msg):
    """輸出日誌"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def check_model():
    """檢查模型是否就緒"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if MODEL_NAME in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return True, {"name": MODEL_NAME, "size": parts[2] if len(parts) > 2 else "unknown"}
            if "gemma4" in result.stdout:
                return True, {"name": "gemma4 (detected)", "size": "unknown"}
        return False, None
    except Exception as e:
        return False, str(e)

def run_task(task, timeout=MAX_WAIT_SECONDS, stall_threshold=STALL_THRESHOLD):
    """執行單一任務"""
    start_time = time.time()
    output_chunks = []
    total_tokens = 0
    last_update = start_time
    stalled = False
    timed_out = False

    log(f"開始任務：{task['name']}")

    try:
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )

        process.stdin.write(task["prompt"] + "\n")
        process.stdin.flush()
        process.stdin.close()

        for line in iter(process.stdout.readline, ''):
            elapsed = time.time() - start_time

            # 檢查超時
            if elapsed > timeout:
                timed_out = True
                log(f"⚠️ 任務超時（{timeout}秒），強制終止")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except:
                    process.kill()
                break

            line = line.strip()
            if not line:
                continue
            if line.startswith("[") or "prompt tokens" in line.lower() or "generate tokens" in line.lower():
                continue

            output_chunks.append(line)
            total_tokens += 1
            last_update = time.time()

            # 檢查停滯
            if time.time() - last_update > stall_threshold and not stalled:
                stalled = True
                log(f"⚠️ 任務可能停滯（{stall_threshold}秒無輸出）")
                sys.stdout.flush()

        process.wait()

    except Exception as e:
        log(f"錯誤：{e}")
        return {
            "task_id": task.get("id", "unknown"),
            "task_name": task.get("name", "unknown"),
            "success": False,
            "error": str(e),
            "tokens": 0,
            "elapsed": time.time() - start_time,
            "stalled": stalled,
            "timed_out": timed_out
        }

    elapsed = time.time() - start_time
    speed = total_tokens / elapsed if elapsed > 0 else 0
    full_output = "".join(output_chunks)

    result = {
        "task_id": task.get("id", "unknown"),
        "task_name": task.get("name", "unknown"),
        "success": not timed_out and not stalled,
        "tokens": total_tokens,
        "elapsed": round(elapsed, 2),
        "speed": round(speed, 2),
        "stalled": stalled,
        "timed_out": timed_out,
        "output_length": len(full_output),
        "output_preview": full_output[:500] + "..." if len(full_output) > 500 else full_output,
        "timestamp": datetime.now().isoformat()
    }

    log(f"完成：{task['name']} | {total_tokens} tokens | {elapsed:.1f}s | {speed:.1f} tokens/s")

    return result

def run_reasoning(question, timeout=MAX_WAIT_SECONDS, stall_threshold=STALL_THRESHOLD):
    """執行推論測驗"""
    start_time = time.time()
    output_chunks = []
    total_tokens = 0
    last_update = start_time
    stalled = False
    timed_out = False

    prompt = f"請回答以下問題，展現完整的推論過程：\n\n{question['question']}"

    log(f"開始推論題 #{question['id']}：{question['category']}")

    try:
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )

        process.stdin.write(prompt + "\n")
        process.stdin.flush()
        process.stdin.close()

        for line in iter(process.stdout.readline, ''):
            elapsed = time.time() - start_time

            if elapsed > timeout:
                timed_out = True
                log(f"⚠️ 推論題超時（{timeout}秒），強制終止")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except:
                    process.kill()
                break

            line = line.strip()
            if not line:
                continue
            if line.startswith("[") or "prompt tokens" in line.lower():
                continue

            output_chunks.append(line)
            total_tokens += 1
            last_update = time.time()

            if time.time() - last_update > stall_threshold and not stalled:
                stalled = True
                log(f"⚠️ 推論題可能停滯（{stall_threshold}秒無輸出）")
                sys.stdout.flush()

        process.wait()

    except Exception as e:
        log(f"錯誤：{e}")
        return {
            "question_id": question["id"],
            "category": question["category"],
            "success": False,
            "error": str(e),
            "tokens": 0,
            "elapsed": time.time() - start_time,
            "stalled": stalled,
            "timed_out": timed_out
        }

    elapsed = time.time() - start_time
    speed = total_tokens / elapsed if elapsed > 0 else 0
    full_output = "".join(output_chunks)

    result = {
        "question_id": question["id"],
        "category": question["category"],
        "success": not timed_out and not stalled,
        "tokens": total_tokens,
        "elapsed": round(elapsed, 2),
        "speed": round(speed, 2),
        "stalled": stalled,
        "timed_out": timed_out,
        "output_length": len(full_output),
        "output_preview": full_output[:500] + "..." if len(full_output) > 500 else full_output,
        "timestamp": datetime.now().isoformat()
    }

    log(f"完成：推論題 #{question['id']} | {total_tokens} tokens | {elapsed:.1f}s")

    return result

# ========== 主程序 ==========
def main():
    print("=" * 60, flush=True)
    print("Gemma 4 E4B Q4_K_M Console 測試工具 v1.2.0", flush=True)
    print(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 60, flush=True)

    # 檢查模型
    print("\n[1/4] 檢查模型狀態...", flush=True)
    available, info = check_model()
    if not available:
        result = {
            "status": "error",
            "message": "模型不可用",
            "model": MODEL_NAME,
            "timestamp": datetime.now().isoformat()
        }
        print_json(result)
        sys.exit(1)

    print(f"✓ 模型就緒：{info}", flush=True)

    # 執行寫作任務
    print("\n[2/4] 執行寫作任務...", flush=True)
    writing_results = []
    for task in TASKS:
        result = run_task(task)
        writing_results.append(result)
        print_json(result)

    # 執行推論測驗
    print("\n[3/4] 執行推論測驗...", flush=True)
    reasoning_results = []
    for q in REASONING_QUESTIONS:
        result = run_reasoning(q)
        reasoning_results.append(result)
        print_json(result)

    # 彙整報告
    print("\n[4/4] 生成報告...", flush=True)

    total_tokens = sum(r.get("tokens", 0) for r in writing_results + reasoning_results)
    total_time = sum(r.get("elapsed", 0) for r in writing_results + reasoning_results)
    avg_speed = total_tokens / total_time if total_time > 0 else 0
    success_count = sum(1 for r in writing_results + reasoning_results if r.get("success"))
    total_count = len(writing_results) + len(reasoning_results)

    summary = {
        "test_session": {
            "model": MODEL_NAME,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "timeout": MAX_WAIT_SECONDS,
            "stall_threshold": STALL_THRESHOLD
        },
        "summary": {
            "total_tests": total_count,
            "successful": success_count,
            "failed": total_count - success_count,
            "success_rate": f"{success_count / total_count * 100:.1f}%",
            "total_tokens": total_tokens,
            "total_time_seconds": round(total_time, 2),
            "average_speed_tokens_per_second": round(avg_speed, 2)
        },
        "writing_results": writing_results,
        "reasoning_results": reasoning_results
    }

    print("\n" + "=" * 60, flush=True)
    print("測試報告摘要", flush=True)
    print("=" * 60, flush=True)
    print(f"總測試數：{total_count}", flush=True)
    print(f"成功：{success_count} | 失敗：{total_count - success_count}", flush=True)
    print(f"總Tokens：{total_tokens}", flush=True)
    print(f"總耗時：{total_time:.1f}秒", flush=True)
    print(f"平均速度：{avg_speed:.1f} tokens/s", flush=True)
    print("=" * 60, flush=True)

    # 寫入檔案
    report_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f"console_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n報告已儲存：{report_file}", flush=True)
    print_json(summary)

if __name__ == "__main__":
    main()