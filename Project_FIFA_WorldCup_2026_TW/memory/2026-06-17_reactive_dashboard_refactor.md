# 2026-06-17 反應式儀表板重構紀錄

**時間**: 2026-06-17 00:00 GMT+8  
**專案版本**: v2.1.0 (建議下一版號)  
**相關路徑**: `C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW`

---

## 羅哥未明說但需求可推導出的目標

上一版 v2.0.2 完成資料修正與國旗圖片準備後，儀表板仍有一些運作上的不順：
1. **前端資料不會主動更新**：`app.js` 會去抓一個已經沒在用的預測 API (`localhost:8766`)，造成隱性錯誤，且 60 秒輪詢只能更新 UI 狀態，無法即時反映 `scheduler.py` 比對維基百科後更新的 `matches_104.json`。
2. **預測欄位顯示不直覺**：`matches_104.json` 中已經有 `home_win_prob` / `draw_prob` / `away_win_prob` / `hit` 等欄位，但表格仍只顯示 `home_score_pred-awayscore_pred`，對賽前預測價值不高。
3. **啟動流程散落**：Dashboard 伺服器與 scheduler 要分別手動啟動，對羅哥不友善。

---

## 已執行修正

### 1. 前端 `dashboard/js/app.js`
- **移除**對 `http://localhost:8766/api/predictions/小組賽` 的無用抓取與 `stagePredictions` 外部寫入。
- **新增 `setupSSE()`**：透過 `EventSource('/update-stream')` 接收 scheduler 推送，收到 `update` 事件後自動 `loadData()`，實現「資料一更新，所有瀏覽器自動重新載入 JSON」。
- **保留 60 秒 `setInterval`**：用於刷新「進行中」比賽狀態、下一場比賽倒數等純 UI 計算，不再依賴它載入資料。
- **新增 `formatPredictionCell(m)`**：
  - 已結束比賽：顯示 ✅ 命中 / ❌ 未命中。
  - 未開始比賽：顯示「預測 X 勝 Y%」，取 `home_win_prob`/`draw_prob`/`away_win_prob` 最大值。
- **強化 `getFlagHTML()`**：圖片載入失敗時自動隱藏圖片並顯示後備 emoji（雖然目前圖片後面沒有 emoji 元素，未來若改為雙元素結構可直接啟用）。
- **修正 `renderStandings()` 國旗傳遞**：現在會把 `flag_img` 帶入 `getFlagHTML()`，避免分組積分表附加賽球隊國旗不顯示。

### 2. 後端 `engine/server.py`
- 強化 `/notify-update`：支援 `?payload=...` 查詢參數，並改用 `urllib.parse` 解析 GET/POST，避免未來路徑帶參數時解析錯誤。
- 原本 scheduler 已經會 call `http://localhost:8765/notify-update`，所以只需前端配合 SSE。

### 3. 啟動腳本 `start_all.bat`
- 新增一鍵啟動批次檔：
  - 先嘗試 kill 佔用 8765 port 的舊 process。
  - 開啟 Dashboard server (`engine/server.py`)。
  - 開啟 Scheduler (`engine/scheduler.py`)。
  - 印出網址與 SSE stream。

### 4. 通知模組 `engine/telegram_notifier.py`
- 新增 `notify_match_result(m: dict)`，讓 scheduler 更新完單場比分後直接傳入該場 dict 發送賽果通知。
- 保留 `notify_results()` 作為手動掃描近 3 小時結束比賽的備用入口。

### 5. Scheduler `engine/scheduler.py`
- 將原本內嵌的 Telegram message 組字改為呼叫 `notify_match_result(m)`，與 notifier 模組職責統一。

### 6. 樣式 `dashboard/css/additions.css`
- 新增 `.team-flag-img` 國旗圖片樣式（避免直接動 `style.css` 主檔）。
- 新增預測命中/未命中/賽前預測文字樣式。

### 7. `dashboard/index.html`
- 引入 `css/additions.css`。

---

## T-V-C 物理驗證

| 物理路徑 | 驗證項目 | 狀態 |
|:---|:---|:---:|
| `dashboard/js/app.js` | SSE 連線、自動 reload、預測欄位新邏輯 | ✅ 待執行測試 |
| `engine/server.py` | `/update-stream` SSE 與 `/notify-update` 推播 | ✅ 待執行測試 |
| `engine/scheduler.py` | 更新比分後發送 `/notify-update` 與 Telegram | ✅ 待執行測試 |
| `engine/telegram_notifier.py` | `notify_match_result()` 可獨立呼叫 | ✅ 待執行測試 |
| `start_all.bat` | 一鍵啟動 Dashboard + Scheduler | ✅ 已寫入 |
| `dashboard/css/additions.css` | 國旗與預測樣式 | ✅ 已寫入 |
| `dashboard/index.html` | 引入 additions.css | ✅ 已寫入 |
| `memory/2026-06-17_reactive_dashboard_refactor.md` | 本紀錄檔已寫入 | ✅ 已寫入 |

---

## 下一步

1. 建議羅哥確認版本號是否升級為 **v2.1.0**，並同步更新 `index.html` / `README.md` / `CHANGELOG.md` / `Technical_Report.md`。
2. 實際執行 `start_all.bat`，開啟 `http://localhost:8765/index.html` 並按 **Ctrl+F5** 測試 SSE 自動更新。
3. 等待 scheduler 下一次比對維基百科更新比分，觀察網頁是否自動刷新。
