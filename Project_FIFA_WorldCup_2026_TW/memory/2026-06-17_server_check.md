# 2026-06-17 儀表板伺服器檢查紀錄

**時間**: 2026-06-17 12:05 GMT+8（台北時間）／比賽現場時間 2026-06-16 22:05  
**台北時間**: 2026-06-17 12:05  
**專案**: Project_FIFA_WorldCup_2026_TW  
**執行**: 啟動 `start_all.bat` 並驗證儀表板資料

---

## 檢查結果

| 項目 | 期望結果 | 實際結果 | 狀態 |
|---|---|---|---|
| 伺服器啟動 | localhost:8765 可連線 | 進程 ID 30328 監聽 0.0.0.0:8765 | OK |
| 總場次數 | 104 場 | 104 場 | OK |
| Match 4 比分 | 美國 4-1 巴拉圭 | 美國 4-1 巴拉圭 | OK |
| Match 13 比分 | 西班牙 0-0 維德角 | 西班牙 0-0 維德角 | OK |
| 國旗圖片欄位 | 48 隊都有 `flag_img` | 48 / 48 | OK |
| CUW (庫拉索) | 補上 `flags/Flag_of_Curacao.png` | 已補上 | OK |
| 前端版本號 | v2.1.1 / 2026-06-17 12:05 | 已更新 | OK |

---

## 發現與處理

1. **庫拉索 (CUW) 缺少 `flag_img`**：在 `data/teams.json` 中唯一缺少圖片路徑的球隊，已補上 `flags/Flag_of_Curacao.png`。
2. **版本號未同步**：`dashboard/index.html` 顯示 `v2.1.0 / 2026-06-17 10:36`，已更新為 `v2.1.1 / 2026-06-17 12:05`（台北時間）。

---

## 下一步

- 請羅哥開啟 http://localhost:8765/index.html 並按 **Ctrl+F5** 強制重新整理。
- 確認所有 48 支球隊皆顯示國旗圖片。
- 版本號顯示應為 **v2.1.1 / 2026-06-17 12:05**（台北時間 12:05）。
- 確認庫拉索 (CUW) 的國旗圖片 `flags/Flag_of_Curacao.png` 正確顯示。

---

## Git 提交

- Commit: `cb0fcd0 (HEAD -> main)`  
- 訊息: `fix: v2.1.1 補齊庫拉索 flag_img 並同步前端版本號與文件`

## 追加修正與提交（2026-06-17 12:30 台北時間）

### 問題
- `engine/wiki_scraper.py` 的 `_extract_all_scores()` 原先接收純文字後再跑 `BeautifulSoup(text, "html.parser")`，導致 table parse 在純文字上無法運作，只剩 regex 路徑；
- 僅能抓到少數帶有完整日期時間的比賽，很多已完成場次（例如 美國 4-1 巴拉圭、墨西哥 2-0 南非）抓不到比分。

### 修正
- `_extract_all_scores()` 改為接受 HTML 或純文字，若是 HTML 先經 `_wiki_text()` 轉為文字，再同時進行 regex 與 `itemprop="name"` table parse。
- `parse_match_score()` 改為直接將原始 HTML 傳入 `_extract_all_scores(html)`，讓兩種解析都能運作。
- 移除前端 `app.js` 中對 `http://localhost:8766/api/predictions/...` 的無用抓取，避免隱性錯誤。

### 驗證
- `python engine/wiki_scraper.py` 測試輸出：
  - 美國 vs 巴拉圭 => `home_score: 4, away_score: 1`
  - 墨西哥 vs 南非 => `home_score: 2, away_score: 0`
  - 德國 vs 庫拉索 => `home_score: 7, away_score: 1`
  - 西班牙 vs 維德角 => `home_score: 0, away_score: 0`
- 全部皆正確對應維基百科賽果。

### 影響
- `scheduler.py` 在比賽開賽 +120 分鐘後抓取維基百科時，現在能正確辨識絕大多數已完成場次的比分，不再漏抓。
- 前端不會再因為連不到 `localhost:8766` 而拋出隱性錯誤。

### Git 提交

- Commit: `2644c1b`
- 訊息: `fix(wiki_scraper): parse HTML directly so table-extraction works; verify 4 finished matches`
