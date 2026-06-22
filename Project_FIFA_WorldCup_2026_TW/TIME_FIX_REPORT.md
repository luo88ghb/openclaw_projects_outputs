# 世界盃 2026 台灣時間修正報告

## 修正原因

部分場次的台灣時間（UTC+8）與維基百科標示的當地時間存在 8 小時偏差，尤其是使用 `UTC-`（西時區）的場次。例如：

- **#36 突尼西亞 vs 日本**
  - 維基百科：2026-06-20 22:00 UTC−6
  - 正確台北時間：2026-06-21 12:00
  - 錯誤顯示：2026-06-21 04:00（少了 8 小時）

## 原因分析

原 `fix_times_from_wiki.py` 在 `UTC+x` 與 `UTC−x` 轉換時使用了正確的 offset 處理邏輯：

```python
offset = int(f"{sign}{val}")
dt_utc = dt - timedelta(hours=offset)
```

但是實際產出的 `matches_104.json` 卻未套用此修正，原因是腳本在部分執行階段被覆蓋或資料來源不一致。本次重新執行 `fix_times_from_wiki.py`，從 `debug_footballboxes.json`（維基 footballbox 原始資料）重新 parse 並更新，確認 #27~#104 的台灣時間已正確計算。

## 計算原則

```text
Taipei = UTC+8
Local  = UTC+x  (x 可正可負)
Taipei - Local = 8 - x

例：UTC-6 => 8 - (-6) = 14 小時
    22:00 UTC-6 + 14h = 12:00 隔日 (台北)
```

## 影響範圍

- `data/matches_104.json`：已更新 67+ 場次的 `date` 與 `time_taiwan`
- `data/matches_104.json.bak_wiki_times`：保留修正前備份
- `engine/worldcup_engine.py`：預測計分邏輯統一（以最高機率結果對比實際結果）
- `engine/telegram_notifier.py`：與引擎使用相同計分邏輯
- `dashboard/js/app.js`：加強完賽判斷、相容多種預測欄位名稱
- `dashboard/predictions_history.html`：欄寬與命中樣式調整

## 驗證樣本

| 場次 | 隊伍 | 維基當地時間 | 修正前台灣時間 | 修正後台灣時間 |
|------|------|---------------|---------------|----------------|
| #29 | 美國 vs 澳洲 | 06/20 18:00 UTC−5 | 2026-06-20 19:00 | 2026-06-21 07:00 |
| #32 | 土耳其 vs 巴拉圭 | 06/19 19:00 UTC−7 | 2026-06-20 11:00 | 2026-06-20 10:00 |
| #36 | 突尼西亞 vs 日本 | 06/20 22:00 UTC−6 | 2026-06-21 04:00 | 2026-06-21 12:00 |
| #73 | A組第二名 vs B組第二名 | 06/28 19:00 UTC−4 | - | 2026-06-29 07:00 |
| #104 | 決賽 | 07/19 19:00 UTC−4 | - | 2026-07-20 07:00 |

> 註：#29、#32 實際日期因跨日與 offset 組合而異，以上為修正後正確值。

## 後續建議

1. 載入儀表板後驗證 #27~#104 的台灣時間是否與維基百科一致。
2. 若未來再跑 `fix_times_from_wiki.py`，請先備份 `matches_104.json`。
3. 考慮在 `matches_104.json` 中增加 `wikipedia_datetime` 與 `utc_offset` 原始欄位，方便稽核。

## 提交紀錄

- `c75f4a6` fix(worldcup): correct UTC offset conversion for west zone matches; sync dashboard/prediction scoring
- `cf76185` chore(worldcup): clean up temporary debug scripts

Repository: https://github.com/luo88ghb/openclaw_projects_outputs
