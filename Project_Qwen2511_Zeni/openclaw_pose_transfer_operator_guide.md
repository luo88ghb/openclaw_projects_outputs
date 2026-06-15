# OpenClaw 執行說明文件：人物對人物姿勢遷移專案操作規格

## 文件目的

本文件的目的，是讓 OpenClaw 能夠讀取並依照文件內容，實際執行「人物對人物姿勢遷移專案」的動手任務，而不是只停留在討論層。OpenClaw 的代理架構通常由身份檔、技能層、工具層與工作區構成；其中身份檔定義角色與行為邊界，Skills 定義方法論，Tools 提供可操作能力，而 SubAgent 適合承接主代理拆出的具體子任務。[cite:18][cite:20][cite:21][cite:22]

此文件假設專案只處理「人物對人物」姿勢遷移，不處理跨物種任務，因此所有流程都以人體姿勢條件、人物身份一致性與 ComfyUI 本地工作流為中心。這樣的任務邊界有助於降低風險，因為 Pose ControlNet 主要對應人體姿勢控制，而 IP-Adapter FaceID 也主要用於人物臉部身份維持。[cite:1][cite:15]

## OpenClaw 應如何讀取本文件

OpenClaw 應將本文件視為專案操作憲章，而不是一般說明文字。根據公開教學與實務說明，OpenClaw 代理通常透過 `SOUL.md` 或 `agent.md` 這類身份文件定義角色，再結合已允許的 skills、tools 與 workspace 來執行任務，因此本文件最適合放入代理工作區的操作規範檔，並在主代理的身份檔中引用。[cite:18][cite:24][cite:27][cite:31]

建議的讀取方式如下：

1. 在主代理工作區建立本文件，檔名可為 `POSE_TRANSFER_OPERATOR_GUIDE.md`。
2. 在主代理的 `SOUL.md` 或 `agent.md` 中明確寫入：「執行人物姿勢遷移任務時，必須先遵循 `POSE_TRANSFER_OPERATOR_GUIDE.md` 的分工、工具與交付規則」。[cite:18][cite:27][cite:31]
3. 將本文件視為高優先規範；若使用者要求與本文件衝突，先回報衝突點，再請求確認。
4. 所有任務完成標準，以本文件定義的輸出物為準，而不是只輸出文字回覆。

## 專案任務定義

### 任務目標

OpenClaw 的任務不是「生成任意好看的圖」，而是產出一個可重複執行的本地流程：給定人物 A 的姿勢來源圖與人物 B 的身份來源圖，在 ComfyUI 中生成「人物 B 做出人物 A 姿勢」的結果，並且留下可重現的節點設定、模型依賴、參數紀錄與故障排除路徑。[cite:1][cite:15]

### 任務交付物

每次正式執行，至少應交付以下產物：

- ComfyUI 工作流 JSON。
- 模型與節點安裝清單。
- 輸入資料夾結構與命名規則。
- 一組可執行的 prompt / negative prompt / 參數紀錄。
- 至少一批測試輸出圖與對應 seed。
- 問題紀錄與修復說明。

這些交付物之所以必要，是因為姿勢遷移專案若缺乏工作流、參數與輸出對照記錄，後續很難重現成功結果，也無法讓代理真正承接工程型任務。[cite:22][cite:31]

## 建議代理架構

公開資料指出，OpenClaw 在多代理協作時，若需求是由主代理拆任務、子代理獨立完成並回傳結果，SubAgent 是對應的標準模式；而多代理應建立清楚的隔離邊界、專屬 workspace 與工具權限。[cite:21][cite:23][cite:24][cite:26]

因此，此專案建議使用「1 個主代理 + 3 個 SubAgent」的結構，而不是一開始就建立太多常駐代理，因為公開實務也建議先從單一主代理與必要的子代理開始，只有在確定需要隔離時才擴充。[cite:23][cite:24]

### 主代理：pose-transfer-orchestrator

主代理負責理解使用者需求、檢查輸入完整性、委派子任務、整合結果與做最終驗收。它不應自己包辦所有細節，而應維持任務狀態、決定何時需要文件更新、何時需要重跑生成流程，以及何時判定結果尚未達標。[cite:18][cite:21]

### SubAgent 1：workflow-designer

此子代理專門處理 ComfyUI 工作流設計，包括節點拓樸、模型掛載位置、ControlNet 與 IP-Adapter 串接方式、兩階段生成與局部修補節點插入點。它的責任是產出可運行的流程規格與 JSON 工作流草案，而不是負責圖像審美評分。[cite:1][cite:21]

### SubAgent 2：dataset-prep-agent

此子代理負責輸入圖像檢查、資料夾結構建立、檔名標準化、人物圖像品質篩選與前處理說明。它的重點是降低垃圾輸入導致的生成失敗率，因為人物姿勢控制非常依賴可用的姿勢來源圖與清晰的人臉／主體參考圖。[cite:1][cite:15]

### SubAgent 3：run-and-evaluate-agent

此子代理負責實際執行生成任務、保存參數、整理輸出、記錄失敗案例與回填驗證表。它需要能操作本地檔案與命令列，必要時啟動 ComfyUI、移動檔案、保存版本，並依驗收規則標記結果是成功、待修復或失敗。[cite:22][cite:31]

## Skills 規格

OpenClaw 的 Skills 本質上是帶有 YAML frontmatter 與操作說明的 `SKILL.md`，屬於「如何把工具組合成完成任務的方法手冊」；因此本專案不應只開工具，還應建立明確的專案技能集。[cite:20][cite:22]

建議 Skills 分為「必要 Skills」與「專案自訂 Skills」。

### 必要 Skills

| Skill 名稱 | 作用 | 給哪個代理用 |
|---|---|---|
| filesystem-ops | 讀寫專案檔案、建立資料夾、整理輸出 | 全代理 |
| shell-execution | 啟動 ComfyUI、安裝節點、執行批次指令 | 主代理、run-and-evaluate-agent |
| web-research | 查詢模型、節點、相依套件說明 | 主代理、workflow-designer |
| markdown-docs | 產出 SOP、安裝文件、故障排除文件 | 主代理、workflow-designer |
| image-review | 依檢核表檢查輸出圖是否達標 | run-and-evaluate-agent |

### 專案自訂 Skills

#### 1. comfyui-pose-transfer

這是本專案的核心 Skill，內容應包含：

- 何時使用 OpenPose ControlNet。
- 何時啟用 IP-Adapter FaceID。
- 兩階段生成的標準順序。
- 何時進入局部重繪。
- 如何輸出 workflow JSON、prompt 與參數紀錄。

此 Skill 應明確要求：若任務是人物對人物，先使用人體姿勢遷移標準流程，不得任意改成風格化或跨物種流程。[cite:1][cite:15]

#### 2. comfyui-install-audit

此 Skill 用於檢查本地環境是否已具備必要模型與節點，至少應包含：

- ComfyUI 主程式是否可啟動。
- OpenPose 對應 ControlNet 模型是否存在。
- IP-Adapter FaceID 相關模型是否齊全。
- VAE、checkpoint、custom nodes 是否放在正確路徑。

#### 3. pose-transfer-qc

此 Skill 用於品質驗收，需定義：

- 姿勢對齊是否達標。
- 臉部相似是否達標。
- 是否有手部、肢體、肩頸、腳步錯位。
- 是否需要進入第二輪重繪。
- 何時可以標記為可交付結果。

## Tools 規格

公開說明指出，Tools 是 OpenClaw 是否「做得到事」的能力層，例如檔案讀寫、命令執行、網頁搜尋與網頁抓取；沒有工具，再好的 Skills 也只會停留在紙上。[cite:22][cite:30]

本專案的主代理與子代理至少應啟用以下工具：

| Tool | 用途 | 必要性 |
|---|---|---|
| read | 讀取專案文件、workflow、設定檔 | 必要 [cite:22] |
| write | 寫入 SOP、JSON、參數表、日誌 | 必要 [cite:22] |
| exec | 啟動 ComfyUI、執行安裝與批次流程 | 必要 [cite:22] |
| web_search | 查詢模型與節點相依資訊 | 建議 [cite:22] |
| web_fetch | 讀取官方文件或模型卡內容 | 建議 [cite:22] |
| browser | 若需互動式檢查 Web UI 可啟用 | 選用 [cite:22] |
| image input / review 類工具 | 檢查輸出圖內容與錯誤型態 | 強烈建議 |

### 工具權限原則

根據多代理最佳實務，應使用每個代理自己的工具許可與 deny list，尤其對公開面向或低信任代理更應限制風險；此外，多代理工作區應隔離，不應共用同一工作目錄。[cite:24][cite:26]

因此，本專案建議：

- 主代理：可使用 read、write、web_search、web_fetch、subagent delegate。
- workflow-designer：可使用 read、write、web_search、web_fetch。
- dataset-prep-agent：可使用 read、write、exec，但不得任意對外抓取不明腳本。
- run-and-evaluate-agent：可使用 read、write、exec、image review，但不負責修改主規格文件。

## SubAgent 委派規則

公開教學指出，SubAgent 的典型流程是主代理呼叫委派函式，傳入任務描述、所需技能與上下文，再讓子代理在獨立 context 中執行並回傳結果。[cite:21]

本專案應固定使用下列委派模板。

### 委派模板 A：建立工作流

- 委派對象：workflow-designer
- 任務內容：依據本文件建立 ComfyUI 人物對人物姿勢遷移流程
- 指定 Skills：`comfyui-pose-transfer`, `markdown-docs`, `web-research`
- 輸出物：`workflow_spec.md`、`workflow_v1.json`、`param_baseline.md`

### 委派模板 B：檢查與整理輸入資料

- 委派對象：dataset-prep-agent
- 任務內容：檢查姿勢來源圖與身份來源圖是否符合規格，整理至標準資料夾
- 指定 Skills：`filesystem-ops`, `comfyui-install-audit`
- 輸出物：`input_manifest.json`、`data_qc_report.md`

### 委派模板 C：執行與驗收

- 委派對象：run-and-evaluate-agent
- 任務內容：使用既定 workflow 執行生成，輸出結果並做品質標記
- 指定 Skills：`comfyui-pose-transfer`, `pose-transfer-qc`, `image-review`
- 輸出物：`run_log.md`、`results/`、`qc_scorecard.csv`

## OpenClaw 實際操作指令思維

OpenClaw 不應把本專案理解成一次性聊天請求，而應採用「規劃 → 委派 → 執行 → 驗收 → 回寫」的工程流程。公開實務也明確建議代理在複雜任務中先規劃，再使用子代理執行，最後驗證結果後才標記完成。[cite:21][cite:31]

建議主代理每次收到任務時，按以下順序執行：

1. 讀取 `POSE_TRANSFER_OPERATOR_GUIDE.md`。
2. 檢查是否已有既存 workflow 與模型盤點檔。
3. 若沒有，先委派 workflow-designer 與 dataset-prep-agent。
4. 待兩者回傳後，再委派 run-and-evaluate-agent 執行首輪生成。
5. 收到輸出後，依 `pose-transfer-qc` 的規則決定是否重跑、局部修補或可交付。
6. 將最終參數、seed、模型版本與結果清單回寫到專案記錄檔。

## 建議工作區結構

為了讓 OpenClaw 能穩定操作，建議每個代理有自己的 workspace；而在專案層，則維持統一的共享輸出結構，由主代理整理索引。這符合多代理隔離與明確邊界的最佳實務。[cite:24][cite:26]

```text
pose-transfer-project/
  docs/
    POSE_TRANSFER_OPERATOR_GUIDE.md
    workflow_spec.md
    param_baseline.md
    troubleshooting.md
  input/
    pose_source/
    identity_source/
  workflows/
    workflow_v1.json
  results/
    run_001/
    run_002/
  logs/
    input_manifest.json
    run_log.md
    qc_scorecard.csv
```

## 驗收標準

對 OpenClaw 而言，任務完成的定義不能只是「已執行」。只有在以下條件同時成立時，才能標記為完成：

- ComfyUI 工作流可成功載入與運行。
- 輸出圖至少有一張達到姿勢對齊與人物身份可辨識的標準。[cite:1][cite:15]
- 所有必要參數均被記錄，可供重現。
- 若失敗，也已產出故障報告，而不是空白結案。

## 最低可行執行策略

若要先讓專案快速落地，建議 OpenClaw 第一輪只完成以下任務：

- 安裝並檢查 ComfyUI 與必要節點。
- 建立第一版 workflow JSON。
- 用 3 組人物對人物測試資料跑通流程。
- 產出第一版結果與 QC 報告。

這樣做的好處，是先證明整個代理系統真的能從文件出發做出結果，而不是在一開始就被過度複雜的自動化設計拖慢。[cite:23][cite:31]

## 建議主代理內嵌指令片段

以下文字可直接放進主代理的 `SOUL.md` 或 `agent.md`：

```md
當任務與人物對人物姿勢遷移有關時：
1. 先讀取 docs/POSE_TRANSFER_OPERATOR_GUIDE.md。
2. 僅使用人物對人物流程，不得切換到跨物種方案。
3. 任務必須拆成 workflow 設計、資料檢查、執行驗收三段。
4. 優先委派對應 SubAgent；主代理只做整合與決策。
5. 任務完成標準是產出可執行 workflow、測試輸出與參數紀錄，不是單純文字分析。
6. 若輸入資料不合格，先回報資料問題，不可硬跑流程。
```

## 結論

要讓 OpenClaw 真正「動手作」並完成可生產結果的任務，關鍵不只是告訴它用 ComfyUI，而是要把角色、工具、技能、分工、交付物與驗收標準全部寫成可操作規格。OpenClaw 的設計本來就把身份層、技能層、工具層與子代理協作視為獨立能力面，因此這個專案最適合以主代理統籌、SubAgent 分工、專案 Skill 固化 SOP 的方式落地。[cite:18][cite:20][cite:21][cite:22]

在人物對人物姿勢遷移場景下，這樣的架構可以把抽象需求轉成實際可執行工程：先設計工作流，再清理輸入，最後執行與驗收，逐步累積穩定的本地生成能力。[cite:1][cite:15][cite:31]
