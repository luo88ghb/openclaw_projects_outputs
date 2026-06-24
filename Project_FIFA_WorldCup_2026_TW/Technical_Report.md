<!-- 下載時間: 2026-06-23 03:19:30 Asia/Taipei | 版本: v2.2.7 -->
# 2026 世界盃足球賽 台灣時間儀表板 — 技術文件

**版本**: v2.2.7  
**日期**: 2026-06-22  
**作者**: Zeni (OpenClaw Agent)  
**專案路徑**: `C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW`

---

## 1. 專案目標

為 2026 FIFA 世界盃足球賽建立一套以 **台灣時間（Asia/Taipei, UTC+8）** 為基準的資訊系統，核心目標：

1. 提供完整 104 場賽程的網頁儀表板。
2. 清楚呈現賽事進度（未開賽 / 進行中 / 已結束）。
3. 顯示分組積分與晉級情況。
4. 透過 Telegram 發送比賽前通知與每日摘要。
5. 預留賽前預測與賽後覆盤的擴充入口。
6. 儀表板 header 顯示版本號與最後更新時間，作為更新認證。

---

## 2. 系統架構

```text
Project_FIFA_WorldCup_2026_TW/
├── data/
│   ├── matches_104.json    # 104 場賽程資料
│   └── teams.json          # 48 支球隊資料
├── engine/
│   ├── worldcup_engine.py # 核心引擎：資料、積分、預測
│   ├── server.py          # 本地 HTTP 伺服器
│   └── telegram_notifier.py # Telegram 通知
├── dashboard/
│   ├── index.html         # 儀表板頁面
│   ├── css/style.css      # 樣式表
│   └── js/app.js          # 前端互動邏輯
├── predictions/           # 預測分析文件（預留）
├── memory/                # 開發錨點與記錄
├── README.md              # 使用者手冊
├── CHANGELOG.md           # 版本迭代記錄
└── Technical_Report.md    # 本文件
```

---

## 3. 資料格式

### 3.1 賽程資料 `matches_104.json`

每場比賽欄位：

| 欄位 | 說明 |
|------|------|
| `match_id` | 場次編號 1 ~ 104 |
| `date` | 台灣日期，格式 `YYYY-MM-DD` |
| `time_taiwan` | 台灣開賽時間，格式 `HH:MM` |
| `stage` | 賽事階段：小組賽 / 32強 / 16強 / 8強 / 4強 / 季軍戰 / 決賽 |
| `group` | 小組賽組別 A~L，淘汰賽為 `null` |
| `home_team` | 主隊中文名稱 |
| `away_team` | 客隊中文名稱 |
| `city` | 舉辦城市 |
| `home_score` | 主隊得分，`null` 表示未賽 |
| `away_score` | 客隊得分，`null` 表示未賽 |
| `status` | `scheduled` / `live` / `finished` |
| `prediction` | 預測物件（預留） |

### 3.2 球隊資料 `teams.json`

| 欄位 | 說明 |
|------|------|
| `id` | FIFA 國家代碼 |
| `name_zh` | 中文名稱 |
| `name_en` | 英文名稱 |
| `confederation` | 所屬洲際足聯 |
| `group` | 組別 |
| `fifa_ranking` | FIFA 世界排名（2026 年預估值） |
| `pot` | 種子檔次 |
| `flag` | 國旗 emoji |
| `flag_img` | 國旗圖片路徑（優先於 emoji 顯示） |

---

## 4. 前端 GUI 規格

### 4.1 設計原則

- **深色主題**：符合長時間觀看賽事的需求，減少眼部疲勞。
- **資訊層級**：頂部 Hero 顯示最重要資訊，下方依序為篩選區、賽程表、積分榜。
- **響應式**：手機下表格可橫向捲動，積分榜卡片自動換行。
- **狀態清楚**：未開賽 / 進行中 / 已結束 用顏色與動畫區分。

### 4.2 頂部 Hero

| 卡片 | 內容 |
|------|------|
| 下一場開賽 | 場次、階段、對戰隊伍、開賽時間、城市 |
| 進階預測 | 各階段預測分頁：小組賽晉級 / 32強 / 16強 / 8強 / 4強 / 冠亞季軍 |

### 4.3 篩選區

- 搜尋框：球隊、城市、組別、階段關鍵字。
- 階段下拉：全部 / 小組賽 / 32 強 / 16 強 / 8 強 / 4 強 / 季軍戰 / 決賽。
- 組別下拉：A~L。
- 重設按鈕。

### 4.4 賽程表

欄位：場次 / 日期 / 時間 / 階段 / 組別 / 主隊 / 比分 / 客隊 / 城市 / 預測。

狀態樣式：

| 狀態 | 樣式 |
|------|------|
| 未開賽 | 正常顯示 |
| 進行中 | 紅色脈動動畫 |
| 已結束 | 整列灰階，比分淡化 |

### 4.5 分組積分

- 12 組卡片並排。
- 每組顯示：排名、球隊、賽、勝、和、負、進球、積分。

---

## 5. 後端引擎

### 5.1 `worldcup_engine.py`

核心類別 `WorldCupEngine` 提供：

- `load_json()` / `save_json()`：資料讀寫。
- `update_score(match_id, home_score, away_score)`：更新賽果並觸發預測資料庫更新。
- `group_standings(group)`：計算單組積分榜。
- `predict_match(match_id)`：基於 FIFA 排名、隊伍向量、主場優勢產生基礎預測。
- `set_prediction(match_id, ...)`：設定單場預測。
- `check_prediction(match_id)`：檢查預測是否命中。
- `generate_stage_predictions(stage)`：產生各階段預測。
- `upcoming_matches(hours)`：查詢接下來 N 小時內的比賽。
- `auto_predictions_for_upcoming(hours)`：自動為即將比賽產生預測。

### 5.2 `server.py`

本地 HTTP 伺服器，預設連接埠 `8765`（靜態）與 `8766`（API）。

提供端點：

| 端點 | 說明 |
|------|------|
| `GET /` | 儀表板首頁 |
| `GET /data/matches_104.json` | 賽程資料 |
| `GET /data/teams.json` | 球隊資料 |
| `GET /api/predictions/{stage}` | 各階段預測結果 |
| `POST /api/update_score` | 更新比賽成績 |

### 5.3 `telegram_notifier.py`

發送：
- 開賽提醒：比賽前 30 分鐘通知。
- 每日摘要：每日 08:00 發送當日重點賽事。

---

## 6. 預測模型

### 6.1 基礎預測（已實作）

- 輸入：FIFA 排名、隊伍滾動向量（attack/defense/form/overall）、主場優勢。
- 輸出：預測比分與勝/和/負機率。
- 賽後自動更新隊伍向量。

### 6.2 預測模型的智慧等級

| 等級 | 名稱 | 特徵 | 狀態 |
|:---:|---|---|---|
| **L1** | **規則式啟發（Rule-based Heuristic）** | FIFA 排名越高勝率越高，線性映射成百分比 | ✅ 目前運行中 |
| L2 | 統計基線模型 | Elo 積分 + 歷史勝率 | 規劃引入 |
| L3 | 機器學習模型 | 多特徵迴歸 / 分類，含近期狀態、傷兵、對戰 | 未來擴充 |
| L4 | 混合模型 | Elo + 近期狀態 + 盤口/賠率水位 | 未來擴充 |
| L5 | 進階模型 | xG、戰術模擬、即時賽事情報 | 長期願景 |

### 6.3 L1 模型限制

- 僅以 **FIFA 排名**作為主要實力指標，未反映即時狀態。
- 未考慮：近期比賽狀態、傷兵、對戰歷史、主場優勢、賽制壓力、戰術風格相克、天氣/時差、xG（預期進球）。
- 對於實力接近的隊伍（例如 FIFA 排名差異 10 名以內）區分度不足。

### 6.4 改進與創新推演架構

建議採用分層資料 → 特徵 → 模型 → 輸出的四層架構：

```text
1. 資料層
   ├── 國家隊 Elo 評分（eloratings.net）
   ├── FIFA 排名與近期比賽結果
   ├── 盤口/賠率數據（市場智慧）
   └── 賽事情報（傷兵、主場、天氣）

2. 特徵層
   ├── 實力差 = Elo 差 → 勝率映射
   ├── 狀態動量（近 5 場得失球、xG 趨勢）
   ├── 主場/中立場加權
   ├── 淘汰賽壓力因子
   └── 對戰風格相克係數

3. 模型層
   ├── 基線：Bradley-Terry / Elo 機率
   ├── 進階：泊松迴歸預測比分
   └── 可選：Gradient Boosting / 神經網路

4. 輸出層
   ├── 勝/和/負機率
   ├── 最可能比分
   ├── 信心區間
   └── 預測覆盤與校正
```

### 6.5 產品路線圖

1. **保留 L1 運行**：目前 FIFA 排名啟發模型繼續作為預設模型。
2. **引入 L2 Elo 模型**：從 eloratings.net 抓取各國 Elo 評分，建立 Elo 機率映射，並與 L1 並行運作。
3. **儀表板模型切換**：在 Hero 區的「進階預測」卡片中加入模型選擇器（L1 / L2），讓用戶切換比較。
4. **賽後覆盤迴路**：每場結束後記錄「預測 vs 實際」結果，計算命中率與校正誤差，並在 `predictions_history.html` 中標示各模型表現。
5. **逐步往 L3/L4 演進**：累積本屆賽事資料後，可用機器學習進行特徵加權與校正。

### 6.6 各階段預測

前端已預留分頁：小組賽晉級 / 32 強 / 16 強 / 8 強 / 4 強 / 冠亞季軍。

---

## 7. 部署與執行

### 7.1 啟動儀表板

```powershell
cd C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW
python engine/server.py
```

瀏覽器開啟：

```text
http://localhost:8765/index.html
```

### 7.2 設定 Telegram

```powershell
$env:TELEGRAM_BOT_TOKEN="你的 Bot Token"
$env:TELEGRAM_CHAT_ID="你的 Chat ID"
python engine/telegram_notifier.py
```

---

## 8. 版本紀錄

詳見 `CHANGELOG.md`。

- v2.1.1 (2026-06-17)：補齊庫拉索 (CUW) 的 `flag_img` 欄位；同步 `dashboard/index.html` 版本號與最後更新時間為 v2.1.1 / 2026-06-17 22:05。
- v2.1.0 (2026-06-17)：新增時間校正排程器 `engine/scheduler.py`、維基百科比分抓取 `engine/wiki_scraper.py`、SSE 主動推送 `/update-stream`、Telegram 賽後通知、一鍵啟動腳本 `start_all.bat`；還原並強化「預測（賽前基礎版）」欄位。
- v2.0.2 (2026-06-16)：依據維基百科修正 Match 4 / Match 13 比分；隊名「波士尼亞」改為「波赫」；新增 `flag_img` 國旗圖片欄位；前端國旗顯示優先使用維基百科 PNG 圖片。
- v2.0.1 (2026-06-16)：移除附加賽勝者佔位符，替換為 6 支真實附加賽晉級隊伍。
- v2.0.0 (2026-06-16)：同步 FIFA 官方已結束賽果（Match 15、16 修正主客/比分），儀表板新增版本號與最後更新時間標示。
- v1.0.1 (2026-06-15)：回滾 GUI 到 v1.0 原始樣式，恢復「預測」欄位。
- v1.0.0 (2026-06-15)：初始專案建立，含 104 場賽程、引擎、儀表板初版。

---

## 9. 未來擴充

- [x] 預測模型分級（L1 ~ L5）與技術路線圖。
- [ ] 引入 L2 Elo 評分模型並在儀表板提供模型切換。
- [ ] 自動即時比分更新（外部 API 或爬蟲）。
- [ ] 更強大的預測模型與可視化。
- [ ] Telegram cron 排程通知自動化。
- [ ] 球員數據、傷兵、天氣等資訊整合。
- [ ] 多語系支援（繁體中文 / 英文）。

---

## 10. 資料來源與外部依賴

- 賽程資料：維基百科 `2026 FIFA World Cup` 頁面（校正後轉為台灣時間）。
- 隊伍資料：內建 `data/teams.json`。
- 預設預測模型：內建 L1 FIFA 排名啟發模型。
- **未來 Elo 資料**：計劃從 `eloratings.net` 抓取各國家隊 Elo 評分。
