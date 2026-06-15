# Gemma4_E4B_測試工具 最終版技術報告

## 目標與範圍
- 提供一個 **本地端** 使用 `gemma4:e4b-it-q4_K_M` 模型的圖形化測試平台。
- 支援文字任務、推論題、使用者自訂測試、以及 **圖片辨識 (OCR/內容分析)** 四大類測試。
- 產出 **報告匯出**、**模型卸載**、**進度監控**、**阻塞與逾時防護** 等完整流程。

---

## 1. 技術思維圖（概念層）
```
+-------------------------------------------+
|               Gemma4_E4B_測試工具          |
| (Tkinter GUI + 多執行緒)                 |
+-------------------+-----------------------+
                    |
                    v
+-------------------+-----------------------+
|   Ollama CLI 客戶端 (OllamaCLI)          |
|   - check_model()                           |
|   - run <model> (stdin)                     |
|   - .image <path> (圖片載入)                |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|   任務類別                                 |
|   • 文字任務 (Academic, Sci-Fi)          |
|   • 推論測驗 (5 題)                     |
|   • 自訂測試 (使用者 Prompt)           |
|   • 圖片辨識測試 (OCR/內容分析)        |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|   核心模組                                 |
|   • 進度監控 (progress bar, speed, tokens) |
|   • 阻塞偵測 (STALL_THRESHOLD = 30s)      |
|   • 超時機制 (MAX_WAIT_SECONDS = 300s)      |
|   • 錯誤處理 (stderr=DEVNULL)                |
|   • 輸出匯出 (reports/*.txt)              |
+-------------------------------------------+
                    |
                    v
+-------------------------------------------+
|   永續資料 (JSON)                         |
|   • test_questions.json (任務、推論、客製) |
|   • reports/ (報告)                         |
+-------------------------------------------+
```

---

## 2. 系統組件說明
| 組件 | 功能 | 主要實作檔案 | 重點實作說明 |
|------|------|--------------|--------------|
| **GUI 主程式** | Tkinter 界面、按鈕、進度、輸出、匯出、模型卸載 | `Gemma4_E4B_測試工具.py` | 使用多執行緒避免 UI 卡死；`run_image_test`、`run_task`、`run_reasoning` 分別處理四種任務。 |
| **OllamaCLI** | 包裝 `ollama list`、`ollama run` | 同上 | `check_model` 取得模型狀態，`run` 以 `subprocess.Popen` 直接與 CLI 溝通，`stderr=DEVNULL` 防止 stdout/stderr 阻塞。 |
| **任務管理** | 讀寫 `test_questions.json`、動態生成任務列表 | 同上 | `load_questions`、`save_questions`；支援編輯、刪除、自訂保存。 |
| **圖片測試模組** | 圖片載入、`.image` 指令、Prompt 合併 | 同上 | `ImageTestDialog` 取得圖片路徑與 base64，`run_image_test` 先發送 `.image <path>` 再發送 prompt，使用 256 Byte buffer 讀取 stdout。 |
| **阻塞/逾時防護** | `STALL_THRESHOLD`、`MAX_WAIT_SECONDS` | 同上 | `check_stalled` 每 5 秒檢查，超過顯示警告；`check_timeout` 超過 5 分鐘自動停止。 |
| **報告匯出** | Markdown/文字報告保存至 `reports/` | 同上 | `export_results` 產生 `gemma4_test_report_YYYYMMDD_HHMMSS.txt`，包含任務資訊、耗時、tokens、輸出摘要。 |
| **模型卸載** | `ollama stop <model>` 並等待完成 | 同上 | `unload_model` 呼叫 `ollama stop`，使用 `check_model_status` 確認已卸載。 |

---

## 3. 開發流程圖（開發階段）
```
1. 需求收集 & 設計
   - 功能需求：文字測試、推論測驗、圖片辨識、匯出、模型卸載
   - UI 原型 (Tkinter Layout)
   - JSON 配置文件結構設計

2. 原型實作 (v1.0.0)
   - 基本 GUI 框架
   - `OllamaCLI.check_model`
   - `run_task` 使用 `subprocess.Popen` 串流讀取
   - 初步報告匯出

3. 迭代改進 (v1.1.0 – v1.2.0)
   - 文字編碼強制 UTF‑8 (解決 cp950)
   - 進度條、速度、Token 計算
   - 加入超時與阻塞偵測
   - 加入模型自動卸載

4. 功能擴充 (v1.2.1 – v1.2.6)
   - 推論題 UI 與編輯功能
   - 自訂測試對話框
   - `test_questions.json` 持久化
   - `auto_test_evaluator.py` 自動評估腳本
   - 圖片辨識概念驗證 (HTTP API 版)

5. 圖片測試重構 (v1.3.0 – v1.3.2)
   - 替換 HTTP API 為 Ollama CLI `.image` 命令
   - 移除 `requests` 依賴
   - 加入圖片載入提示與 `stderr=DEVNULL`
   - 改善緩衝區大小 (128 → 256 bytes)
   - UI 新增「圖片辨識測試」區塊

6. 阻塞與逾時終極修正 (v1.3.3 – v1.3.4)
   - 完全解決 stdout/stderr 死鎖問題
   - 進度停滯警告顯示
   - 超時機制加強 (5 分鐘)
   - 版本號升至 v1.3.4，更新說明檔 & CHANGELOG

7. 最終測試與文件化 (v1.3.4)
   - 完整測試：文字、推論、自訂、圖片
   - 生成 `CHANGELOG.md`、`README.md`
   - 撰寫本技術報告 (即本文件)
   - 版本 Tag `v1.3.4`
```

---

## 4. 使用說明（快速上手）
1. **啟動**  
   ```powershell
   python Gemma4_E4B_測試工具.py
   ```
2. **模型檢查** – 程式啟動後自動檢查模型狀態，綠燈即表示可用。
3. **執行任務** – 點擊左側任務按鈕（文字、推論、自訂、圖片）。
4. **匯出報告** – 完成後點擊「匯出報告」產生 `reports/gemma4_test_report_YYYYMMDD_HHMMSS.txt`。
5. **卸載模型** – 若需釋放顯存，點擊「卸載模型」即可。

---

## 5. 未來展望
- **自動化測試 pipeline**：結合 `cron` 每日跑完整測試套件。
- **多模型支援**：在 UI 中切換不同 Ollama 模型。
- **更細緻的圖片 OCR**：整合 Tesseract 或 Vision API 取得文字層。
- **圖形化流程圖產出**：利用 `graphviz` 自動產生任務依賴圖。

---

*此報告為後續代理人快速理解與延伸開發的基礎文件。*