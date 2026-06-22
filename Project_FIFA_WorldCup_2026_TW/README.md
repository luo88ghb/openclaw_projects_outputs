<!-- 下載時間: 2026-06-22 16:45:18 Asia/Taipei | 版本: v2.2.7 -->
# Project_FIFA_WorldCup_2026_TW

2026 FIFA 世界盃足球賽 台灣時間賽程儀表板與預測分析系統。

**版本**: v2.2.7  
**更新日期**: 2026-06-22

---

## 目標

- 提供以 **台灣時間（Asia/Taipei, UTC+8）** 為基準的完整 104 場賽程。
- 建立本機網頁儀表板，可查詢賽程、分組積分、即將開賽資訊。
- 透過 **Telegram** 發送比賽前通知。
- 賽前提供基礎預測，賽後根據比賽結果滾動修正預測。

---

## 專案結構

```
Project_FIFA_WorldCup_2026_TW/
├── data/
│   ├── matches_104.json    # 完整 104 場賽程
│   └── teams.json          # 48 隊基本資料
├── dashboard/
│   ├── index.html          # 儀表板主頁
│   ├── css/style.css       # 深色主題樣式
│   └── js/app.js           # 前端互動邏輯
├── engine/
│   ├── worldcup_engine.py # 資料維護、積分計算、預測比對
│   ├── server.py          # 本地 HTTP 伺服器
│   └── telegram_notifier.py # Telegram 通知
├── predictions/           # 預測分析文件
├── memory/                # 開發錨點與記錄
├── start_server.bat       # Windows 快速啟動腳本
├── .env.example           # Telegram 環境變數範例
├── CHANGELOG.md           # 版本迭代記錄
├── Technical_Report.md    # 技術文件
└── README.md              # 本文件
```

---

## 使用方式

### 1. 啟動儀表板

```powershell
cd C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW
python engine/server.py
```

開啟瀏覽器：

```text
http://localhost:8765/index.html
```

或直接雙擊 `start_server.bat`。

### 2. 儀表板功能

#### 頂部 Hero

- **下一場開賽**：顯示最近的未賽場次，包含對戰隊伍、開賽時間與城市。
- **進階預測**：顯示小組賽晉級 / 32 強 / 16 強 / 8 強 / 4 強 / 冠亞季軍 預測分頁。

#### 篩選區

- 搜尋球隊、城市、組別或階段。
- 依「階段」、「組別」篩選。

#### 完整賽程表

- 顯示場次、日期、時間、階段、組別、主隊、比分、客隊、城市、預測。
- 進行中場次有紅色脈動動畫。
- 已結束場次以灰階顯示。

#### 分組積分

- 12 組卡片並排。
- 每組顯示排名、球隊、賽、勝、和、負、進球、積分。

### 3. 設定 Telegram 通知

設定環境變數：

```powershell
$env:TELEGRAM_BOT_TOKEN="你的 Bot Token"
$env:TELEGRAM_CHAT_ID="你的 Chat ID"
```

手動測試通知：

```powershell
python engine/telegram_notifier.py
```

Cron job 已設定：
- **開賽提醒**：每小時第 0 分檢查接下來 30 分鐘內開賽的比賽，有則發送 Telegram 通知。
- **每日摘要**：每天 08:00 發送當日重點賽事與預測。

### 4. 更新比賽成績

```python
from engine.worldcup_engine import WorldCupEngine
engine = WorldCupEngine()
engine.update_score(match_id=1, home_score=2, away_score=1)
```

更新後儀表板會自動顯示新的比分與積分（網頁每 60 秒自動重新整理）。

### 5. 設定預測

```python
engine.set_prediction(match_id=1, home_pred=2, away_pred=1, reason="主場優勢")
engine.check_prediction(match_id=1)
```

---

## 資料來源

- FIFA 官方 2026 世界盃賽程，換算為台灣時間。
- 台灣轉播：愛爾達 ELTA.tv（轉播總代理）、中華電信 Hami Video（授權轉播）。

---

## 版本紀錄

詳見 `CHANGELOG.md`。

- **v2.0.2** (2026-06-16)：依據維基百科修正 Match 4 / Match 13 比分；隊名「波士尼亞」改為「波赫」；新增 `flag_img` 國旗圖片欄位；前端國旗顯示優先使用維基百科 PNG 圖片。
- **v2.0.1** (2026-06-16)：移除附加賽勝者佔位符，替換為 6 支晉級真實球隊（含波士尼亞 → 波赫後續更名）。
- **v2.0.0** (2026-06-16)：同步 FIFA 官方已結束賽果（Match 15、16 修正主客/比分），儀表板新增版本號與最後更新時間標示。
- **v1.0.1** (2026-06-15)：回滾 GUI 到 v1.0 原始樣式，恢復「預測」欄位。
- **v1.0.0** (2026-06-15)：初始專案建立，含 104 場賽程、引擎與儀表板初版。

---

## 待辦

- [ ] 自動從網路更新即時比分。
- [ ] 賽後滾動預測模型強化。
- [ ] Telegram cron 排程通知自動部署。
- [ ] 更多球隊數據與預測分析。
- [ ] 多語系支援。
