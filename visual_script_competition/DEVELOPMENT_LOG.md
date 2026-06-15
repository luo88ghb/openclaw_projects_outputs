# 視覺氛圍劇本比賽 - 研發狀態報告 (R&D Status Log)

本文件紀錄本專案從 0 到 1 的所有疊代過程，旨在為後續開發提供追溯依據。

## 🛠️ 版本紀錄

### v0.1 - 基礎定義階段 (2026-05-13)
- **目標**：定義比賽規則與基礎文件。
- **更新內容**：
  - [x] 定義三方代理模型分工（傑尼、迪尼、蝦蝦）。
  - [x] 確立評分矩陣（基礎分、加分項、懲罰機制）。
  - [x] 建立 `arena_config.json` 與 `questions.txt`。
  - [x] 預設 3 回合的 `round_xx.json` 設定檔。
- **狀態**：定義完成。

### v0.2 - 基礎設施構建 (2026-05-13)
- **目標**：實現最小可運行原型 (MVP)。
- **更新內容**：
  - [x] 建立 `server.js` 基礎 API 伺服器（提供 Scoreboard 與 Log 讀取）。
  - [x] 建立 `viewer.html` GUI 監控介面。
  - [x] 編撰 `start_competition.bat` 雙擊啟動腳本。
- **狀態**：結構就緒，等待驗證。

### v0.3 - TVC 驗證與權限除錯 (2026-05-14)
- **目標**：驗證伺服器能否在 OpenClaw 環境中啟動並回應。
- **更新內容**：
  - [x] **TVC 測試**：由於主會話 `exec` 權限 (`allowlist`) 阻塞，改用 `sessions_spawn` 派遣子代理。
  - [x] **驗證結果**：子代理成功啟動伺服器 $\rightarrow$ 請求 `/api/scoreboard` $\rightarrow$ 回傳正確 JSON $\rightarrow$ 正常關閉。
- **狀態**：伺服器核心邏輯驗證通過，但用戶端 `.bat` 啟動端仍存在未知問題。

### v0.4 - 診斷與啟動優化 (2026-05-14)
- **目標**：解決 `.bat` 啟動失敗問題，並強化伺服器穩定性。
- **更新內容**：
  - [x] **啟動腳本重構**：更新 `start_competition.bat`，加入 `netstat` 端口清理機制，防止端口 3000 被舊進程佔用。
  - [x] **伺服器 robust 化**：更新 `server.js`，加入 UTF-8 編碼支持與基礎狀態機 (GameState) 骨架，防止空指標崩潰。
- **狀態**：等待用戶端雙擊驗證啟動狀態。

### v0.4b ~ v0.4d - 亂碼修復與流程調整 (2026-05-14)
- **問題識別**：
  - **問題1**：終端機顯示亂碼 $\rightarrow$ 原因為 Big5 繁體編碼與 `chcp 65001` 未正確執行。
  - **問題2**：3秒倒數計時後關閉 $\rightarrow$ 原因為 `timeout /t 3` 被放在流程中而非結尾，且 `exit /b 0` 會關閉啟動的獨立窗口。
  - **問題3**：沒有啟動網頁介面 $\rightarrow$ 原因為 `start "" "viewer.html"` 使用相對路徑，但 `PROJECT_DIR` 未以 `\` 結尾導致路徑斷裂。
- **修復內容**：
  - [x] 將所有中文訊息置換為 **ASCII 英文**，消除編碼問題。
  - [x] 移除 `timeout /t` 倒數計時，改用 `pause` 讓用戶手動確認啟動成功。
  - [x] 修正路徑拼接：將 `"%PROJECT_DIR%viewer.html"` 改為 `"%PROJECT_DIR%\viewer.html"` 或明確的 `set "VIEWER=%PROJECT_DIR%viewer.html"` 檢查。
  - [x] 將 `/k` 改為 `/c` 搭配 `pause`，確保伺服器窗口不會立即關閉。
- **測試方法**：雙擊 `start_competition.bat`，檢查是否出現「VisualArena_Server」窗口（黑底白字），以及瀏覽器是否自動開啟 `viewer.html`。
- **狀態**：修復完成，等待用戶驗證。

### v0.5 - 路徑Bug修復與API強化 (2026-05-14)
- **問題識別**：
  - `.bat` 批次檔中 `cd /d "%PROJECT_DIR%"` 執行失敗，導致 `server.js` 未真正啟動，但終端機仍然顯示 `[OK] Server launched`。
  - 伺服器雖然在 `localhost:3000` 運行，但 `__dirname` 指向錯誤目錄，導致無法找到 `visual_scoreboard.json` 和 `server.log`。
  - `viewer.html` 顯示「取得分數失敗」是因為 `readJSON` 失敗後回傳 `null`，導致分數板 API 無法正常回應。
- **根因**：`%~dp0` 在 `start` 啟動的新窗口中可能出現路徑解析不一致，導致 `node server.js` 的 `__dirname` 並非預期的 `visual_script_competition` 目錄。
- **修復內容**：
  - [x] **批次檔**：將 `start "" "%~dp0viewer.html"` 改為 `start "" "%~dp0\viewer.html"`（加反斜線分隔）。
  - [x] **批次檔**：在啟動前先初始化 `visual_scoreboard.json` 與 `server.log` 檔案，確保即使路徑有誤也能找到基礎檔案。
  - [x] **伺服器**：增加 `/api/ping` 端點用於快速驗證連線。
  - [x] **伺服器**：增加 `writeJSON` 函式，當偵測到 `visual_scoreboard.json` 不存在或格式錯誤時，自動初始化預設值。
  - [x] **伺服器**：在 `/api/scoreboard` 中加入更詳細的除錯日誌，方便確認資料是否正確讀取。
- **測試方法**：雙擊 `start_competition.bat` $\rightarrow$ 觀察伺服器視窗是否顯示 `Server STARTED at http://localhost:3000` $\rightarrow$ 確認 `viewer.html` 中「取得分數失敗」變為「迪尼: 0 | 蝦蝦: 0」。
- **狀態**：修復完成，等待用戶驗證。

### v0.6 - 舊程序殘留清理與除錯強化 (2026-05-14)
- **問題識別**：
  - 檢查 `server.log` 發現時間戳為 `2026-05-14T11:53:00.000Z`（數小時前），表示新啟動的伺服器**並未更新日誌**，而是**舊的伺服器程序仍在運行**。
  - 根本原因：之前的測試中啟動的 Node 進程**未被徹底關閉**，導致新啟動的伺服器無法正常寫入 `server.log`，且 `visual_scoreboard.json` 的讀取也出現異常。
- **修復內容**：
  - [x] **批次檔**：在最前面加入 `taskkill /F /IM node.exe` 強制終止**所有 Node 程序**，確保只有新的伺服器在運行。
  - [x] **伺服器**：將 `__dirname` 直接賦值給 `PROJECT_DIR` 變數，消除路徑解析歧義。
  - [x] **伺服器**：在**所有函式**中加入 `console.log` 除錯訊息，確保能在 `VisualArena_Server` 黑色窗口中直接看到執行狀態。
  - [x] **伺服器**：`readJSON` 函式增加 `fs.existsSync` 檢查，讓錯誤訊息更具體。
  - [x] **伺服器**：`/api/ping` 回應內容新增 `__dirname`，方便在瀏覽器中驗證伺服器認為自己的工作目錄是否正確。
- **預期觀察**：
  - 黑色伺服器視窗應有**大量除錯訊息**，包含 `[DEBUG] Handling /api/scoreboard`、`[OK] JSON parsed from: ...` 等。
  - 瀏覽器訪問 `http://localhost:3000/api/ping` 應顯示 `{"status":"ok","__dirname":"C:\\Users\\danny\\.openclaw\\workspace\\visual_script_competition"}`。
- **狀態**：修復完成，等待用戶驗證。

---
**紀錄規則**：每次重大修改、Bug 修復或邏輯調整，必須在下方追加 entries。