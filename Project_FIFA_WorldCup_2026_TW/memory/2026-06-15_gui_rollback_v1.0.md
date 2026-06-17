# GUI v1.0 Rollback 紀錄

**日期**: 2026-06-15 (Asia/Taipei)
**操作**: 從 `dashboard_v1_backup/` 還原原始儀表板樣式
**原因**: 羅哥反映 v1.1 修改後的界面被改壞，尤其是「預測」欄位被換成「狀態」欄位不符合需求。

## 還原範圍
- `dashboard/index.html` ← `dashboard_v1_backup/index.html`
- `dashboard/js/app.js` ← `dashboard_v1_backup/js/app.js`
- `dashboard/css/style.css` ← `dashboard_v1_backup/css/style.css`

## 驗證
- 以 SHA256 比對三個檔案與備份一致 ✅
- 賽程表欄位恢復為：場次 / 日期 / 台灣時間 / 階段 / 組別 / 主隊 / 比分 / 客隊 / 城市 / 預測 ✅
- 資料檔案 `teams.json` 與 `matches_104.json` 未被覆蓋，保持完整 ✅

## 後續
- 原始 v1.0 樣式保留，作為羅哥認可的基準版本。
- 預測功能仍維持在「進階預測」卡片內，賽程表僅顯示基礎預測欄位（尚未填入資料時顯示 `-`）。
