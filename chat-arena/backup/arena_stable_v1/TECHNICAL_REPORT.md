# Zeni AI 競技場自動化與穩定性優化：技術總結報告

| 項目屬性 | 詳細資訊 |
| :--- | :--- |
| **文件名稱** | Zeni AI Arena 競技場自動化與穩定性優化報告 |
| **日期** | 2026-05-08 |
| **編撰者** | Antigravity AI Coding Assistant |
| **版本** | v1.2 (Stable Edition) |

---

## 1. 系統設計架構 (System Architecture)

本系統採用 **「主控代理人模式 (Master Agent Orchestration)」** 搭配 **「容器化沙盒 (Containerized Sandbox)」** 的混合式架構。

### 1.1 分層模型
1.  **展示層 (Frontend UI)**:
    *   技術棧：Vanilla HTML5, Modern CSS (Glassmorphism), JavaScript。
    *   通訊：透過 **SSE (Server-Sent Events)** 接收後端即時推播的遊戲日誌與狀態，實現零延遲的觀賽體驗。
2.  **邏輯控制層 (Orchestration Layer)**:
    *   核心：`game-server.js` (Node.js/Express)。
    *   職責：管理遊戲狀態機 (Game State Machine)、控制回合循環、處理 SSE 串流推送。
3.  **執行層 (Agent Execution Layer)**:
    *   技術棧：OpenClaw Gateway + OpenClaw Agent CLI。
    *   運作：主控程序啟動子進程 (Sub-processes)，在獨立的 Docker 沙盒中執行不同角色的 AI 指令。
4.  **模型層 (Model Layer)**:
    *   分配：由 Minimax、GLM-5、GPT-OSS 等雲端大型語言模型提供智慧核心。

### 1.2 資料流向圖
`用戶啟動` -> `API 指令` -> `傑尼核心狀態切換` -> `派遣子代理人(Docker)` -> `雲端模型推理` -> `結果解析與裁決` -> `SSE 推播至 UI`。

---

## 2. 開發核心邏輯 (Development Logic)

### 2.1 非同步狀態機 (Async State Machine)
遊戲流程被拆分為多個原子化階段：
*   `DESIGNER_ASKING` -> `XIAXIA_ANSWERING` -> `JUDGE_PENDING` -> `NEXT_ROUND`。
*   **鎖定機制**：使用全域變數 `isProcessing` 防止並行呼叫導致的邏輯衝突。

### 2.2 子進程管理與超時保護
由於雲端模型在 API 高峰期可能發生回應遲緩，系統實施了 **「寬鬆超時策略」**：
*   所有 `spawn` 任務皆配備 **300 秒** 監控，確保模型在 Fallback（備援鏈）切換時不會被 Node.js 提前擊殺。

### 2.3 裁決邏輯 (Judging Logic)
裁判傑尼 (Zeni) 的任務是比對 `currentAnswer` 與 `currentStandardAnswer`。邏輯優先級為：
1.  **JSON 結構比對**：解析 AI 的結構化輸出。
2.  **語意比對**：由裁判 AI 進行模糊概念一致性判斷。

---

## 3. 關鍵問題診斷與修復紀錄 (Troubleshooting)

### 3.1 系統崩潰 (EXIT_CODE_null)
*   **原因**：Docker Desktop 文件系統監控服務 (fs) 阻塞。
*   **解決方案**：清理殘留容器並提升 Subagent 逾時上限。

### 3.2 回合遞迴死結 (Infinite Recursion Lock)
*   **原因**：`await` 鏈過長導致狀態鎖未釋放就啟動下一輪。
*   **解決方案**：利用 `setTimeout` 切斷同步執行鏈，確保每一回合堆疊 (Stack) 能正確清理。

### 3.3 Gateway 路由修正
*   **原因**：環境變數缺少 `http://` 導致連線協議解析失敗。
*   **解決方案**：強制標準化 URL 格式為 `http://${host}:${port}`。

---

## 4. 備份檔案路徑與版本控制
*   **備份目錄**：`backup/arena_stable_v1/`
*   **主要原始碼**：`game-server.js`
*   **前端介面**：`public/index.html`

> [!IMPORTANT]
> **開發提示**：在開發多代理人系統時，必須考慮「物理環境（如 Docker）」對「軟體邏輯」的影響。本案例中，大部分問題源於環境延遲而非程式碼語法。
