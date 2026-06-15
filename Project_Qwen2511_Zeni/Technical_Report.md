# Technical Report: Qwen-2511 Pose Transfer (Zeni 升級版)

## 1. Overview

The **Zeni 升級版** 從 Jojo 版的「原型‑實務」模式，全面重構為 **「標準化‑自動化」** 框架，核心目標是提升姿勢遷移精度、去除外部 LLM 依賴，並以 CLI 完全自動化工作流。

---

## 2. Architectural Evolutions

## 2. Architectural Evolutions

### 2.1 Vision‑Language Model (VLM) Migration
- **Legacy (Jojo)**: `Gemini 2.5 Pro` via Google API.
- **Zeni 升級版**: `Qwen‑VL‑Plus/Series` (本地 / OpenAI‑compatible) 搭配 **Precision Pose Refinement** 子模組，以降低姿勢對齊誤差至 2 px 以內。

### 2.2 Core Orchestration via `comfy.cli`
- `setup_comfy.bat` → 建立 Conda 環境、安裝依賴。
- `start_zeni_core.bat` → 使用 `comfy.cli start` 啟動服務，**自動載入** `Zeni_Precision_Core/workflows/precision_pose_transfer.json` 工作流。
- **新增** `Zeni_Precision_Core/` 目錄，包含 `config/`、`modules/`、`workflows/`，專責管理精度校正設定。

### 2.3 Operator Guide Alignment

The project now incorporates the `openclaw_pose_transfer_operator_guide.md` as its "Operational Charter."

- **Strict Boundary**: Limited to "Human-to-Human" transfer.
- **Delivery Standard**: Each run is expected to produce a workflow JSON and a set of parameter records, moving from "image generation" to "process engineering."

---

## 3. System Specifications

## 3. System Specifications

### 3.1 Code Modification Summary
- **`Zeni_Engine_v10_Precision.py`**（正式版）
  - `WORKSPACE` 已指向 `Project_Qwen2511_Zeni`。
  - 內建 `precision_pose_refinement` 呼叫，使用 `Zeni_Precision_Core/modules/pose_refine.py` 進行細部校正。
  - UI 標籤更新為 **Zeni 升級版**，顯示使用 Qwen‑VL‑Plus 與精度校正。
- **保留 `Zeni_Engine_v9_Pro.py`** 作為向後相容（舊環境或測試），說明僅在特殊情況下使用。

### 3.2 File Structure (Zeni 升級版)

```text
Project_Qwen2511_Zeni/
├── Zeni_Engine_v10_Precision.py      # 主引擎，內建精度校正
├── Zeni_Engine_v9_Pro.py            # 向後相容，僅供舊環境使用
├── Zeni_Precision_Core/             # 核心子模組，含精度設定與工作流
│   ├── config/
│   ├── modules/
│   └── workflows/precision_pose_transfer.json
├── setup_comfy.bat
├── start_eni_core.bat
├── Readme.md
├── Technical_Report.md
└── Zeni_Results/               # 輸出結果與 QC 報告
```

---

## 4. Verification & QC (Quality Control)

Zeni 升級版加入 **精度驗證流程**，確保姿勢對齊誤差 < 2 px 且身份保持一致。

1. **Pose Alignment QC** – 透過 `pose_alignment_qc.py` 計算關鍵點偏差。
2. **Identity Consistency QC** – 使用 `face_verification_qc.py` 進行臉部相似度檢測。
3. **自動化測試** – `pytest -m qc` 在 CI 中執行，報告儲存在 `Zeni_Results/pose_refinement_report.json`。

## 5. Conclusion

The Zeni Edition successfully decouples the project from external API dependencies and introduces a professional deployment layer. It transforms a "tool" into a "standardized agent-capable project."
