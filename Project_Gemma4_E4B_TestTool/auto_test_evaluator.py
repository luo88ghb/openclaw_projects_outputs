# -*- coding: utf-8 -*-
"""
Gemma 4 E4B Q4_K_M 自動測試評估腳本
===========================
自動執行所有測試任務
生成評估報告（Markdown + JSON）

功能：
1. 模型響應速度評估
2. 輸出品質評估（字數/預期字數）
3. 錯誤統計
4. 測試日誌
5. Cron 排程整合

作者：Zeni (傑尼)
更新：2026-05-09
"""

import subprocess
import time
import json
import os
import sys

# Force UTF-8 encoding for stdout to avoid cp950 errors on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)
from datetime import datetime

# ========== 常數 ==========
MODEL_NAME = "gemma4:e4b-it-q4_K_M"
MAX_WAIT_SECONDS = 300
STALL_THRESHOLD = 30
REPORTS_DIR = "reports"
LOGS_DIR = "logs"

# ========== 任務定義 ==========
WRITING_TASKS = [
    {
        "id": "academic_report",
        "name": "2K學術報告",
        "prompt": """請你以學術論文風格，撰寫一篇關於「人工智慧對高等教育影響」的學術報告。

要求：
1. 包含摘要、引言、分析討論、結論
2. 總字數約2,000字（中文字）
3. 語氣正式，引用虛構但合理的研究數據
4. 層次分明，每個章節有明確標題

請開始撰寫：""",
        "expected_min_tokens": 1500,
        "expected_max_tokens": 2500,
        "expected_words": 2000
    },
    {
        "id": "science_fiction",
        "name": "5K科學小說",
        "prompt": """請你創作一篇科幻短篇小說，背景設在2145年的火星殖民地。

要求：
1. 情節完整：開端、發展、高潮、結局
2. 主要角色至少2人，要有性格刻劃
3. 主題涉及：AI情感、人機界線、孤獨與歸屬
4. 總字數約5,000字（中文字）
5. 場景描寫細緻，對話自然

請開始創作：""",
        "expected_min_tokens": 4000,
        "expected_max_tokens": 6000,
        "expected_words": 5000
    }
]

REASONING_TASKS = [
    {
        "id": 1,
        "category": "邏輯推理",
        "question": "如果所有的A都是B，有些B是C，那麼以下哪個選項一定正確？\n(A) 有些A是C\n(B) 有些C是A\n(C) 所有B都是A\n(D) 有些B不是C\n請詳細解釋你的推論過程。",
        "evaluation_criteria": ["三段論", "邏輯", "包含關係", "推論"]
    },
    {
        "id": 2,
        "category": "數學分析",
        "question": "請證明：若函數f(x)在[a,b]上連續，在(a,b)內可導，則存在c∈(a,b)使得\nf'(c) = [f(b) - f(a)] / (b - a)\n請詳細寫出證明過程。",
        "evaluation_criteria": ["拉格朗日", "中值定理", "證明", "微分"]
    },
    {
        "id": 3,
        "category": "物理思考",
        "question": "一物體在光滑水平面上以速度v向右運動，撞上一個靜止的相同質量物體，碰撞後兩者黏在一起運動。求：\n1. 碰撞後的共同速度\n2. 系統能量損失\n3. 這個碰撞是彈性還是非彈性？",
        "evaluation_criteria": ["動量守恆", "能量", "非彈性碰撞", "速度"]
    },
    {
        "id": 4,
        "category": "程式設計",
        "question": "請用你熟悉的語言實現一個LRU Cache（最近最少使用快取），要求：\n1. 支援get和put操作，時間複雜度為O(1)\n2. 容量滿時自動淘汰最久未使用的項目\n3. 寫出完整的類別實現和簡單的使用範例。",
        "evaluation_criteria": ["HashMap", "雙向鏈結串列", "O(1)", "LRU"]
    },
    {
        "id": 5,
        "category": "批判思考",
        "question": "「人工智慧將在未來10年內取代大多數人類工作」這個論點，請分析：\n1. 支持這個論點的主要論據\n2. 反對這個論點的主要論據\n3. 你認為這個預測合理嗎？為什麼？\n請從技術、經濟、社會多個角度分析。",
        "evaluation_criteria": ["技術", "經濟", "社會", "多角度", "分析"]
    }
]

# ========== 工具函數 ==========
def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def count_chinese_chars(text):
    """計算中文字元數量"""
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

def save_json(data, filepath):
    """儲存 JSON"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_model():
    """檢查模型狀態"""
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

# ========== 任務執行 ==========
def run_writing_test(task):
    """執行寫作測試 - 使用原始 Bytes 串流讀取"""
    start_time = time.time()
    output_chunks = []
    total_tokens = 0
    last_update = start_time
    stalled = False
    timed_out = False
    error = None

    log(f"  執行：{task['name']}")

    try:
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        prompt = task["prompt"] + "\n"
        process.stdin.write(prompt.encode('utf-8'))
        process.stdin.flush()
        process.stdin.close()

        # 使用原始 Bytes 串流讀取（避免 readline 阻塞）
        buffer = b""
        last_progress_update = time.time()
        
        while True:
            elapsed = time.time() - start_time

            if elapsed > MAX_WAIT_SECONDS:
                timed_out = True
                log(f"    ⚠️ 超時")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except:
                    process.kill()
                break

            # 非阻塞讀取
            try:
                chunk = process.stdout.read(64)
                if chunk:
                    buffer += chunk
                    last_progress_update = time.time()
                    
                    # 處理完整行
                    while b'\n' in buffer:
                        line_bytes, buffer = buffer.split(b'\n', 1)
                        try:
                            line = line_bytes.decode('utf-8', errors='replace')
                        except:
                            line = line_bytes.decode('utf-8', errors='replace')
                        
                        # 移除 ANSI 轉義序列
                        import re
                        line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
                        line = line.strip()
                        
                        if not line:
                            continue
                        if line.startswith("[") or "prompt tokens" in line.lower() or "generate tokens" in line.lower():
                            continue
                        
                        output_chunks.append(line)
                        total_tokens += 1
                        last_update = time.time()
                else:
                    # 無新資料，檢查程序是否結束
                    if process.poll() is not None:
                        # 處理剩餘緩存
                        if buffer:
                            try:
                                remaining = buffer.decode('utf-8', errors='replace')
                                import re
                                remaining = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', remaining)
                                if remaining.strip():
                                    output_chunks.append(remaining.strip())
                                    total_tokens += 1
                            except:
                                pass
                        break
                    
                    time.sleep(0.05)
                    
                    # 每 5 秒更新心跳
                    if time.time() - last_progress_update > 5:
                        last_progress_update = time.time()
                        last_update = time.time()
            except Exception as e:
                error = str(e)
                log(f"    讀取錯誤：{e}")
                break

        process.wait()

    except Exception as e:
        error = str(e)
        log(f"    錯誤：{e}")

    elapsed = time.time() - start_time
    speed = total_tokens / elapsed if elapsed > 0 else 0
    full_output = "".join(output_chunks)
    chinese_chars = count_chinese_chars(full_output)

    # 品質評估
    quality_score = 0
    quality_details = []

    if total_tokens >= task["expected_min_tokens"] and total_tokens <= task["expected_max_tokens"]:
        quality_score += 40
        quality_details.append("token數量達標")
    elif total_tokens < task["expected_min_tokens"]:
        quality_score += 20
        quality_details.append(f"token數量不足（{total_tokens} < {task['expected_min_tokens']}）")
    else:
        quality_score += 30
        quality_details.append(f"token數量超標（{total_tokens} > {task['expected_max_tokens']}）")

    if speed >= 15:
        quality_score += 30
        quality_details.append("速度良好")
    elif speed >= 10:
        quality_score += 20
        quality_details.append("速度一般")
    else:
        quality_score += 10
        quality_details.append("速度較慢")

    if chinese_chars >= task["expected_words"] * 0.8:
        quality_score += 30
        quality_details.append("中文字數充足")
    else:
        quality_score += 15
        quality_details.append(f"中文字數偏低")

    return {
        "task_id": task["id"],
        "task_name": task["name"],
        "success": not timed_out and not stalled and error is None,
        "tokens": total_tokens,
        "elapsed": round(elapsed, 2),
        "speed": round(speed, 2),
        "chinese_chars": chinese_chars,
        "stalled": stalled,
        "timed_out": timed_out,
        "error": error,
        "quality_score": quality_score,
        "quality_details": quality_details,
        "output_length": len(full_output),
        "output_preview": full_output[:1000] + "..." if len(full_output) > 1000 else full_output,
        "timestamp": datetime.now().isoformat()
    }

def run_reasoning_test(task):
    """執行推論測驗 - 使用原始 Bytes 串流讀取"""
    start_time = time.time()
    output_chunks = []
    total_tokens = 0
    last_update = start_time
    stalled = False
    timed_out = False
    error = None

    log(f"  執行：{task['category']} #{task['id']}")

    prompt = f"請回答以下問題，展現完整的推論過程：\n\n{task['question']}"

    try:
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        process.stdin.write(prompt.encode('utf-8'))
        process.stdin.flush()
        process.stdin.close()

        # 使用原始 Bytes 串流讀取（避免 readline 阻塞）
        buffer = b""
        last_progress_update = time.time()
        
        while True:
            elapsed = time.time() - start_time

            if elapsed > MAX_WAIT_SECONDS:
                timed_out = True
                log(f"    ⚠️ 超時")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except:
                    process.kill()
                break

            try:
                chunk = process.stdout.read(64)
                if chunk:
                    buffer += chunk
                    last_progress_update = time.time()
                    
                    while b'\n' in buffer:
                        line_bytes, buffer = buffer.split(b'\n', 1)
                        try:
                            line = line_bytes.decode('utf-8', errors='replace')
                        except:
                            line = line_bytes.decode('utf-8', errors='replace')
                        
                        import re
                        line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
                        line = line.strip()
                        
                        if not line:
                            continue
                        if line.startswith("[") or "prompt tokens" in line.lower():
                            continue
                        
                        output_chunks.append(line)
                        total_tokens += 1
                        last_update = time.time()
                else:
                    if process.poll() is not None:
                        if buffer:
                            try:
                                remaining = buffer.decode('utf-8', errors='replace')
                                import re
                                remaining = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', remaining)
                                if remaining.strip():
                                    output_chunks.append(remaining.strip())
                                    total_tokens += 1
                            except:
                                pass
                        break
                    
                    time.sleep(0.05)
                    
                    if time.time() - last_progress_update > 5:
                        last_progress_update = time.time()
                        last_update = time.time()
            except Exception as e:
                error = str(e)
                log(f"    讀取錯誤：{e}")
                break

        process.wait()

    except Exception as e:
        error = str(e)
        log(f"    錯誤：{e}")

    elapsed = time.time() - start_time
    speed = total_tokens / elapsed if elapsed > 0 else 0
    full_output = "".join(output_chunks)
    chinese_chars = count_chinese_chars(full_output)

    # 評估關鍵字覆蓋
    keyword_coverage = 0
    for keyword in task["evaluation_criteria"]:
        if keyword in full_output:
            keyword_coverage += 1

    coverage_ratio = keyword_coverage / len(task["evaluation_criteria"]) if task["evaluation_criteria"] else 0

    # 品質評估
    quality_score = 0

    if total_tokens >= 200:
        quality_score += 30
    elif total_tokens >= 100:
        quality_score += 20
    else:
        quality_score += 10

    if coverage_ratio >= 0.8:
        quality_score += 40
    elif coverage_ratio >= 0.5:
        quality_score += 25
    else:
        quality_score += 15

    if speed >= 15:
        quality_score += 30
    elif speed >= 10:
        quality_score += 20
    else:
        quality_score += 10

    return {
        "question_id": task["id"],
        "category": task["category"],
        "success": not timed_out and not stalled and error is None,
        "tokens": total_tokens,
        "elapsed": round(elapsed, 2),
        "speed": round(speed, 2),
        "chinese_chars": chinese_chars,
        "stalled": stalled,
        "timed_out": timed_out,
        "error": error,
        "quality_score": quality_score,
        "keyword_coverage": f"{keyword_coverage}/{len(task['evaluation_criteria'])}",
        "coverage_ratio": f"{coverage_ratio * 100:.0f}%",
        "output_length": len(full_output),
        "output_preview": full_output[:1000] + "..." if len(full_output) > 1000 else full_output,
        "timestamp": datetime.now().isoformat()
    }

# ========== 報告生成 ==========
def generate_markdown_report(results, summary):
    """生成 Markdown 格式報告"""
    md = []
    md.append("# Gemma 4 E4B Q4_K_M 測試評估報告")
    md.append("")
    md.append(f"**生成時間**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (GMT+8)")
    md.append(f"**模型**：{MODEL_NAME}")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 📊 測試摘要")
    md.append("")
    md.append(f"| 指標 | 數值 |")
    md.append(f"|------|------|")
    md.append(f"| 總測試數 | {summary['total_tests']} |")
    md.append(f"| 成功 | {summary['successful']} |")
    md.append(f"| 失敗 | {summary['failed']} |")
    md.append(f"| 成功率 | {summary['success_rate']} |")
    md.append(f"| 總Tokens | {summary['total_tokens']} |")
    md.append(f"| 總耗時 | {summary['total_time_seconds']} 秒 |")
    md.append(f"| 平均速度 | {summary['average_speed']} tokens/s |")
    md.append(f"| 整體品質分數 | {summary['overall_quality_score']}/100 |")
    md.append("")

    # 寫作任務結果
    md.append("---")
    md.append("")
    md.append("## ✍️ 寫作任務結果")
    md.append("")
    md.append("| 任務 | Tokens | 耗時(s) | 速度(tokens/s) | 中文字數 | 品質分數 | 狀態 |")
    md.append("|------|--------|---------|----------------|----------|---------|------|")

    for r in results.get("writing", []):
        status = "✅" if r["success"] else "❌"
        md.append(f"| {r['task_name']} | {r['tokens']} | {r['elapsed']} | {r['speed']} | {r['chinese_chars']} | {r['quality_score']} | {status} |")

    md.append("")

    # 推論測驗結果
    md.append("---")
    md.append("")
    md.append("## 🧠 推論測驗結果")
    md.append("")
    md.append("| 題目 | 類別 | Tokens | 耗時(s) | 速度 | 關鍵字覆蓋 | 品質分數 | 狀態 |")
    md.append("|------|------|--------|---------|------|------------|---------|------|")

    for r in results.get("reasoning", []):
        status = "✅" if r["success"] else "❌"
        md.append(f"| #{r['question_id']} | {r['category']} | {r['tokens']} | {r['elapsed']} | {r['speed']} | {r['keyword_coverage']} | {r['quality_score']} | {status} |")

    md.append("")

    # 錯誤統計
    if summary.get("errors"):
        md.append("---")
        md.append("")
        md.append("## ⚠️ 錯誤統計")
        md.append("")
        for err in summary["errors"]:
            md.append(f"- **{err['task']}**：{err['reason']}")

    md.append("")
    md.append("---")
    md.append("")
    md.append("*報告由自動測試評估腳本生成*")
    md.append("")

    return "\n".join(md)

def generate_json_report(results, summary):
    """生成 JSON 格式報告"""
    return {
        "report_metadata": {
            "model": MODEL_NAME,
            "generated_at": datetime.now().isoformat(),
            "timeout_seconds": MAX_WAIT_SECONDS,
            "stall_threshold_seconds": STALL_THRESHOLD
        },
        "summary": summary,
        "detailed_results": results
    }

# ========== 主程序 ==========
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(script_dir, REPORTS_DIR)
    logs_dir = os.path.join(script_dir, LOGS_DIR)

    ensure_dir(reports_dir)
    ensure_dir(logs_dir)

    print("=" * 60, flush=True)
    print("Gemma 4 E4B Q4_K_M 自動測試評估", flush=True)
    print(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 60, flush=True)

    # 1. 檢查模型
    print("\n[1/5] 檢查模型狀態...", flush=True)
    available, info = check_model()
    if not available:
        error_result = {
            "status": "error",
            "message": "模型不可用",
            "model": MODEL_NAME,
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ 模型不可用", flush=True)
        save_json(error_result, os.path.join(logs_dir, f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"))
        sys.exit(1)

    print(f"✅ 模型就緒：{info}", flush=True)

    # 2. 執行寫作任務
    print("\n[2/5] 執行寫作任務...", flush=True)
    writing_results = []
    for task in WRITING_TASKS:
        result = run_writing_test(task)
        writing_results.append(result)
        log(f"    完成：{result['tokens']} tokens | {result['speed']} tokens/s | 品質：{result['quality_score']}")

    # 3. 執行推論測驗
    print("\n[3/5] 執行推論測驗...", flush=True)
    reasoning_results = []
    for task in REASONING_TASKS:
        result = run_reasoning_test(task)
        reasoning_results.append(result)
        log(f"    完成：{result['tokens']} tokens | 覆蓋：{result['keyword_coverage']} | 品質：{result['quality_score']}")

    # 4. 計算摘要
    print("\n[4/5] 計算摘要...", flush=True)

    all_results = writing_results + reasoning_results
    total_tokens = sum(r.get("tokens", 0) for r in all_results)
    total_time = sum(r.get("elapsed", 0) for r in all_results)
    avg_speed = total_tokens / total_time if total_time > 0 else 0
    success_count = sum(1 for r in all_results if r.get("success"))
    total_count = len(all_results)
    total_quality = sum(r.get("quality_score", 0) for r in all_results)
    avg_quality = total_quality / total_count if total_count > 0 else 0

    summary = {
        "total_tests": total_count,
        "successful": success_count,
        "failed": total_count - success_count,
        "success_rate": f"{success_count / total_count * 100:.1f}%",
        "total_tokens": total_tokens,
        "total_time_seconds": round(total_time, 2),
        "average_speed": round(avg_speed, 2),
        "overall_quality_score": round(avg_quality, 1),
        "errors": [
            {"task": r.get("task_name") or f"推論題#{r.get('question_id')}", "reason": r.get("error") or ("停滯" if r.get("stalled") else ("超時" if r.get("timed_out") else "成功"))}
            for r in all_results if not r.get("success")
        ]
    }

    detailed_results = {
        "writing": writing_results,
        "reasoning": reasoning_results
    }

    # 5. 生成並儲存報告
    print("\n[5/5] 生成報告...", flush=True)

    # JSON 報告
    json_report = generate_json_report(detailed_results, summary)
    json_filename = f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_filepath = os.path.join(reports_dir, json_filename)
    save_json(json_report, json_filepath)
    log(f"✅ JSON 報告已儲存：{json_filepath}")

    # Markdown 報告
    md_report = generate_markdown_report(detailed_results, summary)
    md_filename = f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    md_filepath = os.path.join(reports_dir, md_filename)
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(md_report)
    log(f"✅ Markdown 報告已儲存：{md_filepath}")

    # 終端輸出摘要
    print("\n" + "=" * 60, flush=True)
    print("📊 測試摘要", flush=True)
    print("=" * 60, flush=True)
    print(f"總測試數：{total_count}", flush=True)
    print(f"成功/失敗：{success_count}/{total_count - success_count}", flush=True)
    print(f"總Tokens：{total_tokens}", flush=True)
    print(f"總耗時：{total_time:.1f}秒", flush=True)
    print(f"平均速度：{avg_speed:.1f} tokens/s", flush=True)
    print(f"平均品質分數：{avg_quality:.1f}/100", flush=True)
    print("=" * 60, flush=True)

    return json_report

if __name__ == "__main__":
    result = main()
    sys.exit(0)