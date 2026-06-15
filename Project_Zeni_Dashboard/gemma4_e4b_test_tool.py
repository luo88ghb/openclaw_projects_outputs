"""
Gemma 4 E4B Q4_K_M 測試與驗證工具
===========================
功能：
1. 寫一篇 10K tokens 學術報告
2. 寫一篇 20K tokens 科學小說
3. 5道大學生等級推論題
4. GUI 顯示精確測試狀況和進度

使用方式：
- 雙擊執行 python gemma4_e4b_test_tool.py
- 或指令: python gemma4_e4b_test_tool.py

作者：Zeni (傑尼)
日期：2026-05-08 (更新：停止功能已修復)
"""

import subprocess
import time
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import json
from datetime import datetime
import sys
import os
import re

# ========== 測試題目 ==========
REASONING_QUESTIONS = [
    {
        "id": 1,
        "category": "邏輯推理",
        "difficulty": "大學生",
        "question": "如果所有的A都是B，有些B是C，那麼以下哪個選項一定正確？\n(A) 有些A是C\n(B) 有些C是A\n(C) 所有B都是A\n(D) 有些B不是C\n請詳細解釋你的推論過程。",
        "expected": "這是一道經典的三段論邏輯題。需要分析A、B、C之間的包含關係。"
    },
    {
        "id": 2,
        "category": "數學分析",
        "difficulty": "大學生",
        "question": "請證明：若函數f(x)在[a,b]上連續，在(a,b)內可導，則存在c∈(a,b)使得\nf'(c) = [f(b) - f(a)] / (b - a)\n請詳細寫出證明過程。",
        "expected": "拉格朗日中值定理的標準證明。"
    },
    {
        "id": 3,
        "category": "物理思考",
        "difficulty": "大學生",
        "question": "一物體在光滑水平面上以速度v向右運動，撞上一個靜止的相同質量物體，碰撞後兩者黏在一起運動。求：\n1. 碰撞後的共同速度\n2. 系統能量損失\n3. 這個碰撞是彈性還是非彈性？",
        "expected": "動量守恆+能量分析。"
    },
    {
        "id": 4,
        "category": "程式設計",
        "difficulty": "大學生",
        "question": "請用你熟悉的語言實現一個LRU Cache（最近最少使用快取），要求：\n1. 支援get和put操作，時間複雜度為O(1)\n2. 容量滿時自動淘汰最久未使用的項目\n3. 寫出完整的類別實現和簡單的使用範例。",
        "expected": "需要結合HashMap和雙向連結串列來實現O(1)操作。"
    },
    {
        "id": 5,
        "category": "批判思考",
        "difficulty": "大學生",
        "question": "「人工智慧將在未來10年內取代大多數人類工作」這個論點，請分析：\n1. 支持這個論點的主要論據\n2. 反對這個論點的主要論據\n3. 你認為這個預測合理嗎？為什麼？\n請從技術、經濟、社會多個角度分析。",
        "expected": "需要多角度批判性分析，不是簡單的二元論點。"
    }
]

# ========== 任務定義 ==========
TASKS = [
    {
        "id": "academic_report",
        "name": "2K 學術報告",
        "description": "撰寫一篇完整的學術報告（約2,000 tokens）",
        "prompt": "請你以學術論文風格，撰寫一篇關於「人工智慧對高等教育影響」的學術報告。\n\n要求：\n1. 包含摘要、引言、分析討論、結論\n2. 總字數約2,000字（中文字）\n3. 語氣正式，引用虛構但合理的研究數據\n4. 層次分明，每個章節有明確標題\n\n請開始撰寫：",
        "expected_tokens": 2000
    },
    {
        "id": "science_fiction",
        "name": "5K 科學小說",
        "description": "撰寫一篇科幻短篇小說（約5,000 tokens）",
        "prompt": "請你創作一篇科幻短篇小說，背景設在2145年的火星殖民地。\n\n要求：\n1. 情節完整：開端、發展、高潮、結局\n2. 主要角色至少2人，要有性格刻劃\n3. 主題涉及：AI情感、人機界線、孤獨與歸屬\n4. 總字數約5,000字（中文字）\n5. 場景描寫細緻，對話自然\n\n請開始創作：",
        "expected_tokens": 5000
    }
]

# ========== Ollama CLI 客戶端 ==========
class OllamaCLI:
    """使用 subprocess 調用 ollama CLI"""
    
    def __init__(self, model_name="gemma4:e4b-it-q4_K_M"):
        self.model_name = model_name
        
    def check_model(self):
        """檢查模型狀態"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if self.model_name in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            return True, {"name": self.model_name, "size": parts[2] if len(parts) > 2 else "unknown"}
                if "gemma4" in result.stdout:
                    return True, {"name": "gemma4 (detected)", "size": "9.6GB"}
            return False, None
        except Exception as e:
            return False, str(e)

# ========== GUI 应用 ==========
class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemma 4 E4B Q4_K_M 測試工具")
        self.root.geometry("1000x750")
        
        self.ollama = OllamaCLI()
        self.is_running = False
        self.current_task = None
        self.test_results = []
        self.current_process = None  # 用於停止 subprocess
        
        self.setup_ui()
        
    def setup_ui(self):
        """設置 GUI"""
        # 標題
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="Gemma 4 E4B Q4_K_M 測試與驗證工具",
            font=("Microsoft JhengHei", 18, "bold"),
            fg="white",
            bg="#2c3e50"
        ).pack(pady=15)
        
        # 狀態列
        self.status_var = tk.StringVar(value="準備就緒")
        status_bar = tk.Frame(self.root, bg="#34495e", height=30)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)
        
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            font=("Microsoft JhengHei", 10),
            fg="white",
            bg="#34495e",
            anchor=tk.W
        ).pack(side=tk.LEFT, padx=10)
        
        # 模型狀態
        self.model_status_var = tk.StringVar(value="檢查模型中...")
        tk.Label(
            status_bar,
            textvariable=self.model_status_var,
            font=("Microsoft JhengHei", 10),
            fg="#2ecc71",
            bg="#34495e",
            anchor=tk.E
        ).pack(side=tk.RIGHT, padx=10)
        
        # 主要內容區
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側面板 - 任務選擇
        left_panel = tk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)
        
        tk.Label(
            left_panel,
            text="測試任務",
            font=("Microsoft JhengHei", 14, "bold")
        ).pack(pady=10)
        
        # 任務按鈕
        self.task_buttons = {}
        for task in TASKS:
            btn = tk.Button(
                left_panel,
                text=f"{task['name']}",
                font=("Microsoft JhengHei", 11),
                command=lambda t=task: self.start_task(t),
                height=2,
                bg="#3498db",
                fg="white",
                relief=tk.RAISED
            )
            btn.pack(fill=tk.X, pady=5, padx=5)
            self.task_buttons[task["id"]] = btn
        
        # 分隔線
        tk.Frame(left_panel, height=2, bg="#bdc3c7").pack(fill=tk.X, pady=10, padx=5)
        
        tk.Label(
            left_panel,
            text="推論測驗",
            font=("Microsoft JhengHei", 14, "bold")
        ).pack(pady=10)
        
        self.reasoning_buttons = {}
        for q in REASONING_QUESTIONS:
            btn = tk.Button(
                left_panel,
                text=f"{q['category']} #{q['id']}",
                font=("Microsoft JhengHei", 10),
                command=lambda q=q: self.start_reasoning(q),
                height=1,
                bg="#9b59b6",
                fg="white",
                relief=tk.RAISED
            )
            btn.pack(fill=tk.X, pady=3, padx=5)
            self.reasoning_buttons[q["id"]] = btn
        
        # 右側面板 - 輸出
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10,0))
        
        # 進度框架
        progress_frame = tk.LabelFrame(right_panel, text="測試進度", font=("Microsoft JhengHei", 12, "bold"))
        progress_frame.pack(fill=tk.X, pady=(0,10))
        
        self.progress_var = tk.StringVar(value="等待開始...")
        tk.Label(
            progress_frame,
            textvariable=self.progress_var,
            font=("Microsoft JhengHei", 11)
        ).pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            length=500,
            maximum=100
        )
        self.progress_bar.pack(pady=5, padx=10, fill=tk.X)
        
        # 速度顯示
        speed_frame = tk.Frame(progress_frame)
        speed_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(speed_frame, text="速度:", font=("Microsoft JhengHei", 10)).pack(side=tk.LEFT)
        self.speed_var = tk.StringVar(value="-- tokens/s")
        tk.Label(speed_frame, textvariable=self.speed_var, font=("Microsoft JhengHei", 10, "bold"), fg="#e74c3c").pack(side=tk.LEFT, padx=(5,20))
        
        tk.Label(speed_frame, text="已生成:", font=("Microsoft JhengHei", 10)).pack(side=tk.LEFT)
        self.tokens_var = tk.StringVar(value="0 tokens")
        tk.Label(speed_frame, textvariable=self.tokens_var, font=("Microsoft JhengHei", 10, "bold"), fg="#27ae60").pack(side=tk.LEFT, padx=(5,20))
        
        tk.Label(speed_frame, text="耗時:", font=("Microsoft JhengHei", 10)).pack(side=tk.LEFT)
        self.elapsed_var = tk.StringVar(value="0.0s")
        tk.Label(speed_frame, textvariable=self.elapsed_var, font=("Microsoft JhengHei", 10, "bold"), fg="#3498db").pack(side=tk.LEFT, padx=5)
        
        # 輸出框架
        output_frame = tk.LabelFrame(right_panel, text="模型輸出", font=("Microsoft JhengHei", 12, "bold"))
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            height=25
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 按鈕框架
        btn_frame = tk.Frame(right_panel)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="停止",
            font=("Microsoft JhengHei", 11),
            command=self.stop_task,
            state=tk.DISABLED,
            bg="#e74c3c",
            fg="white",
            width=10
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=5)
        
        self.clear_btn = tk.Button(
            btn_frame,
            text="清除",
            font=("Microsoft JhengHei", 11),
            command=self.clear_output,
            bg="#95a5a6",
            fg="white",
            width=10
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=5)
        
        self.export_btn = tk.Button(
            btn_frame,
            text="匯出報告",
            font=("Microsoft JhengHei", 11),
            command=self.export_results,
            bg="#2ecc71",
            fg="white",
            width=10
        )
        self.export_btn.pack(side=tk.RIGHT, padx=5)
        
        # 啟動時檢查模型
        self.root.after(500, self.check_model_status)
        
    def check_model_status(self):
        """檢查模型狀態，若可用則設定 model_ready 為 True"""
        available, info = self.ollama.check_model()
        if available:
            size_info = info.get("size", "unknown") if info else "unknown"
            self.model_status_var.set(f"Model ready ({size_info})")
            self.model_ready = True
        else:
            self.model_status_var.set("Model not found")
            self.model_ready = False
        self.update_button_states()
        
    def update_button_states(self):
        """更新按鈕狀態 – 只有在模型已就緒且未執行任務時才啟用"""
        state = tk.NORMAL if (self.model_ready and not self.is_running) else tk.DISABLED
        for btn in self.task_buttons.values():
            btn.config(state=state)
        for btn in self.reasoning_buttons.values():
            btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if self.is_running else tk.DISABLED)
        
    def start_task(self, task):
        """開始任務"""
        if self.is_running:
            return
        
        self.is_running = True
        self.current_task = task
        self.update_button_states()
        self.status_var.set(f"執行中: {task['name']}")
        self.progress_var.set(f"任務: {task['name']}")
        self.progress_bar["value"] = 0
        
        thread = threading.Thread(target=self.run_task, args=(task,))
        thread.daemon = True
        thread.start()
        
    def start_reasoning(self, question):
        """開始推論測驗"""
        if self.is_running:
            return
        
        self.is_running = True
        self.current_task = question
        self.update_button_states()
        self.status_var.set(f"執行中: 推論題 #{question['id']}")
        self.progress_var.set(f"題目: {question['category']} #{question['id']}")
        self.progress_bar["value"] = 0
        
        thread = threading.Thread(target=self.run_reasoning, args=(question,))
        thread.daemon = True
        thread.start()
        
    def run_task(self, task):
        """執行任務"""
        start_time = time.time()
        output_chunks = []
        total_tokens = 0
        process = None
        
        self.output_text.delete("1.0", tk.END)
        self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] 開始：{task['name']}\n")
        self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] 提示：{task['description']}\n")
        self.append_output("=" * 60 + "\n\n")
        
        try:
            cmd = ["ollama", "run", self.ollama.model_name]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            self.current_process = process
            
            process.stdin.write(task["prompt"] + "\n")
            process.stdin.flush()
            process.stdin.close()
            
            for line in iter(process.stdout.readline, ''):
                if not self.is_running:
                    self.append_output("\n[已停止]\n")
                    break
                    
                line = line.strip()
                if not line:
                    continue
                if line.startswith("[") or "prompt tokens" in line.lower() or "generate tokens" in line.lower():
                    continue
                    
                output_chunks.append(line)
                total_tokens += 1
                
                elapsed = time.time() - start_time
                speed = total_tokens / elapsed if elapsed > 0 else 0
                
                self.root.after(0, self.update_progress, total_tokens, speed, elapsed, line, task["expected_tokens"])
            
            process.wait()
            
        except Exception as e:
            self.root.after(0, self.show_error, str(e))
        finally:
            self.current_process = None
            full_output = "".join(output_chunks)
            self.save_result(task["name"], full_output, total_tokens, time.time() - start_time, "success")
            self.root.after(0, self.task_completed)
            
    def run_reasoning(self, question):
        """執行推論測驗"""
        start_time = time.time()
        output_chunks = []
        total_tokens = 0
        process = None
        
        self.output_text.delete("1.0", tk.END)
        self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] 推論題 #{question['id']}\n")
        self.append_output(f"[難度] {question['difficulty']} | [類型] {question['category']}\n")
        self.append_output("-" * 60 + "\n")
        self.append_output(f"[題目]\n{question['question']}\n")
        self.append_output("-" * 60 + "\n")
        self.append_output("[模型回答]\n")
        
        try:
            prompt = f"請回答以下問題，展現完整的推論過程：\n\n{question['question']}"
            cmd = ["ollama", "run", self.ollama.model_name]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            self.current_process = process
            
            process.stdin.write(prompt + "\n")
            process.stdin.flush()
            process.stdin.close()
            
            for line in iter(process.stdout.readline, ''):
                if not self.is_running:
                    self.append_output("\n[已停止]\n")
                    break
                    
                line = line.strip()
                if not line:
                    continue
                if line.startswith("[") or "prompt tokens" in line.lower():
                    continue
                    
                output_chunks.append(line)
                total_tokens += 1
                
                elapsed = time.time() - start_time
                speed = total_tokens / elapsed if elapsed > 0 else 0
                
                self.root.after(0, self.update_progress, total_tokens, speed, elapsed, line, 2000)
            
            process.wait()
            
        except Exception as e:
            self.root.after(0, self.show_error, str(e))
        finally:
            self.current_process = None
            full_output = "".join(output_chunks)
            self.save_result(f"推論題#{question['id']}", full_output, total_tokens, time.time() - start_time, "reasoning")
            self.root.after(0, self.task_completed)
            
    def update_progress(self, tokens, speed, elapsed, last_chunk=None, expected=None):
        """更新進度"""
        self.tokens_var.set(f"{tokens} tokens")
        self.speed_var.set(f"{speed:.1f} tokens/s")
        self.elapsed_var.set(f"{elapsed:.1f}s")
        
        if last_chunk:
            self.append_output(last_chunk)
        
        if expected:
            progress = min(tokens / expected * 100, 100)
            self.progress_bar["value"] = progress
            self.progress_var.set(f"進行中... ({progress:.1f}%)")
        
        self.root.update_idletasks()
        
    def task_completed(self):
        """任務完成"""
        self.is_running = False
        self.current_task = None
        self.update_button_states()
        self.status_var.set("完成")
        self.progress_var.set("測試完成")
        self.progress_bar["value"] = 100
        
    def stop_task(self):
        """停止任務 - 設置標記 + 終止 subprocess"""
        self.is_running = False
        self.status_var.set("已停止")
        self.progress_var.set("已停止")
        
        # 終止 subprocess
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=2)
            except:
                try:
                    self.current_process.kill()
                except:
                    pass
            self.current_process = None
        
        # 也停止 ollama
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'ollama.exe'], 
                         capture_output=True, timeout=5)
        except:
            pass
            
        self.update_button_states()
        
    def clear_output(self):
        """清除輸出"""
        self.output_text.delete("1.0", tk.END)
        self.progress_bar["value"] = 0
        self.speed_var.set("-- tokens/s")
        self.tokens_var.set("0 tokens")
        self.elapsed_var.set("0.0s")
        
    def append_output(self, text):
        """追加輸出文字"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        
    def show_error(self, error_msg):
        """顯示錯誤"""
        self.append_output(f"\nError：{error_msg}\n")
        if self.current_task:
            self.save_result(self.current_task.get("name", "unknown"), error_msg, 0, 0, "error")
        
    def save_result(self, task_name, output, tokens, elapsed, result_type):
        """保存結果"""
        result = {
            "task_name": task_name,
            "output": output[:5000],
            "tokens": tokens,
            "elapsed": elapsed,
            "speed": tokens / elapsed if elapsed > 0 else 0,
            "result_type": result_type,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
    def export_results(self):
        """匯出報告"""
        if not self.test_results:
            self.append_output("\n沒有測試結果可以匯出\n")
            return
            
        report = []
        report.append("=" * 70)
        report.append("Gemma 4 E4B Q4_K_M 測試報告")
        report.append(f"生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        report.append("")
        
        for i, r in enumerate(self.test_results, 1):
            report.append(f"\n【測試 {i}】{r['task_name']}")
            report.append("-" * 50)
            report.append(f"  類型：{r['result_type']}")
            report.append(f"  Tokens：{r['tokens']}")
            report.append(f"  耗時：{r['elapsed']:.2f}s")
            report.append(f"  速度：{r['speed']:.2f} tokens/s")
            report.append(f"  時間戳：{r['timestamp']}")
            report.append("")
            
        report.append("=" * 70)
        report.append("報告結束")
        report.append("=" * 70)
        
        filename = f"gemma4_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(os.getcwd(), filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(report))
            self.append_output(f"\n報告已匯出至：{filepath}\n")
        except Exception as e:
            self.append_output(f"\n匯出失敗：{str(e)}\n")

# ========== 主程序 ==========
if __name__ == "__main__":
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()
