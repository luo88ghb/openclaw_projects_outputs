"""
Gemma 4 E4B Q4_K_M 控制台測試工具
================================
功能：
1. 寫一篇 10K tokens 學術報告
2. 寫一篇 20K tokens 科學小說  
3. 5道大學生等級推論題
4. 即時顯示速度、進度、token 數量

使用方式：
python gemma4_e4b_console_test.py

作者：Zeni (傑尼)
日期：2026-05-08
"""

import subprocess
import time
import sys
import os
from datetime import datetime

# ========== 測試題目 ==========
REASONING_QUESTIONS = [
    {
        "id": 1,
        "category": "邏輯推理",
        "question": """如果所有的A都是B，有些B是C，那麼以下哪個選項一定正確？
(A) 有些A是C
(B) 有些C是A
(C) 所有B都是A
(D) 有些B不是C
請詳細解釋你的推論過程。"""
    },
    {
        "id": 2,
        "category": "數學分析",
        "question": """請證明：若函數f(x)在[a,b]上連續，在(a,b)內可導，則存在c∈(a,b)使得
f'(c) = [f(b) - f(a)] / (b - a)
請詳細寫出證明過程。"""
    },
    {
        "id": 3,
        "category": "物理思考",
        "question": """一物體在光滑水平面上以速度v向右運動，撞上一個靜止的相同質量物體，碰撞後兩者黏在一起運動。求：
1. 碰撞後的共同速度
2. 系統能量損失
3. 這個碰撞是彈性還是非彈性？"""
    },
    {
        "id": 4,
        "category": "程式設計",
        "question": """請用你熟悉的語言實現一個LRU Cache（最近最少使用快取），要求：
1. 支援get和put操作，時間複雜度為O(1)
2. 容量滿時自動淘汰最久未使用的項目
3. 寫出完整的類別實現和簡單的使用範例。"""
    },
    {
        "id": 5,
        "category": "批判思考",
        "question": """「人工智慧將在未來10年內取代大多數人類工作」這個論點，請分析：
1. 支持這個論點的主要論據
2. 反對這個論點的主要論據
3. 你認為這個預測合理嗎？為什麼？
請從技術、經濟、社會多個角度分析。"""
    }
]

# ========== 任務定義 ==========
TASKS = [
    {
        "id": "academic_report",
        "name": "2K 學術報告",
        "description": "撰寫一篇關於「人工智慧對高等教育影響」的學術報告（約2,000 tokens）",
        "prompt": "請你以學術論文風格，撰寫一篇關於「人工智慧對高等教育影響」的學術報告。\n\n要求：\n1. 包含摘要、引言、分析討論、結論\n2. 總字數約2,000字（中文字）\n3. 語氣正式，引用虛構但合理的研究數據\n4. 層次分明，每個章節有明確標題\n\n請開始撰寫："
    },
    {
        "id": "science_fiction",
        "name": "5K 科學小說",
        "description": "創作一篇設在2145年火星殖民地的科幻短篇小說（約5,000 tokens）",
        "prompt": "請你創作一篇科幻短篇小說，背景設在2145年的火星殖民地。\n\n要求：\n1. 情節完整：開端、發展、高潮、結局\n2. 主要角色至少2人，要有性格刻劃\n3. 主題涉及：AI情感、人機界線、孤獨與歸屬\n4. 總字數約5,000字（中文字）\n5. 場景描寫細緻，對話自然\n\n請開始創作："
    }
]

MODEL_NAME = "gemma4:e4b-it-q4_K_M"

# ========== ANSI 顏色代碼 ==========
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_line():
    sys.stdout.write('\r' + ' ' * 120 + '\r')
    sys.stdout.flush()

def print_progress(token_count, speed, elapsed, prefix=""):
    bar_len = 30
    fill = '=' * min(int(token_count / 100), bar_len)
    empty = ' ' * (bar_len - len(fill))
    progress_pct = min(token_count / 100, 100)
    
    line = f"\r{prefix} [{fill}{empty}] {progress_pct:.0f}% | {token_count} tokens | {speed:.1f} tokens/s | {elapsed:.1f}s"
    clear_line()
    sys.stdout.write(line)
    sys.stdout.flush()

def print_result(text):
    clear_line()
    print(f"\n{Colors.GREEN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.GREEN}{text}{Colors.ENDC}")
    print(f"{Colors.GREEN}{'='*60}{Colors.ENDC}\n")

def print_error(text):
    print(f"{Colors.RED}錯誤: {text}{Colors.ENDC}")

def check_model():
    print(f"{Colors.CYAN}檢查模型 {MODEL_NAME}...{Colors.ENDC}")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if MODEL_NAME in result.stdout or "gemma4" in result.stdout:
            print(f"{Colors.GREEN}✅ 模型已就緒{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.YELLOW}⚠️ 模型未找到，嘗試使用 gemma4:e4b{Colors.ENDC}")
            return False
    except Exception as e:
        print_error(str(e))
        return False

def run_task(task):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}開始：{task['name']}{Colors.ENDC}")
    print(f"{Colors.HEADER}描述：{task['description']}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    start_time = time.time()
    token_count = 0
    output_chars = []
    
    try:
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        process.stdin.write(task["prompt"] + "\n")
        process.stdin.flush()
        process.stdin.close()
        
        for line in iter(process.stdout.readline, ''):
            if not line:
                continue
            line = line.strip()
            if not line:
                continue
            # 跳過 debug 輸出
            if line.startswith("[") or "prompt tokens" in line.lower() or "generate tokens" in line.lower():
                continue
                
            output_chars.append(line)
            token_count += 1
            
            elapsed = time.time() - start_time
            speed = token_count / elapsed if elapsed > 0 else 0
            
            print_progress(token_count, speed, elapsed, task["name"])
        
        process.wait()
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}已中斷{Colors.ENDC}")
        process.terminate()
        return
    
    elapsed = time.time() - start_time
    speed = token_count / elapsed if elapsed > 0 else 0
    
    clear_line()
    print_result(f"完成：{task['name']} | {token_count} tokens | {speed:.1f} tokens/s | {elapsed:.1f}s")
    
    return {
        "task": task["name"],
        "tokens": token_count,
        "speed": speed,
        "elapsed": elapsed
    }

def run_reasoning(question):
    print(f"\n{Colors.PURPLE}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.PURPLE}推論題 #{question['id']} | {question['category']}{Colors.ENDC}")
    print(f"{Colors.PURPLE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.CYAN}題目：{question['question'][:100]}...{Colors.ENDC}\n")
    
    start_time = time.time()
    token_count = 0
    output_chars = []
    
    prompt = f"請回答以下問題，展現完整的推論過程：\n\n{question['question']}"
    
    try:
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        process.stdin.write(prompt + "\n")
        process.stdin.flush()
        process.stdin.close()
        
        for line in iter(process.stdout.readline, ''):
            if not line:
                continue
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") or "prompt tokens" in line.lower():
                continue
                
            output_chars.append(line)
            token_count += 1
            
            elapsed = time.time() - start_time
            speed = token_count / elapsed if elapsed > 0 else 0
            
            print_progress(token_count, speed, elapsed, f"Q{question['id']}")
        
        process.wait()
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}已中斷{Colors.ENDC}")
        process.terminate()
        return
    
    elapsed = time.time() - start_time
    speed = token_count / elapsed if elapsed > 0 else 0
    
    clear_line()
    print_result(f"推論題 #{question['id']} 完成 | {token_count} tokens | {speed:.1f} tokens/s | {elapsed:.1f}s")
    
    return {
        "task": f"推論題#{question['id']}",
        "tokens": token_count,
        "speed": speed,
        "elapsed": elapsed
    }

def print_menu():
    print(f"\n{Colors.BOLD}{'='*60}")
    print("Gemma 4 E4B Q4_K_M 測試工具")
    print(f"{'='*60}{Colors.ENDC}\n")
    print(f"  {Colors.GREEN}1{Colors.ENDC}. 10K 學術報告測試")
    print(f"  {Colors.GREEN}2{Colors.ENDC}. 20K 科學小說測試")
    print(f"  {Colors.BLUE}3{Colors.ENDC}. 執行所有推論題測試")
    print(f"  {Colors.CYAN}4{Colors.ENDC}. 執行所有測試")
    print(f"  {Colors.YELLOW}5{Colors.ENDC}. 顯示模型資訊")
    print(f"  {Colors.RED}0{Colors.ENDC}. 離開")
    print()

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"\n{Colors.CYAN}載入 Gemma 4 E4B Q4_K_M 測試工具...{Colors.ENDC}\n")
    
    check_model()
    
    results = []
    
    while True:
        print_menu()
        choice = input(f"{Colors.BOLD}請選擇 (0-5): {Colors.ENDC}").strip()
        
        if choice == "0":
            print(f"\n{Colors.CYAN}再見！{Colors.ENDC}\n")
            break
            
        elif choice == "1":
            result = run_task(TASKS[0])
            if result:
                results.append(result)
                
        elif choice == "2":
            result = run_task(TASKS[1])
            if result:
                results.append(result)
                
        elif choice == "3":
            for q in REASONING_QUESTIONS:
                result = run_reasoning(q)
                if result:
                    results.append(result)
                    
        elif choice == "4":
            for task in TASKS:
                result = run_task(task)
                if result:
                    results.append(result)
            for q in REASONING_QUESTIONS:
                result = run_reasoning(q)
                if result:
                    results.append(result)
                    
        elif choice == "5":
            print(f"\n{Colors.CYAN}模型資訊：{Colors.ENDC}")
            print(f"  名稱：{MODEL_NAME}")
            print(f"  Context：8192 tokens")
            print(f"  量化：Q4_K_M")
            try:
                result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
                print(result.stdout)
            except:
                pass
        else:
            print(f"{Colors.RED}無效選擇，請重試{Colors.ENDC}")
    
    # 顯示總結
    if results:
        print(f"\n{Colors.BOLD}{'='*60}")
        print("測試結果總結")
        print(f"{'='*60}{Colors.ENDC}\n")
        for r in results:
            print(f"  {r['task']}: {r['tokens']} tokens, {r['speed']:.1f} tokens/s, {r['elapsed']:.1f}s")
        
        avg_speed = sum(r['speed'] for r in results) / len(results)
        total_tokens = sum(r['tokens'] for r in results)
        total_time = sum(r['elapsed'] for r in results)
        
        print(f"\n{Colors.GREEN}平均速度：{avg_speed:.1f} tokens/s{Colors.ENDC}")
        print(f"{Colors.GREEN}總 tokens：{total_tokens}{Colors.ENDC}")
        print(f"{Colors.GREEN}總時間：{total_time:.1f}s{Colors.ENDC}\n")

if __name__ == "__main__":
    main()
