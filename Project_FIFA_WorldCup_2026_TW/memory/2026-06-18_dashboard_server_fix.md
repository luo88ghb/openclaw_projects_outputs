# 2026-06-18 Dashboard 伺服器修復紀錄

**時間**: 台北 2026-06-18 06:25 GMT+8

## 問題現象
羅哥反應儀表板「開」和「關」都不順，網頁開得起來但資料載不進來。

## 根因
`engine/server.py` 使用 `socketserver.TCPServer`（單執行緒）。
當瀏覽器建立 `/update-stream` SSE 長連線後，靜態檔案與 `/data/matches_104.json` 等後續請求會被卡住，導致頁面空白或資料無法載入。

## 修正內容
1. **server.py**
   - 改用 `socketserver.ThreadingTCPServer`，每個 HTTP 請求獨立執行緒，避免 SSE 阻塞資料載入。
   - 新增 `/api/status`：回傳運行狀態、版本號、PID。
   - 新增 `/api/shutdown`（POST）：可遠端關閉儀表板伺服器。

2. **批次檔（開關體驗）**
   - `start_dashboard.bat`：雙擊啟動儀表板伺服器，自動開瀏覽器前準備。
   - `stop_dashboard.bat`：雙擊關閉，先嘗試 `/api/shutdown` 優雅關閉，再強制清理 port 8765 與 scheduler.py。
   - `start_all.bat`：更新為一鍵啟動「伺服器 + 排程器」。

## 驗證
啟動後實測：
- `http://localhost:8765/api/status` → 正常 JSON 回應。
- `http://localhost:8765/data/matches_104.json` → 正常載入。
- `http://localhost:8765/data/teams.json` → 正常載入。
- 多次 `start_dashboard.bat` / `stop_dashboard.bat` 可正常開關。

## 後續注意
- 若 port 8765 仍被佔用，stop 腳本會自動清理。
- 建議羅哥使用 `start_dashboard.bat` 與 `stop_dashboard.bat` 操作，不要再直接對 `server.py` 下命令。
