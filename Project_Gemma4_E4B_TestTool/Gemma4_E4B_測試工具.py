# -*- coding: utf-8 -*-
"""
Gemma 4 E4B Q4_K_M 測試工具 (GUI版) v1.3.0
===========================
功能：
1. 撰寫 2K tokens 學術報告
2. 撰寫 5K tokens 科學小說
3. 5道大學生等級推論題
4. 可編輯並儲存測試題目
5. 自訂測試題目
6. 圖片辨識測試（OCR/內容分析）
7. GUI 顯示精確測試狀況和進度

增強功能（v1.3.0）：
- ✅ 匯出報告至 reports/ 資料夾
- ✅ 可編輯測試題目並儲存
- ✅ 自訂測試題目功能
- ✅ 圖片辨識測試功能
- ✅ JSON 配置檔案管理題目

作者：Zeni (傑尼)
更新：2026-05-11
"""

import subprocess
import time
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, messagebox, simpledialog
import threading
import json
from datetime import datetime
import sys
import os
import re
import base64

# 強制 UTF-8 編碼（修復 Windows cp950 問題）
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)

# ========== 全域設定 ==========
STALL_THRESHOLD = 30  # 停滯警告秒數
MAX_WAIT_SECONDS = 300  # 5分鐘超時
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")
QUESTIONS_FILE = os.path.join(SCRIPT_DIR, "test_questions.json")

# 確保目錄存在
os.makedirs(REPORTS_DIR, exist_ok=True)

# ========== 載入測試題目 ==========
def load_questions():
    """載入測試題目"""
    if os.path.exists(QUESTIONS_FILE):
        try:
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 預設題目
    default = {
        "tasks": [
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
        ],
        "reasoning_questions": [
            {
                "id": 1,
                "category": "邏輯推理",
                "difficulty": "大學生",
                "question": "如果所有的A都是B，有些B是C，那麼以下哪個選項一定正確？\n(A) 有些A是C\n(B) 有些C是A\n(C) 所有B都是A\n(D) 有些B不是C\n請詳細解釋你的推論過程。"
            },
            {
                "id": 2,
                "category": "數學分析",
                "difficulty": "大學生",
                "question": "請證明：若函數f(x)在[a,b]上連續，在(a,b)內可導，則存在c∈(a,b)使得\nf'(c) = [f(b) - f(a)] / (b - a)\n請詳細寫出證明過程。"
            },
            {
                "id": 3,
                "category": "物理思考",
                "difficulty": "大學生",
                "question": "一物體在光滑水平面上以速度v向右運動，撞上一個靜止的相同質量物體，碰撞後兩者黏在一起運動。求：\n1. 碰撞後的共同速度\n2. 系統能量損失\n3. 這個碰撞是彈性還是非彈性？"
            },
            {
                "id": 4,
                "category": "程式設計",
                "difficulty": "大學生",
                "question": "請用你熟悉的語言實現一個LRU Cache（最近最少使用快取），要求：\n1. 支援get和put操作，時間複雜度為O(1)\n2. 容量滿時自動淘汰最久未使用的項目\n3. 寫出完整的類別實現和簡單的使用範例。"
            },
            {
                "id": 5,
                "category": "批判思考",
                "difficulty": "大學生",
                "question": "「人工智慧將在未來10年內取代大多數人類工作」這個論點，請分析：\n1. 支持這個論點的主要論據\n2. 反對這個論點的主要論據\n3. 你認為這個預測合理嗎？為什麼？\n請從技術、經濟、社會多個角度分析。"
            }
        ],
        "custom_prompts": []
    }
    
    # 儲存預設題目
    save_questions(default)
    return default

def save_questions(data):
    """儲存測試題目"""
    try:
        with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"儲存題目失敗: {e}")
        return False

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
                timeout=10
            )
            output = result.stdout.decode('utf-8', errors='replace')
            if self.model_name in output or "gemma4" in output:
                return True, {"name": self.model_name, "size": "13GB"}
            return False, None
        except Exception as e:
            return False, str(e)

# ========== 編輯題目對話框 ==========
class EditQuestionDialog(tk.Toplevel):
    """編輯題目對話框"""
    
    def __init__(self, parent, question, question_type, callback):
        super().__init__(parent)
        self.title("編輯題目")
        self.geometry("600x600")
        self.question = question.copy()
        self.question_type = question_type
        self.callback = callback
        
        self.setup_ui()
        
    def setup_ui(self):
        """設置 UI"""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 題目名稱/類別
        if self.question_type == "reasoning":
            tk.Label(main_frame, text="題目類別:", font=("Microsoft JhengHei", 11)).pack(anchor=tk.W)
            self.category_entry = tk.Entry(main_frame, font=("Microsoft JhengHei", 11), width=50)
            self.category_entry.insert(0, self.question.get("category", ""))
            self.category_entry.pack(fill=tk.X, pady=(0, 10))
        
        # 題目內容
        tk.Label(main_frame, text="題目內容:", font=("Microsoft JhengHei", 11)).pack(anchor=tk.W)
        self.question_text = scrolledtext.ScrolledText(main_frame, font=("Microsoft JhengHei", 11), height=15)
        self.question_text.insert("1.0", self.question.get("question", self.question.get("prompt", "")))
        self.question_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 按鈕
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="儲存", font=("Microsoft JhengHei", 11), bg="#2ecc71", fg="white",
                  command=self.save).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="取消", font=("Microsoft JhengHei", 11), bg="#e74c3c", fg="white",
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
    def save(self):
        """儲存題目"""
        if self.question_type == "reasoning":
            self.question["category"] = self.category_entry.get()
            self.question["question"] = self.question_text.get("1.0", tk.END).strip()
        else:
            self.question["prompt"] = self.question_text.get("1.0", tk.END).strip()
        
        self.callback(self.question, self.question_type)
        self.destroy()

# ========== 自訂測試對話框 ==========
class CustomTestDialog(tk.Toplevel):
    """自訂測試對話框"""
    
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("自訂測試題目")
        self.geometry("700x700")
        self.callback = callback
        
        self.setup_ui()
        
    def setup_ui(self):
        """設置 UI"""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        tk.Label(main_frame, text="自訂測試題目", font=("Microsoft JhengHei", 14, "bold")).pack(pady=(0, 10))
        
        # 名稱
        tk.Label(main_frame, text="測試名稱:", font=("Microsoft JhengHei", 11)).pack(anchor=tk.W)
        self.name_entry = tk.Entry(main_frame, font=("Microsoft JhengHei", 11), width=50)
        self.name_entry.insert(0, "自訂測試")
        self.name_entry.pack(fill=tk.X, pady=(0, 10))
        
        # 提示詞
        tk.Label(main_frame, text="提示詞 (Prompt):", font=("Microsoft JhengHei", 11)).pack(anchor=tk.W)
        self.prompt_text = scrolledtext.ScrolledText(main_frame, font=("Microsoft JhengHei", 11), height=15)
        self.prompt_text.insert("1.0", "請輸入您的測試提示詞...")
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 預期 tokens
        tk.Label(main_frame, text="預期輸出 tokens (選填):", font=("Microsoft JhengHei", 11)).pack(anchor=tk.W)
        self.tokens_entry = tk.Entry(main_frame, font=("Microsoft JhengHei", 11), width=20)
        self.tokens_entry.insert(0, "2000")
        self.tokens_entry.pack(anchor=tk.W, pady=(0, 10))
        
        # 按鈕
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="開始測試", font=("Microsoft JhengHei", 11), bg="#2ecc71", fg="white",
                  command=self.start_test).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="儲存為常用", font=("Microsoft JhengHei", 11), bg="#3498db", fg="white",
                  command=self.save_custom).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="取消", font=("Microsoft JhengHei", 11), bg="#e74c3c", fg="white",
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
    def start_test(self):
        """開始測試"""
        task = {
            "id": f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": self.name_entry.get() or "自訂測試",
            "prompt": self.prompt_text.get("1.0", tk.END).strip(),
            "expected_tokens": int(self.tokens_entry.get() or "2000")
        }
        self.callback(task)
        self.destroy()
        
    def save_custom(self):
        """儲存為常用測試"""
        task = {
            "id": f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": self.name_entry.get() or "自訂測試",
            "prompt": self.prompt_text.get("1.0", tk.END).strip(),
            "expected_tokens": int(self.tokens_entry.get() or "2000")
        }
        self.callback(task, save=True)
        self.destroy()

# ========== 圖片測試對話框 ==========
class ImageTestDialog(tk.Toplevel):
    """圖片辨識測試對話框"""
    
    def __init__(self, parent, model_name, callback):
        super().__init__(parent)
        self.title("圖片辨識測試")
        self.geometry("800x600")
        self.model_name = model_name
        self.callback = callback
        self.image_path = None
        self.image_data = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """設置 UI"""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        tk.Label(main_frame, text="圖片辨識測試", font=("Microsoft JhengHei", 14, "bold")).pack(pady=(0, 10))
        
        # 圖片選擇
        img_frame = tk.LabelFrame(main_frame, text="選擇圖片", font=("Microsoft JhengHei", 11))
        img_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.img_label = tk.Label(img_frame, text="尚未選擇圖片", font=("Microsoft JhengHei", 10), fg="#7f8c8d")
        self.img_label.pack(pady=5)
        
        tk.Button(img_frame, text="選擇圖片", font=("Microsoft JhengHei", 11), bg="#3498db", fg="white",
                  command=self.select_image).pack(pady=5)
        
        # 圖片預覽
        self.preview_label = tk.Label(img_frame, text="", font=("Microsoft JhengHei", 10))
        self.preview_label.pack(pady=5)
        
        # 測試提示
        prompt_frame = tk.LabelFrame(main_frame, text="測試提示", font=("Microsoft JhengHei", 11))
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(prompt_frame, text="請輸入您想讓模型分析的內容:", font=("Microsoft JhengHei", 10)).pack(anchor=tk.W, padx=5, pady=5)
        
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, font=("Microsoft JhengHei", 11), height=10)
        self.prompt_text.insert("1.0", "請描述這張圖片的內容，包括：\n1. 主要物件\n2. 場景描述\n3. 顏色和構圖\n4. 任何文字（如有）")
        self.prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 按鈕
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="開始測試", font=("Microsoft JhengHei", 11), bg="#2ecc71", fg="white",
                  command=self.start_test).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="取消", font=("Microsoft JhengHei", 11), bg="#e74c3c", fg="white",
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
    def select_image(self):
        """選擇圖片"""
        filetypes = [
            ("圖片檔案", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("所有檔案", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self.image_path = filepath
            
            # 讀取圖片為 base64
            try:
                with open(filepath, 'rb') as f:
                    self.image_data = base64.b64encode(f.read()).decode('utf-8')
                
                self.img_label.config(text=f"已選擇: {os.path.basename(filepath)}", fg="#27ae60")
                self.preview_label.config(text=f"檔案大小: {len(self.image_data) // 1024} KB (base64)")
            except Exception as e:
                messagebox.showerror("錯誤", f"讀取圖片失敗: {e}")
                
    def start_test(self):
        """開始圖片測試"""
        if not self.image_path:
            messagebox.showwarning("警告", "請先選擇一張圖片")
            return
            
        task = {
            "id": f"image_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": "圖片辨識測試",
            "image_path": self.image_path,
            "image_data": self.image_data,
            "prompt": self.prompt_text.get("1.0", tk.END).strip(),
            "expected_tokens": 2000
        }
        self.callback(task)
        self.destroy()

# ========== GUI 应用 ==========
class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemma 4 E4B Q4_K_M 測試工具 v1.3.4")
        self.root.geometry("1200x950")
        self.root.minsize(1100, 850)
        
        # 綁定關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.ollama = OllamaCLI()
        self.is_running = False
        self.model_ready = False
        self.current_task = None
        self.test_results = []
        self.current_process = None
        self.last_update_time = time.time()
        self.stall_warning_shown = False
        
        # 載入題目
        self.questions_data = load_questions()
        
        self.setup_ui()
        
    def setup_ui(self):
        """設置 GUI"""
        # 標題
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="Gemma 4 E4B Q4_K_M 測試與驗證工具 v1.3.4",
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
        
        self.model_status_var = tk.StringVar(value="檢查模型中...")
        self.model_status_label = tk.Label(
            status_bar,
            textvariable=self.model_status_var,
            font=("Microsoft JhengHei", 10),
            fg="#2ecc71",
            bg="#34495e",
            anchor=tk.E
        )
        self.model_status_label.pack(side=tk.RIGHT, padx=10)
        
        # 主要內容區
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側面板 - 任務選擇
        left_panel = tk.Frame(main_frame, width=320)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)
        
        # 使用 Canvas 支援滾動
        canvas = tk.Canvas(left_panel, highlightthickness=0)
        scrollbar = tk.Scrollbar(left_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ===== 測試任務 =====
        tk.Label(
            scrollable_frame,
            text="📝 測試任務",
            font=("Microsoft JhengHei", 14, "bold")
        ).pack(pady=10, fill=tk.X, padx=5)
        
        self.task_buttons = {}
        for task in self.questions_data.get("tasks", []):
            btn_frame = tk.Frame(scrollable_frame)
            btn_frame.pack(fill=tk.X, pady=2, padx=5)
            
            btn = tk.Button(
                btn_frame,
                text=f"▶ {task['name']}",
                font=("Microsoft JhengHei", 10),
                command=lambda t=task: self.start_task(t),
                height=2,
                bg="#3498db",
                fg="white",
                relief=tk.RAISED
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            edit_btn = tk.Button(
                btn_frame,
                text="✏️",
                font=("Microsoft JhengHei", 10),
                command=lambda t=task: self.edit_question(t, "task"),
                bg="#f39c12",
                fg="white",
                width=3
            )
            edit_btn.pack(side=tk.RIGHT, padx=(2, 0))
            
            self.task_buttons[task["id"]] = btn
        
        # ===== 推論測驗 =====
        tk.Frame(scrollable_frame, height=2, bg="#bdc3c7").pack(fill=tk.X, pady=10, padx=5)
        
        tk.Label(
            scrollable_frame,
            text="🧠 推論測驗",
            font=("Microsoft JhengHei", 14, "bold")
        ).pack(pady=10, fill=tk.X, padx=5)
        
        self.reasoning_buttons = {}
        for q in self.questions_data.get("reasoning_questions", []):
            btn_frame = tk.Frame(scrollable_frame)
            btn_frame.pack(fill=tk.X, pady=2, padx=5)
            
            btn = tk.Button(
                btn_frame,
                text=f"▶ {q['category']} #{q['id']}",
                font=("Microsoft JhengHei", 10),
                command=lambda q=q: self.start_reasoning(q),
                height=1,
                bg="#9b59b6",
                fg="white",
                relief=tk.RAISED
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            edit_btn = tk.Button(
                btn_frame,
                text="✏️",
                font=("Microsoft JhengHei", 10),
                command=lambda q=q: self.edit_question(q, "reasoning"),
                bg="#f39c12",
                fg="white",
                width=3
            )
            edit_btn.pack(side=tk.RIGHT, padx=(2, 0))
            
            self.reasoning_buttons[q["id"]] = btn
        
        # ===== 自訂測試 =====
        tk.Frame(scrollable_frame, height=2, bg="#bdc3c7").pack(fill=tk.X, pady=10, padx=5)
        
        tk.Label(
            scrollable_frame,
            text="🎨 自訂測試",
            font=("Microsoft JhengHei", 14, "bold")
        ).pack(pady=10, fill=tk.X, padx=5)
        
        tk.Button(
            scrollable_frame,
            text="➕ 新增自訂測試",
            font=("Microsoft JhengHei", 11),
            command=self.open_custom_test,
            height=2,
            bg="#1abc9c",
            fg="white",
            relief=tk.RAISED
        ).pack(fill=tk.X, pady=5, padx=5)
        
        # 自訂測試按鈕
        self.custom_buttons = {}
        for custom in self.questions_data.get("custom_prompts", []):
            btn_frame = tk.Frame(scrollable_frame)
            btn_frame.pack(fill=tk.X, pady=2, padx=5)
            
            btn = tk.Button(
                btn_frame,
                text=f"▶ {custom['name']}",
                font=("Microsoft JhengHei", 10),
                command=lambda c=custom: self.start_task(c),
                height=1,
                bg="#16a085",
                fg="white",
                relief=tk.RAISED
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            del_btn = tk.Button(
                btn_frame,
                text="🗑️",
                font=("Microsoft JhengHei", 10),
                command=lambda c=custom: self.delete_custom(c),
                bg="#e74c3c",
                fg="white",
                width=3
            )
            del_btn.pack(side=tk.RIGHT, padx=(2, 0))
            
            self.custom_buttons[custom["id"]] = btn
        
        # ===== 圖片測試 =====
        tk.Frame(scrollable_frame, height=2, bg="#bdc3c7").pack(fill=tk.X, pady=10, padx=5)
        
        tk.Label(
            scrollable_frame,
            text="🖼️ 圖片辨識測試",
            font=("Microsoft JhengHei", 14, "bold")
        ).pack(pady=10, fill=tk.X, padx=5)
        
        tk.Button(
            scrollable_frame,
            text="📷 選擇圖片並測試",
            font=("Microsoft JhengHei", 11),
            command=self.open_image_test,
            height=2,
            bg="#e74c3c",
            fg="white",
            relief=tk.RAISED
        ).pack(fill=tk.X, pady=5, padx=5)
        
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
        
        # 停滯警告
        self.stall_var = tk.StringVar(value="")
        tk.Label(
            progress_frame,
            textvariable=self.stall_var,
            font=("Microsoft JhengHei", 11, "bold"),
            fg="#e67e22"
        ).pack(pady=2)
        
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
        
        self.unload_btn = tk.Button(
            btn_frame,
            text="卸載模型",
            font=("Microsoft JhengHei", 11),
            command=self.unload_model,
            bg="#e67e22",
            fg="white",
            width=10
        )
        self.unload_btn.pack(side=tk.RIGHT, padx=5)
        
        # 說明框架
        info_frame = tk.LabelFrame(right_panel, text="操作說明", font=("Microsoft JhengHei", 10, "bold"))
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        info_text = tk.Label(
            info_frame,
            text="💡 報告匯出至: Project_Gemma4_E4B_TestTool/reports/",
            font=("Microsoft JhengHei", 9),
            fg="#7f8c8d",
            anchor=tk.W
        )
        info_text.pack(padx=10, pady=5, fill=tk.X)
        
        info_text2 = tk.Label(
            info_frame,
            text="✏️ 點擊黃色編輯按鈕可修改題目並儲存",
            font=("Microsoft JhengHei", 9),
            fg="#f39c12",
            anchor=tk.W
        )
        info_text2.pack(padx=10, pady=(0, 5), fill=tk.X)
        
        info_text3 = tk.Label(
            info_frame,
            text="🖼️ 支援圖片辨識測試 (OCR/內容分析)",
            font=("Microsoft JhengHei", 9),
            fg="#e74c3c",
            anchor=tk.W
        )
        info_text3.pack(padx=10, pady=(0, 5), fill=tk.X)
        
        # 啟動時檢查模型
        self.root.after(500, self.check_model_status)
        
    def check_model_status(self):
        """檢查模型狀態"""
        self.model_status_var.set("檢查中...")
        self.root.update_idletasks()

        available, info = self.ollama.check_model()
        if available:
            size_info = info.get("size", "unknown") if info else "unknown"
            self.model_status_var.set(f"Model ready ({size_info})")
            self.model_status_label.config(fg="#2ecc71")
            self.model_ready = True
            self.status_var.set("模型已就緒，選擇任務開始測試")
        else:
            self.model_status_var.set("Model not found")
            self.model_status_label.config(fg="#e74c3c")
            self.model_ready = False
            self.status_var.set("警告：模型未就緒")

        self.update_button_states()

    def update_button_states(self):
        """更新按鈕狀態"""
        state = tk.NORMAL if (self.model_ready and not self.is_running) else tk.DISABLED
        for btn in self.task_buttons.values():
            btn.config(state=state)
        for btn in self.reasoning_buttons.values():
            btn.config(state=state)
        for btn in self.custom_buttons.values():
            btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if self.is_running else tk.DISABLED)

    def edit_question(self, question, question_type):
        """編輯題目"""
        def callback(updated, q_type):
            if q_type == "reasoning":
                for i, q in enumerate(self.questions_data["reasoning_questions"]):
                    if q["id"] == updated["id"]:
                        self.questions_data["reasoning_questions"][i] = updated
                        break
            else:
                for i, t in enumerate(self.questions_data["tasks"]):
                    if t["id"] == updated["id"]:
                        self.questions_data["tasks"][i] = updated
                        break
            
            save_questions(self.questions_data)
            messagebox.showinfo("成功", "題目已儲存！")
        
        EditQuestionDialog(self.root, question, question_type, callback)

    def open_custom_test(self):
        """開啟自訂測試對話框"""
        def callback(task, save=False):
            if save:
                if "custom_prompts" not in self.questions_data:
                    self.questions_data["custom_prompts"] = []
                self.questions_data["custom_prompts"].append(task)
                save_questions(self.questions_data)
                messagebox.showinfo("成功", "自訂測試已儲存！重新啟動工具以載入新題目")
            self.start_task(task)
        
        CustomTestDialog(self.root, callback)
        
    def delete_custom(self, custom):
        """刪除自訂測試"""
        if messagebox.askyesno("確認", f"確定要刪除 '{custom['name']}' 嗎？"):
            self.questions_data["custom_prompts"] = [
                c for c in self.questions_data.get("custom_prompts", [])
                if c["id"] != custom["id"]
            ]
            save_questions(self.questions_data)
            messagebox.showinfo("成功", "已刪除！重新啟動工具以更新列表")

    def open_image_test(self):
        """開啟圖片測試對話框"""
        def callback(task):
            self.start_image_test(task)
        
        ImageTestDialog(self.root, self.ollama.model_name, callback)

    def start_task(self, task):
        """開始任務"""
        if self.is_running or not self.model_ready:
            return

        self.is_running = True
        self.current_task = task
        self.last_update_time = time.time()
        self.stall_warning_shown = False
        self.stall_var.set("")
        self.update_button_states()
        self.status_var.set(f"執行中: {task['name']}")
        self.progress_var.set(f"任務: {task['name']}")
        self.progress_bar["value"] = 0

        thread = threading.Thread(target=self.run_task, args=(task,))
        thread.daemon = True
        thread.start()

    def start_reasoning(self, question):
        """開始推論測驗"""
        if self.is_running or not self.model_ready:
            return

        self.is_running = True
        self.current_task = question
        self.last_update_time = time.time()
        self.stall_warning_shown = False
        self.stall_var.set("")
        self.update_button_states()
        self.status_var.set(f"執行中: 推論題 #{question['id']}")
        self.progress_var.set(f"題目: {question['category']} #{question['id']}")
        self.progress_bar["value"] = 0

        thread = threading.Thread(target=self.run_reasoning, args=(question,))
        thread.daemon = True
        thread.start()

    def start_image_test(self, task):
        """開始圖片測試"""
        if self.is_running or not self.model_ready:
            return

        self.is_running = True
        self.current_task = task
        self.last_update_time = time.time()
        self.stall_warning_shown = False
        self.stall_var.set("")
        self.update_button_states()
        self.status_var.set(f"執行中: 圖片辨識測試")
        self.progress_var.set(f"圖片: {os.path.basename(task['image_path'])}")
        self.progress_bar["value"] = 0

        thread = threading.Thread(target=self.run_image_test, args=(task,))
        thread.daemon = True
        thread.start()

    def check_stalled(self):
        """檢查是否停滯"""
        elapsed_since_update = time.time() - self.last_update_time
        if elapsed_since_update > STALL_THRESHOLD and not self.stall_warning_shown:
            self.stall_warning_shown = True
            return True
        return False

    def check_timeout(self, start_time):
        """檢查是否超時"""
        elapsed = time.time() - start_time
        return elapsed > MAX_WAIT_SECONDS

    def process_line(self, line, output_chunks):
        """處理單行輸出"""
        line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
        line = line.strip()
        if not line:
            return False
        if line.startswith("[") or "prompt tokens" in line.lower() or "generate tokens" in line.lower():
            return False
        output_chunks.append(line)
        return True

    def run_task(self, task):
        """執行任務"""
        start_time = time.time()
        output_chunks = []
        total_tokens = 0
        process = None

        self.output_text.delete("1.0", tk.END)
        self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] 開始：{task['name']}\n")
        self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] Timeout：{MAX_WAIT_SECONDS}秒 | 停滯警告：{STALL_THRESHOLD}秒\n")
        self.append_output("=" * 60 + "\n\n")

        try:
            cmd = ["ollama", "run", self.ollama.model_name]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            self.current_process = process
            
            prompt = task["prompt"] + "\n"
            process.stdin.write(prompt.encode('utf-8'))
            process.stdin.flush()
            process.stdin.close()
            
            buffer = b""
            last_progress_update = time.time()
            
            while True:
                if not self.is_running:
                    self.append_output("\n[已停止]\n")
                    break
                
                if self.check_timeout(start_time):
                    self.append_output(f"\n[超時警告：已運行 {MAX_WAIT_SECONDS} 秒，強制停止]\n")
                    self.handle_timeout()
                    break
                
                try:
                    chunk = process.stdout.read(64)
                    if chunk:
                        buffer += chunk
                        last_progress_update = time.time()
                        
                        while b'\n' in buffer:
                            line_bytes, buffer = buffer.split(b'\n', 1)
                            line = line_bytes.decode('utf-8', errors='replace')
                            
                            if self.process_line(line, output_chunks):
                                total_tokens += 1
                                self.last_update_time = time.time()
                                self.stall_warning_shown = False
                                
                                elapsed = time.time() - start_time
                                speed = total_tokens / elapsed if elapsed > 0 else 0
                                self.root.after(0, self.update_progress, total_tokens, speed, elapsed, line, task.get("expected_tokens", 2000))
                    else:
                        if process.poll() is not None:
                            if buffer:
                                remaining = buffer.decode('utf-8', errors='replace')
                                if remaining.strip():
                                    if self.process_line(remaining.strip(), output_chunks):
                                        total_tokens += 1
                            break
                        
                        time.sleep(0.05)
                        
                        if time.time() - last_progress_update > 5:
                            last_progress_update = time.time()
                            self.last_update_time = time.time()
                except Exception as e:
                    self.root.after(0, self.show_error, str(e))
                    break
            
            process.wait()

        except Exception as e:
            self.root.after(0, self.show_error, str(e))
        finally:
            self.current_process = None
            full_output = "".join(output_chunks)
            self.save_result(task["name"], full_output, total_tokens, time.time() - start_time, "task")
            self.root.after(0, self.task_completed)

    def run_reasoning(self, question):
        """執行推論測驗"""
        start_time = time.time()
        output_chunks = []
        total_tokens = 0
        process = None

        self.output_text.delete("1.0", tk.END)
        self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] 推論題 #{question['id']}\n")
        self.append_output(f"[難度] {question.get('difficulty', '大學生')} | [類型] {question['category']}\n")
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
                stderr=subprocess.DEVNULL
            )
            self.current_process = process
            
            process.stdin.write(prompt.encode('utf-8'))
            process.stdin.flush()
            process.stdin.close()
            
            buffer = b""
            last_progress_update = time.time()
            
            while True:
                if not self.is_running:
                    self.append_output("\n[已停止]\n")
                    break
                
                if self.check_timeout(start_time):
                    self.append_output(f"\n[超時警告：已運行 {MAX_WAIT_SECONDS} 秒，強制停止]\n")
                    self.handle_timeout()
                    break
                
                try:
                    chunk = process.stdout.read(64)
                    if chunk:
                        buffer += chunk
                        last_progress_update = time.time()
                        
                        while b'\n' in buffer:
                            line_bytes, buffer = buffer.split(b'\n', 1)
                            line = line_bytes.decode('utf-8', errors='replace')
                            
                            if self.process_line(line, output_chunks):
                                total_tokens += 1
                                self.last_update_time = time.time()
                                self.stall_warning_shown = False
                                
                                elapsed = time.time() - start_time
                                speed = total_tokens / elapsed if elapsed > 0 else 0
                                self.root.after(0, self.update_progress, total_tokens, speed, elapsed, line, 2000)
                    else:
                        if process.poll() is not None:
                            if buffer:
                                remaining = buffer.decode('utf-8', errors='replace')
                                if remaining.strip():
                                    if self.process_line(remaining.strip(), output_chunks):
                                        total_tokens += 1
                            break
                        
                        time.sleep(0.05)
                        
                        if time.time() - last_progress_update > 5:
                            last_progress_update = time.time()
                            self.last_update_time = time.time()
                except Exception as e:
                    self.root.after(0, self.show_error, str(e))
                    break
            
            process.wait()

        except Exception as e:
            self.root.after(0, self.show_error, str(e))
        finally:
            self.current_process = None
            full_output = "".join(output_chunks)
            self.save_result(f"推論題#{question['id']}", full_output, total_tokens, time.time() - start_time, "reasoning")
            self.root.after(0, self.task_completed)

    def run_image_test(self, task):
        """執行圖片測試 - 使用 Ollama CLI .image 命令"""
        start_time = time.time()
        output_chunks = []
        total_tokens = 0
        process = None

        self.output_text.delete("1.0", tk.END)
        self.append_output(f"[{datetime.now().strftime('%H:%M:%S')}] 圖片辨識測試\n")
        self.append_output(f"[圖片] {os.path.basename(task['image_path'])}\n")
        self.append_output("-" * 60 + "\n")
        self.append_output(f"[提示]\n{task['prompt']}\n")
        self.append_output("-" * 60 + "\n")
        self.append_output("[載入圖片...]\n")

        try:
            # 使用 Ollama CLI 的 .image 命令
            # 關鍵：使用 stderr=DEVNULL 避免 stdout/stderr 管道阻塞
            process = subprocess.Popen(
                ["ollama", "run", self.ollama.model_name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL  # 忽略 stderr 避免阻塞
            )
            self.current_process = process
            
            # 建構命令：先載入圖片，再發送提示詞
            commands = f".image {task['image_path']}\n{task['prompt']}\n"
            process.stdin.write(commands.encode('utf-8'))
            process.stdin.flush()
            process.stdin.close()
            
            buffer = b""
            last_progress_update = time.time()
            
            while True:
                if not self.is_running:
                    self.append_output("\n[已停止]\n")
                    break
                
                if self.check_timeout(start_time):
                    self.append_output(f"\n[超時警告]\n")
                    self.handle_timeout()
                    break
                
                try:
                    # 使用 binary 模式讀取
                    chunk = process.stdout.read(256)
                    if chunk:
                        buffer += chunk
                        last_progress_update = time.time()
                        
                        # 處理完整的行
                        while b'\n' in buffer:
                            line_bytes, buffer = buffer.split(b'\n', 1)
                            line = line_bytes.decode('utf-8', errors='replace')
                            
                            # 跳過 ANSI 轉義序列
                            line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
                            line = line.strip()
                            
                            # 跳過空行
                            if not line or len(line) < 2:
                                continue
                            
                            # 跳過 Thinking 標記
                            if 'Thinking' in line or 'thinking' in line.lower():
                                self.append_output("[模型思考中...]\n")
                                continue
                            
                            # 跳過 done thinking 標記
                            if 'done thinking' in line.lower():
                                continue
                            
                            if self.process_line(line, output_chunks):
                                total_tokens += 1
                                self.last_update_time = time.time()
                                self.stall_warning_shown = False
                                
                                elapsed = time.time() - start_time
                                speed = total_tokens / elapsed if elapsed > 0 else 0
                                self.root.after(0, self.update_progress, total_tokens, speed, elapsed, line, 2000)
                    else:
                        # 檢查進程是否結束
                        if process.poll() is not None:
                            # 處理剩餘 buffer
                            if buffer:
                                remaining = buffer.decode('utf-8', errors='replace')
                                remaining = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', remaining)
                                if remaining.strip():
                                    if self.process_line(remaining.strip(), output_chunks):
                                        total_tokens += 1
                            break
                        
                        # 短暫等待
                        time.sleep(0.05)
                        
                        # 每 5 秒更新停滯檢測
                        if time.time() - last_progress_update > 5:
                            last_progress_update = time.time()
                            self.last_update_time = time.time()
                except Exception as e:
                    self.root.after(0, self.show_error, str(e))
                    break
            
            process.wait()

        except Exception as e:
            self.root.after(0, self.show_error, str(e))
        finally:
            self.current_process = None
            full_output = "".join(output_chunks)
            self.save_result(f"圖片測試-{os.path.basename(task['image_path'])}", full_output, total_tokens, time.time() - start_time, "image")
            self.root.after(0, self.task_completed)

    def update_progress(self, tokens, speed, elapsed, last_chunk=None, expected=None):
        """更新進度"""
        self.tokens_var.set(f"{tokens} tokens")
        self.speed_var.set(f"{speed:.1f} tokens/s")
        self.elapsed_var.set(f"{elapsed:.1f}s")

        if self.check_stalled():
            self.stall_var.set("⚠️ 可能停滯了！")
        else:
            self.stall_var.set("")

        if last_chunk:
            self.append_output(last_chunk)

        if expected:
            progress = min(tokens / expected * 100, 100)
            self.progress_bar["value"] = progress
            self.progress_var.set(f"進行中... ({progress:.1f}%)")

        self.root.update_idletasks()

    def handle_timeout(self):
        """處理超時"""
        self.is_running = False
        self.status_var.set("已超時")
        self.progress_var.set("超時停止")
        self.stall_var.set("⏱️ 已超時")
        self.update_button_states()

    def task_completed(self):
        """任務完成"""
        self.is_running = False
        self.current_task = None
        self.update_button_states()
        self.status_var.set("完成")
        self.progress_var.set("測試完成")
        self.progress_bar["value"] = 100
        self.stall_var.set("✅ 完成")

    def stop_task(self):
        """停止任務"""
        self.is_running = False
        self.status_var.set("已停止")
        self.progress_var.set("已停止")
        self.stall_var.set("🛑 已停止")

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
        self.stall_var.set("")
        
    def append_output(self, text):
        """追加輸出文字"""
        try:
            self.output_text.insert(tk.END, text)
            self.output_text.see(tk.END)
        except:
            pass
        
    def show_error(self, error_msg):
        """顯示錯誤"""
        self.append_output(f"\n錯誤：{error_msg}\n")
        if self.current_task:
            task_name = self.current_task.get("name", "unknown") if isinstance(self.current_task, dict) else str(self.current_task)
            self.save_result(task_name, error_msg, 0, 0, "error")
        
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
        """匯出報告到 reports/ 資料夾"""
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
            report.append(f"  輸出預覽：{r['output'][:500]}...")
            report.append("")
            
        report.append("=" * 70)
        report.append("報告結束")
        report.append("=" * 70)
        
        # 確保使用 reports 資料夾
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filename = f"gemma4_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(REPORTS_DIR, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(report))
            self.append_output(f"\n✅ 報告已匯出至：{filepath}\n")
            messagebox.showinfo("匯出成功", f"報告已儲存至：\n{filepath}")
        except Exception as e:
            self.append_output(f"\n❌ 匯出失敗：{str(e)}\n")
            messagebox.showerror("匯出失敗", str(e))

    def unload_model(self):
        """手動卸載模型"""
        try:
            self.append_output("\n正在卸載模型...\n")
            self.append_output(f"指令: ollama stop {self.ollama.model_name}\n")
            self.root.update_idletasks()
            
            result = subprocess.run(
                ["ollama", "stop", self.ollama.model_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.append_output("等待模型卸載完成...\n")
            self.root.update_idletasks()
            
            for i in range(30):
                time.sleep(1)
                check_result = subprocess.run(
                    ["ollama", "ps"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if self.ollama.model_name not in check_result.stdout:
                    self.append_output(f"✅ 模型已從 VRAM 卸載（等待 {i+1} 秒）\n")
                    self.model_ready = False
                    self.model_status_var.set("Model unloaded")
                    self.model_status_label.config(fg="#e74c3c")
                    self.status_var.set("模型已卸載，請點擊『檢查模型』重新載入")
                    self.update_button_states()
                    return
            
            self.append_output("⚠️ 卸載逾時，模型可能仍在運行\n")
            self.append_output("💡 手動卸載指令: ollama stop gemma4:e4b-it-q4_K_M\n")
            
        except subprocess.TimeoutExpired:
            self.append_output("⚠️ 卸載逾時（60秒），請手動執行：ollama stop gemma4:e4b-it-q4_K_M\n")
        except Exception as e:
            self.append_output(f"❌ 卸載錯誤：{str(e)}\n")

    def on_closing(self):
        """關閉視窗時自動卸載模型"""
        try:
            if self.is_running and self.current_process:
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=2)
                except:
                    self.current_process.kill()
            
            subprocess.Popen(
                ["ollama", "stop", self.ollama.model_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            pass
        
        self.root.destroy()

# ========== 主程序 ==========
if __name__ == "__main__":
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()