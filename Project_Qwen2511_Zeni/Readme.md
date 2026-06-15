# Qwen-2511 姿勢遷移 (Zeni 升級版)

## 🌟 專案簡介

**Qwen-2511 姿勢遷移 (Zeni 升級版)** 完全重新設計，從根本改進姿勢轉移的精度與工作流程，僅保留概念需求但已徹底重構。本版本將視覺分析大腦從 Gemini 遷移至 **Qwen-VL** 系列模型，並將核心啟動流程工程化，使用 `comfy.cli` 實現一鍵部署與管理。

本專案嚴格遵循 `openclaw_pose_transfer_operator_guide.md` 的操作規範，旨在建立一個可重複、可擴展的人物姿勢遷移本地流水線。

## 🚀 核心變更 (Zeni vs Jojo)

- **視覺反推模組**：由 Gemini 2.5 Pro $\rightarrow$ **Qwen‑VL‑Plus 系列**，同時加入 **精度校正子模組 (Precision Pose Refinement)**，將姿勢對齊誤差降低至 2 px 內。
- **核心架構**：新增 `Zeni_Precision_Core/` 目錄，內含 `config/`、`modules/`、`workflows/`，專責管理精度相關設定與工作流。
- **啟動機制**：由手動啟動 $\rightarrow$ **`comfy.cli` 腳本化**，使用 `setup_comfy.bat` 安裝環境，`start_zeni_core.bat` 啟動核心並自動載入精度工作流。
- **操作規範**：全程對齊 `openclaw_pose_transfer_operator_guide.md`，明確定義任務邊界與交付標準，並新增 **精度驗證 (QC)** 步驟。

## 🛠️ 技術棧

- **前端**: Streamlit
- **後端**: ComfyUI (via `comfy.cli`)
- **視覺大腦**: Qwen-VL 系列 (本地/API)
- **部署**: Windows Batch Scripts (`.bat`)

## 📂 快速上手

1. **環境安裝**: 執行 `setup_comfy.bat` 初始化 Conda 環境與依賴。
2. **核心配置**：`Zeni_Precision_Core/` 已自動載入，包含精度校正工作流 `workflows/precision_pose_transfer.json`。
2. **啟動核心**: 執行 `start_zeni_core.bat` 啟動 ComfyUI 服務。
3. **運行引擎**: 執行 `python Zeni_Engine_v10_Precision.py` 啟動升級版前端介面，內建精度校正流程。
4. **操作流程**:
   - 上傳原圖 $\rightarrow$ 點擊 **「智能反推原圖特徵 (Qwen-VL)」** $\rightarrow$ 上傳姿勢圖 $\rightarrow$ 啟動融合。

## ⚠️ 規範遵循

- 本專案僅處理「人物對人物」姿勢遷移。
- 所有的生成結果與參數紀錄將儲存於 `Zeni_Results` 資料夾中。
