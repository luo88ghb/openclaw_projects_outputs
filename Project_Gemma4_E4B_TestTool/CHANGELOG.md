# Gemma 4 E4B Q4_K_M 控制台測試工具 - 技術開發日誌

## 📋 文件資訊

| 欄位 | 內容 |
|------|------|
| 編撰者 | Zeni (傑尼) |
| 建立日期 | 2026-05-09 |
| 最近更新 | 2026-05-10 09:58 GMT+8 |

---

## 📝 版本疊代紀錄

### v1.3.4 (2026-05-12 01:05 GMT+8) - Zeni
**修復圖片測試 stdout/stderr 管道阻塞**
- 問題：同時使用 stdout=PIPE + stderr=PIPE 在 Windows 上會死鎖
- 原因：stderr 緩衝區被 "Added image" 訊息填滿後阻塞整個管道
- 修復：改用 stderr=subprocess.DEVNULL
- 測試：CLI 測試腳本驗證成功（27秒完成，完整輸出）
- 優化：buffer 增加至 256 bytes

### v1.3.3 (2026-05-12 00:50 GMT+8) - Zeni
**修復圖片測試阻塞問題**
- 問題：圖片測試執行後卡頓阻塞
- 原因：stdout 管道阻塞（與之前文字測試相同）
- 修復：增加 buffer 大小至 128 bytes
- 修復：新增圖片載入狀態檢測（"Added image"）
- 修復：跳過 Thinking 標記和進度動畫字符
- 修復：顯示「載入圖片」和「模型思考中」狀態

### v1.3.2 (2026-05-11 23:50 GMT+8) - Zeni
**修復圖片辨識使用本地模型**
- 問題：v1.3.1 使用 HTTP API 會調用雲端模型
- 修復：改用 Ollama CLI `.image <路徑>` 命令
- 格式：先發送 `.image <圖片路徑>`，再發送 prompt
- 移除：`requests` 模組依賴（不再需要）
- 測試：CLI 圖片載入成功，輸出正常

### v1.3.1 (2026-05-11 23:25 GMT+8) - Zeni
**修復圖片辨識測試功能**
- 問題：Ollama CLI 不支援 `--image` 參數
- 修復：改用 Ollama HTTP API (`localhost:11434/api/generate`)
- 新增：`requests` 模組處理 HTTP 請求
- 新增：base64 編碼圖片
- 測試：成功辨識 GUI 螢幕截圖（1690 tokens）

### v1.3.0 (2026-05-11 22:30 GMT+8) - Zeni
**功能增強：完整重構版本**
- 新增：報告匯出至 `reports/` 資料夾
- 新增：可編輯測試題目並儲存（黃色編輯按鈕）
- 新增：自訂測試題目功能（可儲存為常用）
- 新增：圖片辨識測試功能（支援 OCR/內容分析）
- 新增：JSON 配置檔案 `test_questions.json` 管理題目
- 優化：左側面板支援滾動
- 優化：視窗大小調整為 1200x950
- 修復：匯出報告路徑問題

### v1.2.6 (2026-05-11 20:15 GMT+8) - Zeni
**修復 Windows cp950 編碼問題**
- 問題：Windows 終端機使用 cp950 編碼，無法處理 UTF-8 字符
- 問題：`subprocess.Popen` 的 stderr 線程觸發 `UnicodeDecodeError`
- 修復：強制 `sys.stdout` 和 `sys.stderr` 使用 UTF-8 編碼
- 修復：`stderr=subprocess.DEVNULL` 避免 cp950 解碼錯誤
- 測試：簡易測試腳本 `simple_test.py` 驗證成功（32.87秒，3881字）

### v1.2.3 (2026-05-11 16:05 GMT+8) - Zeni
**發現系統級阻塞問題**
- 問題：即使使用 Bytes 串流讀取，自動評估腳本仍會卡住
- 測試結果：`auto_test_evaluator.py` 執行 5+ 分鐘後超時
- 診斷：Ollama CLI 在 Windows 上的 stdout 行為可能導致阻塞
- 建議：改用 Ollama HTTP API 而非 CLI
- 已同步修復 `auto_test_evaluator.py` 的 Bytes 串流讀取和 ANSI 過濾
- 已生成測試評估報告：`reports/test_report_2026-05-11.md`

### v1.2.0 (2026-05-09 23:04 GMT+8) - Zeni
**變更內容：**
- ✅ 完成 `Gemma4_E4B_測試工具.py` (GUI版)
  - 從 `Project_Zeni_Dashboard/gemma4_e4b_test_tool.py` 複製並增強
  - 強制 UTF-8 編碼輸出
  - 繁體中文提示
  - 進度停滯檢測（30秒無進展顯示警告）
  - Timeout 機制（5分鐘超時）
  - model_ready 模型狀態驗證（啟動時檢查，禁用直到就緒）
  - 停滯/超時警告標籤
- ✅ 完成 `Gemma4_E4B_Console_測試.py` (Console版)
  - 純命令列版本，適合自動化
  - JSON 格式輸出報告
  - 自動寫入 reports/ 目錄
- ✅ 完成 `auto_test_evaluator.py` (自動評估版)
  - 自動執行所有測試任務
  - 生成 Markdown + JSON 評估報告
  - 模型響應速度評估
  - 輸出品質評估（字數/預期字數）
  - 錯誤統計
  - 關鍵字覆蓋率評估
  - 品質分數計算

---

### v1.1.0 (2026-05-09 20:50 GMT+8) - Zeni
**變更內容：**
- ✅ 新增 README.md 專案規格書
- ✅ 新增模型加載狀態驗證（啟動時檢查，禁用直到就緒）
- ✅ 新增進度停滯檢測（30秒無進展提示「可能卡住」）
- ✅ 新增 Timeout 機制（防止無限等待）
- ✅ 強制 UTF-8 編碼（避免繁體中文亂碼）
- ✅ 獨立專案資料夾結構
- ✅ 測試報告輸出至 reports/ 目錄

---

## 🐛 Bug 修復紀錄

### Bug #1: 沒有模型加載驗證
**問題:** 工具啟動後立即可用，但模型可能未就緒
**影響:** 用戶點擊測試後發現模型不能用
**解決:** 啟動時檢查模型狀態，`model_ready` 為 False 時禁用測試按鈕

### Bug #2: 進度條不前進像是掛掉
**問題:** 測試時進度條卡住，用戶不知道是還在跑還是當機
**影響:** 用戶經常重啟或誤以為當機
**解決:** 加入進度停滯檢測，30秒無新輸出時顯示警告

### Bug #3: 沒有防崩潰機制
**問題:** 模型回應慢或停滯時，系統無反應
**影響:** 用戶只能強制關閉程式
**解決:** 加入 timeout 和進度停滯檢測，即時回饋用戶

### Bug #4: 繁體中文亂碼
**問題:** 模型輸出可能有亂碼
**影響:** 閱讀體驗差
**解決:** 強制 stdout 編碼為 UTF-8，確保繁體中文正常顯示

### Bug #5: StringVar 錯誤呼叫 config (v1.2.0)
**問題:** `self.model_status_var.config(fg="#2ecc71")` 導致 AttributeError
**影響:** 程式無法啟動
**解決:** 建立 `self.model_status_label` 參照，对 Label 呼叫 `.config()`

### Bug #6: 進度停滯在 0.2%~1.1% (v1.2.1)
**問題:** `readline()` 在 Windows 上有行緩衝延遲，導致模型輸出無法即時顯示
**影響:** 進度條卡在 0.2%~1.1%，看起來像當機
**解決:** 
- 改用原始 Bytes 串流 (`read(64)`)
- 手動處理行分割和 UTF-8 解碼
- 每 5 秒發送心跳更新，防止誤判停滯

---

## 🔧 技術細節

### 模型狀態檢測
```python
def check_model_status(self):
    """檢查模型狀態，若可用則設定 model_ready 為 True"""
    available, info = self.ollama.check_model()
    if available:
        self.model_ready = True
        self.model_status_label.config(fg="#2ecc71")
    else:
        self.model_ready = False
        self.model_status_label.config(fg="#e74c3c")
    self.update_button_states()
```

### 進度停滯檢測
```python
STALL_THRESHOLD = 30  # 30秒無更新視為停滯

def check_stalled(self):
    elapsed_since_update = time.time() - self.last_update_time
    if elapsed_since_update > STALL_THRESHOLD and not self.stall_warning_shown:
        self.stall_warning_shown = True
        return True
    return False
```

### Bytes 串流讀取（修復停滯問題）
```python
# 使用原始 Bytes 串流讀取
buffer = b""
while True:
    chunk = process.stdout.read(64)  # 每次讀取 64 bytes
    if chunk:
        buffer += chunk
        while b'\n' in buffer:
            line_bytes, buffer = buffer.split(b'\n', 1)
            line = line_bytes.decode('utf-8', errors='replace')
            # 處理行...
```

---

## 📁 檔案結構
```
Project_Gemma4_E4B_TestTool/
├── Gemma4_E4B_測試工具.py       # GUI 主程式 (v1.2.1) ⭐ 已修復停滯問題
├── Gemma4_E4B_Console_測試.py   # Console 測試版 (v1.2.0)
├── auto_test_evaluator.py       # 自動測試評估腳本 (v1.2.0)
├── README.md                    # 專案規格書
├── CHANGELOG.md                 # 本技術日誌
├── reports/                     # 測試報告輸出
│   └── .gitkeep
└── logs/                       # 日誌目錄
    └── .gitkeep
```

---

## ⚠️ 已知限制

1. 模型首次生成時可能需要較長的「思考時間」（非當機）
2. 進度停滯閾值（30秒）可能需要依硬體調整
3. Ollama CLI 必需已在背景運行
4. 品質分數計算為內部評估，僅供參考

---

## ✅ 已完成功能

- [x] model_ready 模型狀態驗證
- [x] 進度停滯檢測（30秒無進展顯示警告）
- [x] Timeout 機制（5分鐘超時）
- [x] UTF-8 編碼輸出
- [x] 繁體中文提示
- [x] Console 測試版本
- [x] 自動測試評估腳本
- [x] 品質分數評估
- [x] Markdown + JSON 報告生成
- [x] Bytes 串流讀取修復（解決進度停滯問題）

---

## 📌 待完成

- [ ] Cron Job 設定（每日 22:00 自動執行）
- [ ] 加入更精細的進度百分比估算
- [ ] 加入測試報告自動匯出到指定位置
- [ ] 加入多次測試的平均速度統計