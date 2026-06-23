<!-- 下載時間: 2026-06-23 03:19:30 Asia/Taipei | 版本: v2.2.7 -->
# Changelog
## 2026-06-24 v2.2.9
### 新增
- **用戶反饋模型機制（User Model Feedback）**：
  - 儀表板預測歷史 modal 中新增 L1 / L2 模型反饋面板，用戶可針對每場次給予 +1 / +0.5 / -0.5 / -1 的獎懲評分。
  - 前端：`dashboard/index.html` modal 擴充反饋區；`dashboard/css/additions.css` 新增反饋面板樣式；`dashboard/js/app.js` 負責載入、渲染與送出。
  - 後端：`engine/api_server.py` 新增 `POST /api/feedback` 與 `GET /api/feedback?match_id=`，儲存於 `data/user_model_feedback.json`。
  - 預測引擎：`engine/worldcup_engine.py` 載入反饋權重，正/負反饋會微調對應模型的預期進球（±0.5 球 / ±0.25 球）。
  - 資料：`data/user_model_feedback.json` 採用 v1 schema，記錄 `match_id`、`model`、`feedback`、`timestamp`。

## 2026-06-23 v2.2.8
### Fixed
- `engine/scraper.py`:
  - `find_match_id()` now also accepts swapped home/away pairings; some public sources (e.g., FIFA-TW) list teams in the opposite order from our internal schedule.
  - Result merging is now source-count-agnostic and flags score conflicts across all active sources instead of hardcoding Wikipedia/FIFA-TW comparison.
- `engine/worldcup_engine.py`:
  - Added relative-import fallback so the module can be executed both via `python -m engine.scorer` and directly.
- `engine/score_updater.py`:
  - Reverted to absolute import so direct CLI usage works alongside module execution.
- `engine/__init__.py`:
  - Added empty `__init__.py` to make `engine` a package, enabling `python -m engine.*` invocations.
- Updated data:
  - Match #41 阿根廷 vs 奧地利 now has final score 2-0 and prediction hit=true.
  - Regenerated all stage predictions and saved updated `predictions_db.json` / `scraped_results.json`.

所有版本迭代與重要變更都記錄於此。格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)。

---

## [2.2.7] - 2026-06-23

### 雜項
- 統一版本標記與下載時間戳。

## [2.2.7] - 2026-06-22

### 新增
- **預測審查評語（Strict Reviewer / 教練風格）**：
  - 不再只判斷「模型一致 / 分歧」，而是像嚴格教練對 L1、L2 兩位選手逐場打分（A/B/C/D）與評語。
  - 評估面向：預測穩定性、機率合理性、和局機率是否被壓抑、比分預測是否離譜、是否過度自信。
  - 顯示逐模型「值得鼓勵」與「需要檢討」的具體評語。
  - 若比賽已結束，直接比較哪個模型命中、哪個失準，並點名過擬合或保守問題。
  - 底部給出教練總評，提供可操作的參考建議。

### 修正
- **儀表板預測文字顏色修正**：主表單與預測歷史頁面的命中/未命中/未開賽狀態使用高對比色（黃/綠/紅），避免被已完成場次的灰色字樣覆蓋。
- **預測歷史頁面欄位調整**：命中狀態欄提前，並加粗提升可讀性。

---

## [2.2.5] - 2026-06-21

### 修正
- **過場更新與預測命中同步問題**：
  - 用戶回報：部分已過開球時間的場次未即時補抓比分，且 Telegram 與儀表板的命中判定不同步。
  - 統一後端 `engine/worldcup_engine.py` 與 `engine/telegram_notifier.py` 的計分邏輯：皆以預測機率最高者（主勝/和局/客勝）對比實際結果，機率全為 0 時才回退到比數預測；命中 score 固定為 ±1，不再因比分差異而變動。
  - 重新跑 `check_prediction()` 校正所有 36 場已結束場次的 `hit` / `score` 與 `predicted_outcome` / `actual_outcome`。

### 修正
- **淘汰賽台灣時間錯誤**：
  - 用戶回報淘汰賽（match_id 73–104）的 `date` / `time_taiwan` 與維基百科的當地開賽時間換算後不一致。
  - 問題原因：原始資料以錯誤的 UTC 偏移推導台灣時間，導致多數場次被標成隔天凌晨/早晨。
  - 現已根據維基百科的當地時間，統一減 14 小時換算為台灣時間（Asia/Taipei UTC+8），更新 32 場淘汰賽的 `date` / `time_taiwan`。

### 新增
- **儀表板「跳到最近賽局」按鈕**：
  - 在「完整賽程」標題右側新增 `⬇️ 跳到最近賽局` 按鈕，點擊後自動捲動至視窗中心場次（比賽中 > 下一場 > 最後結束）並高亮該行。
  - 新增對應樣式 `.highlight-row` 於 `dashboard/css/additions.css`。

---

## [2.2.1] - 2026-06-19

### 修正
- **開賽前 30 分鐘 Telegram 提醒重複/遺漏問題**：
  - 根據用戶回報，#25、#28 等場次未準時收到開場推播。
  - 問題原因：`run_kickoff_notifier()` 原本只取第一個符合條件的場次通知一次，且未記錄已通知場次，導致重啟後會重複通知或跳過。
  - 改為：每分鐘掃描，只選出最接近開賽的未結束場次；已通知場次寫入 `predictions/kickoff_notified.json`，避免重複；支援 `match_id` 精準指定單場通知。
  - `notify_upcoming()` 新增 `match_id` 選項，可單獨通知指定場次。

### 新增
- `predictions/kickoff_notified.json`：持久化已通知場次清單。

---

## [2.2.0] - 2026-06-19

### 新增
- **進階預測系統**：新增 engine/advanced_predictor.py，採用三視角模型（Vector_A 量化數據 40%、Vector_B 戰術相剋 35%、Vector_C 外部變數 25%）。
- **預測研究快取**：新增 cache/prediction_research_cache.json，儲存 search 工具搜集的各隊真實資料。
- **預測報告生成器**：新增 engine/generate_prediction_report.py，輸出 predictions/Advanced_Prediction_Report.md。
- **並行資料搜集**：啟動 3 個 subagent 並行回填 B~L 組共 44 支球隊研究資料。

### 變更
- predictions/advanced_predictions.json 現包含 72 場小組賽預測與 32 強晉級名單。

### 備註
- 淘汰賽推演將在小組賽結果確認後繼續開發。

---

## [2.1.7] - 2026-06-18

### 新增
- **自動產生賽前預測**：新增 `engine/generate_predictions.py` 腳本，為所有 `status: scheduled` 且 `prediction: null` 的場次自動產生預測。
  - 預測內容包含：主客隊比分預測、勝率機率（主勝/和局/客勝）、預測依據（FIFA 排名 + 累積向量）。
  - 執行 `python engine/generate_predictions.py` 可批次產生預測。
- **Telegram 開賣前 30 分鐘提醒**：`scheduler.py` 新增 `run_kickoff_notifier()` 背景執行緒，每分鐘檢查是否有比賽在 30 分鐘內開賽，自動發送提醒訊息。
  - 提醒訊息包含：場次、對戰、時間、地點、預測勝隊與勝率。

### 變更
- **Schedule Section 預測欄位修正**：
  - 未開賽場次現在會顯示「預測 [隊名] 勝 [勝率]%」，不再空白。
  - 已結束場次顯示「✅ 命中」或「❌ 未命中」。
- **Telegram 賽果推播內容優化**：
  - 改為顯示「預測：[隊名] ✅ 命中 / ❌ 未命中 | 實際：[結果]」
  - 不再顯示預測比分（因為比分預測準確度極低，勝隊預測較具參考價值）。

### 備註
- 預測產生後，前端 Schedule Section 的「預測」欄位已不再空白。
- Telegram 推播需設定環境變數 `TELEGRAM_BOT_TOKEN` 與 `TELEGRAM_CHAT_ID`。

---

## [2.1.6] - 2026-06-18

### 重大修正
- **Next Match Card 邏輯改為「以場次為基礎的滑動視窗」**：
  - 不再以日期定位，改以 `match_id` 順序滑動。
  - **已結束比賽**：固定顯示以中心場次為基準，往前最多 4 場已結束比賽。
  - **比賽中**：若存在進行中比賽，獨立顯示在「🔴 比賽中」區塊。
  - **下一場比賽**：固定顯示中心場次往後最多 4 場尚未開賽的比賽。
  - 中心場次判定優先順序：進行中比賽 > 下一場未賽比賽 > 最後一場已結束比賽。
  - 隨著比賽結束，視窗會自動向前輪替。

### 變更
- `js/app.js` 新增 `FOCUS_WINDOW_SIZE = 4` 常數與輔助函式 `getMatchWindowCenter()`、`getMatchByOffset()`。
- `renderMatchInfo()` 新增 `compact` 選項，讓多場次列表更緊湊。
- `css/additions.css` 微調行距與新增比賽中區塊標題紅色樣式。
- 更新 `dashboard/index.html` 前端版本號為 `v2.1.6`，最後更新時間為 **台北時間 2026-06-18 17:40**。

---

## [2.1.5] - 2026-06-18

### 重大修正
- **Next Match Card 邏輯重新設計**：
  - 以「下一場未賽 / 進行中比賽」所在的日期定義為「今日」。
  - **上半區「今日已結束比賽」**：列出該日所有 `status: finished` 的場次。
  - **下半區「今日賽程（尚未開賽 / 比賽中）」**：列出該日所有未結束場次，進行中比賽顯示「● 比賽中」與即時比分。
  - 隨著比賽進行，場次會自然從下半區移動到上半區。
  - 當「今日」所有比賽結束後，自動推進到下一個有賽事的日期。
  - 例：下一場未賽 #25 為 2026-06-19 00:00，則「今日」= 2026-06-19，目前因 #25 尚未開賽，上半區顯示 2026-06-18 的 #21~#24；待 #25 開始後「今日」切換為 2026-06-19，顯示 #25 狀態，#26~#28 列於下半區。

### 變更
- `renderMatchInfo()` 現在三態顯示：已結束（比分綠色）、比賽中（紅色閃爍 ● 比賽中 + 即時比分）、尚未開賽（灰色）。
- 移除 `getPreviousDay()`，改為 `getTodayOfNextUpcoming()` 動態判定「今日」日期。
- 更新 `dashboard/css/additions.css`：新增比賽中動畫與三態顏色區分。
- 更新 `dashboard/index.html` 前端版本號為 `v2.1.5`，最後更新時間為 **台北時間 2026-06-18 16:40**。

---

## [2.1.4] - 2026-06-18

### 修正
- **Next Match Card 邏輯修正**：原「最後完成單場」改為顯示「次日的已結束比賽」。
  - 以「下一場未賽比賽」的日期為基準，往前推一天，列出該日所有 `status: finished` 的場次。
  - 例：下一場未賽為 #25（2026-06-19 00:00），則顯示 2026-06-18 的 #21、#22、#23、#24 四場已結束比賽。
- 新增 `getPreviousDay()` 輔助函式，使用 Asia/Taipei 時區計算前一天日期。
- 更新 `renderMatchInfo()` 為通用行內賽事資訊渲染，移除固定的 `last` / `next` 標籤，改由區塊標題區分。
- 更新 `dashboard/css/additions.css` 樣式，使多場次日賽事以緊湊行內形式呈現。

### 變更
- 更新 `dashboard/index.html` 前端版本號為 `v2.1.4`，最後更新時間為 **台北時間 2026-06-18 15:35**。

---

## [2.1.3] - 2026-06-18

### 新增
- **Next Match Card 上方補上「最後完成比賽」資訊**：`js/app.js` 新增 `renderMatchInfo()` 通用渲染函式，`renderNextMatch()` 同時顯示最近一場已完成比賽與下一場未賽比賽。
- **建立 v2.1.2 備份**：複製 `dashboard/` 至 `dashboard_v2.1.2_backup/`，保留 GUI 修改前的對照基準。

### 修正
- **修復 Stage Filter / Group Filter 篩選失效問題**：`js/app.js` 新增 `setupFilters()`，在 `loadData()` 初始化後為階段下拉、組別下拉、搜尋框綁定 `change` / `input` 事件，即時觸發 `renderMatches()`。

### 變更
- Next Match Card 標題由「下一場比賽」改為「賽事焦點」，以反映同時顯示「最後完成 + 下一場」的內容。
- 更新 `dashboard/index.html` 前端版本號為 `v2.1.3`，最後更新時間為 **台北時間 2026-06-18 15:20**。
- 新增 `dashboard/css/additions.css` 樣式，區分「最後完成」與「下一場」兩筆賽事資訊的視覺層級。

### 備註
- 篩選功能失效原因：v2.0.2 之後重構 `loadData()` 時遺漏了事件監聽器綁定，導致下拉選單變更不會重新渲染賽程表。

---

## [2.1.2] - 2026-06-18

### 修正
- 修復 `engine/server.py` 單執行緒導致 SSE 長連線阻塞資料載入的問題：改為 `socketserver.ThreadingTCPServer`。
- 新增 `/api/status` 與 `/api/shutdown` 端點，支援遠端查看狀態與優雅關閉。
- 新增 `start_dashboard.bat` 與 `stop_dashboard.bat`，雙擊即可開啟/關閉儀表板伺服器。
- 更新 `start_all.bat` 為一鍵啟動伺服器 + 排程器。

### 備註
- 之前開啟網頁但資料載不進來，是因為 SSE 連線佔住伺服器執行緒；改用多執行緒後已解決。

---

## [2.1.1] - 2026-06-17

### 修正
- 補齊 `data/teams.json` 中庫拉索 (CUW) 缺少的 `flag_img` 欄位：`flags/Flag_of_Curacao.png`。
- 更新 `dashboard/index.html` 前端版本號為 `v2.1.1`，最後更新時間為 **台北時間 2026-06-17 12:05**（比賽現場時間 2026-06-16 22:05）。

### 備註
- 確保全部 48 支參賽球隊皆有 `flag_img`，儀表板可統一顯示國旗圖片。

---

## [2.1.0] - 2026-06-17

### 新增
- **時間校正自動更新機制**：新增 `engine/scheduler.py`，持續以台灣時間（Asia/Taipei, UTC+8）掃描 `matches_104.json`，在每場比賽開賽時間 **+120 分鐘** 自動觸發。
- **維基百科比分抓取**：新增 `engine/wiki_scraper.py`，觸發時自動抓取中文維基百科 2026 世界盃頁面，更新該場比賽的比分與狀態。
- **主動推送儀表板**：`engine/server.py` 新增 SSE（Server-Sent Events）端點 `/update-stream`，資料更新後主動通知前端重新載入。
- **Telegram 賽後通知**：排程器觸發後自動發送賽果與「預測（賽前基礎版）」命中狀態。
- **一鍵啟動腳本**：新增 `start_all.bat`，同時啟動 HTTP 伺服器與時間校正排程器。

### 變更
- **還原並強化「預測（賽前基礎版）」欄位**：
  - 賽前：賽程表「預測」欄顯示預測勝隊與勝率（例如 `預測 法國 勝 58%`）。
  - 賽後：顯示預測是否命中（`✅ 命中` / `❌ 未命中`）。
- **賽前自動產生預測**：`engine/worldcup_engine.py` 在排程器執行時，自動為尚未設定預測的比賽產生基礎預測。

### 技術備註
- 觸發時間計算方式：`datetime(date + time_taiwan) + timedelta(minutes=120)`，使用台灣時間（Asia/Taipei, UTC+8）作為系統時間。
- 若觸發時維基百科尚未公布該場比分，則每 5 分鐘重試一次，最多持續 60 分鐘，直到取得有效比分。
- 排程器偵測到下一場未賽比賽後，會以該場開賽時間 +120 分鐘設為下一次觸發點，避免無意義輪詢。
- 資料來源：中文維基百科 — 2026年國際足總世界盃。

## [2.0.2] - 2026-06-16

### 修正
- **Match 4 (D組)**：比分從「美國 2-0 巴拉圭」改回「**美國 4-1 巴拉圭**」（依據維基百科 2026 世界盃賽程頁面）。
- **Match 13 (H組)**：比分從「西班牙 1-1 維德角」改為「**西班牙 0-0 維德角**」（依據維基百科 2026 世界盃賽程頁面）。
- **隊名修正**：「波士尼亞」統一更名為「**波赫**」（依據維基百科繁體中文慣用譯名）；同步修正 `teams.json` 中 `BIH` 的國旗 emoji 為 `🇧🇦`。

### 變更
- 國旗顯示方式準備改為維基百科國旗圖片（`download_flags.ps1` 腳本 + `dashboard/flags/` 資料夾），前端 `app.js` 同步支援 `<img>` 載入國旗。

### 資料來源
- 中文維基百科：2026年國際足總世界盃 https://zh.wikipedia.org/zh-tw/2026%E5%B9%B4%E5%9C%8B%E9%9A%9B%E8%B6%B3%E5%8D%94%E4%B8%96%E7%95%8C%E7%9B%83

---

## [2.0.1] - 2026-06-16

### 修正
- 移除 `matches_104.json` 中所有「附加賽勝者A ~ F」佔位符隊名，替換為 FIFA 2026 世界盃附加賽晉級真實球隊：
  - 附加賽勝者A → 捷克（Group A）
  - 附加賽勝者B → 波士尼亞（Group B）
  - 附加賽勝者C → 土耳其（Group D）
  - 附加賽勝者D → 瑞典（Group F）
  - 附加賽勝者E → 伊拉克（Group I）
  - 附加賽勝者F → 剛果民主共和國（Group K）
- 新增上述 6 支球隊到 `teams.json`，補齊 id、英文名稱、洲協、小組、FIFA 排名、種子序、國旗 emoji。
- 修正 **Match 4 (D組)** 比分：從「美國 4-1 巴拉圭」改為「**美國 2-0 巴拉圭**」（對照 2026fifa.tw 官方賽果）。

### 備註
- 後續於 v2.0.2 根據維基百科修正回「美國 4-1 巴拉圭」。

### 資料來源
- 2026 FIFA 世界盃附加賽結果：worldcupwiki.com / 2026fifa.tw
- 即時賽程與比分：2026fifa.tw

---

## [2.0.0] - 2026-06-16

### 修正
- **Match 15 (H組)**：修正主客隊順序與比分，從「沙烏地阿拉伯 0-0 烏拉圭」改為「烏拉圭 1-1 沙烏地阿拉伯」（依據 FIFA 官方資料）。
- **Match 16 (G組)**：修正主客隊順序與比分，從「伊朗 0-0 紐西蘭」改為「紐西蘭 2-2 伊朗」（依據 FIFA 官方資料）。
- 修正 header 顯示：新增版本號 (v2.0.0) 與最後更新時間，方便追蹤資料狀態。

### 資料來源
- 比對來源：FIFA 官方網站 (fifa.com) 與台灣世足資訊站 (xn--fifa-tc5fq65k1ju.tw)
- 官方比分驗證：
  - 烏拉圭 1-1 沙烏地阿拉伯 (Maxi Araújo 80' 烏拉圭 / Abdulelah Al-Amri 41' 沙烏地阿拉伯)
  - 紐西蘭 2-2 伊朗 (E. Just 7', 54' / R. Rezaeian 32', M. Mohebi 64')

### 版本號說明
- 自 2026-06-16 起，本專案正式進入 **v2.0.0** 迭代週期。
---

## [1.1.0] - 2026-06-15 → 已回滾 (Rolled Back) → 不納入正式版本

> ⚠️ 羅哥反饋 v1.1 的界面修改不符合需求（特別是賽程表的「預測」欄位被改為「狀態」），因此已從 `dashboard_v1_backup/` 完整還原為 v1.0 樣式。此版本從未正式發布，僅供參考。本專案自 2026-06-16 起正式進入 **v2.0.0** 迭代週期。

### 新增（已撤銷）
- 儀表板頂部新增「賽事進度」統計卡：總場次 / 已結束 / 今日 / 即將 24 小時。
- 儀表板新增「狀態」篩選與狀態標籤（未開賽 / 進行中 / 已結束）。
- 下一場開賽卡片新增倒數計時（還有 X 天 X 小時 X 分鐘）。
- 分組積分卡片標示前 2 名晉級線與晉級底色。
- 新增響應式表格橫向捲動，手機也可正常瀏覽。

### 變更（已撤銷）
- 將原本佔據 Hero 區的「進階預測」區塊，改為獨立彈出視窗入口，主介面更聚焦賽程與進度。
- 預測視窗內保留小組賽晉級 / 32 強 / 16 強 / 8 強 / 4 強 / 冠亞季軍 分頁預留。
- 賽程表欄位重組：移除原「預測」欄位，改以「狀態」欄位清楚標示每場比賽階段。

### 修正（已撤銷）
- 修正 `getTeam()` 無法正確比對英文名稱的問題（雖然資料以中文為主）。
- 修正日期字串比對邏輯，今日場次統計更穩定。

---

## [1.0.1] - 2026-06-15

### 修正
- 回滾 GUI 到 v1.0 原始樣式，恢復賽程表的「預測」欄位。
- 保留 `dashboard_v1_backup/` 作為未來任何修改前的對照基準。
- 新增回滾紀錄：`memory/2026-06-15_gui_rollback_v1.0.md`。

---

## [1.0.0] - 2026-06-15

### 新增
- 初始建立專案 `Project_FIFA_WorldCup_2026_TW`。
- 完整 104 場賽程資料（`data/matches_104.json`），以台灣時間 Asia/Taipei UTC+8 換算。
- 48 隊球隊基本資料（`data/teams.json`）：中文名稱、英文名稱、組別、FIFA 排名、種子、旗幟 emoji。
- `engine/worldcup_engine.py`：資料載入、積分計算、賽果更新、基礎預測。
- `engine/server.py`：本地 HTTP 伺服器，提供 API 與靜態檔案服務。
- `engine/telegram_notifier.py`：Telegram 開賽提醒與每日摘要。
- `dashboard/index.html` + `css/style.css` + `js/app.js`：網頁儀表板初版。
- `predictions/`：預測分析文件預留區。
- `README.md`：專案說明與使用方式。

---

## 版本號規則

採用語意化版本 [SemVer](https://semver.org/lang/zh-TW/)：

- **MAJOR**：架構或資料格式重大變更，可能破壞既有使用方式。
- **MINOR**：新增功能（例如新的視覺區塊、新的通知類型、新的篩選條件）。
- **PATCH**：問題修正、資料更新、微調樣式。