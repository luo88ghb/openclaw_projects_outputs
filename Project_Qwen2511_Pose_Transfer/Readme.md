# Qwen-2511 姿勢遷移 (Jojo版)

## 🌟 專案簡介
**Qwen-2511 姿勢遷移** 是一個高效的人物姿勢轉移工具，專為高品質、高精確度的影像生成設計。透過整合 **Streamlit** 前端、**ComfyUI** 算力後端以及 **Gemini 2.5 Pro** 視覺分析大腦，實現將特定人物（原圖）的特徵（臉部、服裝、風格）完美遷移至另一張參考圖的姿勢中。

本專案的「Jojo版」強調實戰化架構，優化了 UI 佈局與操作流程，旨在提供一個「上傳 $\rightarrow$ 分析 $\rightarrow$ 生成」的閉環體驗。

## 🚀 核心功能
- **高精度姿勢克隆**：利用 Qwen 視覺模型與 ComfyUI 工作流，確保產出影像的姿勢與參考圖像素級一致。
- **智能特徵反推 (Nano Banana Pro)**：整合 Gemini 2.5 Pro API，自動分析原圖背景、光影與氛圍，生成專業的描述詞，消除手動輸入的繁瑣。
- **視覺化預處理**：內建自定義影像處理邏輯，自動將不同比例的輸入圖進行等比例縮放並以「高斯模糊背景」填補，確保模型輸入的一致性。
- **動態參數控制**：支援 Seed、CFG、Steps 及輸出解析度（Longest Edge）的即時調整。
- **實時狀態監控**：透過 WebSocket 監控 ComfyUI 節點執行進度，提供詳細的運算日誌與進度條。

## 🛠️ 技術棧
- **Frontend**: Streamlit (Python)
- **Backend**: ComfyUI (via REST API & WebSocket)
- **AI Models**: 
  - 視覺分析: Gemini 2.5 Pro
  - 影像生成: Qwen-2511 / ComfyUI Custom Workflow
- **Image Processing**: Pillow (PIL)
- **Communication**: Requests, Websocket-client

## 📂 快速上手
1. **環境準備**: 確保本地 ComfyUI 伺服器運行於 `127.0.0.1:8188`。
2. **啟動程式**: 執行 `python Zeni_Engine_v9_Pro.py`。
3. **操作流程**:
   - 上傳 **人物原圖** $\rightarrow$ 點擊 **「智能反推原圖特徵」**。
   - 上傳 **姿勢參考圖**。
   - 在進階設定中調整提示詞或參數（可選）。
   - 點擊 **「啟動融合運算」** $\rightarrow$ 確認彈窗 $\rightarrow$ 等待結果產出。
4. **結果查看**: 生成圖片將自動保存至 `Zeni_Results` 資料夾。

## ⚠️ 注意事項
- 請確保環境變數中配置了 `GEMINI_API_KEY` 以啟用智能反推功能。
- 生成品質取決於 `Jojo_workflow_api.json` 的節點配置。
