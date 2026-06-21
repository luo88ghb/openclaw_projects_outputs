# ChangeLog - 2026-06-21 世足儀表板修正

## 修正項目

1. 過場更新機制（scheduler.py / wiki_scraper.py）
   - 增加 robust 重試與 backfill 邏輯，確保網路斷線或資料源不穩定時，已完成開賽時間的場次會被重新抓取。
   - `scrape_checked` 只在成功取得比分後才標記，避免誤判為已檢查而跳過補抓。

2. 預測命中邏輯（worldcup_engine.py / telegram_notifier.py）
   - 統一採用「預測機率最高之結果（主勝/和局/客勝）對比實際結果」為計分標準。
   - 移除比分精準命中才能得分的複雜規則，簡化為方向正確即 +1、錯誤即 -1。
   - 已重新校正 #34/#35/#36 等近場資料，#36 日本客勝現在顯示命中。

3. 儀表板 UX（dashboard/index.html / dashboard/js/app.js / dashboard/css/additions.css）
   - 「完整賽程」標題旁新增「⬇️ 跳到最近賽局」按鈕，點擊後自動平滑捲動並高亮當前/下一場/最近結束場次。
   - app.js 底部補回遺失的 `setupSSE(); loadData();` 啟動呼叫，修復頁面空白問題。

## 已驗證

- `node --check dashboard/js/app.js` 通過語法檢查。
- #34 德國 2-1 象牙海岸：hit=True
- #35 厄瓜多 0-0 庫拉索：hit=False
- #36 突尼西亞 0-2 日本：hit=True（預測客勝 48%）
