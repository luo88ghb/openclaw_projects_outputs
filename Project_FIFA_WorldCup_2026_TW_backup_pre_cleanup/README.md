# Project_FIFA_WorldCup_2026_TW

2026 FIFA 世界盃足球賽 台灣時間賽程儀表板與預測分析系統。

## 目標

- 提供以 **台灣時間（Asia/Taipei, UTC+8）** 為基準的完整 104 場賽程。
- 建立本機網頁儀表板，可查詢賽程、分組積分、即將開賽資訊。
- 透過 **Telegram** 發送比賽前通知。
- 賽前提供基礎預測，賽後根據比賽結果滾動修正預測。

## 專案結構

```
Project_FIFA_WorldCup_2026_TW/
├── data/
│   ├── matches_104.json    # 完整 104 場賽程
│   └── teams.json          # 48 隊基本資料
├── dashboard/
│   ├── index.html          # 儀表板主頁
│   ├── css/style.css       # 樣式
│   └── js/app.js           # 前端互動邏輯
├── engine/
│   ├── worldcup_engine.py # 資料維護、積分計算、預測比對
│   ├── server.py          # 本地 HTTP server
│   └── telegram_notifier.py # Telegram 通知
├── predictions/
│   ├── analysis.md         # 預測與分析文件
│   ├── prediction_model.md # 預測模型邏輯
│   ├── post_match_review.md # 賽後覆盤與命中率
│   └── daily_briefing.md   # 每日賽事摘要
├── start_server.bat       # Windows 快速啟動腳本
├── .env.example           # Telegram 環境變數範例
└── README.md
```

## 使用方式

### 1. 啟動儀表板

```powershell
cd C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW
python engine/server.py
```

開啟瀏覽器：
```
http://localhost:8765/index.html
```

或直接雙擊 `start_server.bat`。

### 2. 設定 Telegram 通知

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

### 3. 更新比賽成績

```python
from engine.worldcup_engine import WorldCupEngine
engine = WorldCupEngine()
engine.update_score(match_id=1, home_score=2, away_score=1)
```

### 4. 設定預測

```python
engine.set_prediction(match_id=1, home_pred=2, away_pred=1, reason="主場優勢")
engine.check_prediction(match_id=1)
```

## 資料來源

- FIFA 官方 2026 世界盃賽程，換算為台灣時間。
- 台灣轉播：愛爾達 ELTA.tv（轉播總代理）、中華電信 Hami Video（授權轉播）。

## 待辦

- [ ] 自動從網路更新即時比分
- [ ] 賽後滾動預測模型
- [ ] Telegram cron 排程通知
- [ ] 更多球隊數據與預測分析
