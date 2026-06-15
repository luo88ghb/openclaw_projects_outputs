# Zeni-Precision 架構變更計畫 (2026-06-04)

## 1. 核心目標：從「全局傳遞」轉向「分層精煉」
目前的 Jojo/Zeni 方案僅為單一階段的全局 IP-Adapter 注入，缺乏對面部局部特徵（眼神、唇形、面部骨骼微調）的精確控制。本計畫旨在建立一套基於「分層精煉 (Layered Refinement)」的物理架構。

## 2. 物理架構重構 (Physical Restructuring)
取消扁平化的檔案存放方式，建立邏輯分層目錄：

- **路徑**: `C:\Users\danny\.openclaw\workspace\projects\Project_Qwen2511_Pose_Transfer\Zeni_Precision_Core\`
  - `/workflows/`: 存放分段 JSON。
    - `base_pose_transfer.json`: 負責姿勢遷移與全局特徵基礎。
    - `face_refinement.json`: 負責高精度局部五官重繪 (Inpainting)。
  - `/config/`: 存放節點對應表與權重配置。
  - `/modules/`: 存放 Zeni 專屬的後處理邏輯。

## 3. 引擎邏輯升級 (`Zeni_Engine_v10_Precision.py`)
- **模式變更**: $\text{Single Call} \rightarrow \text{Pipeline Call}$。
- **執行流**: 
  1. `Input` $\rightarrow$ `base_pose_transfer.json` $\rightarrow$ `Intermediate_Image`
  2. `Intermediate_Image` $\rightarrow$ `face_refinement.json` $\rightarrow$ `Final_Image`
- **動態控制**: 引入 `precision_level` 參數，動態調整 `FaceDetailer` 的偵測閾值與重繪強度 (Denoising Strength)。

## 4. 節點工程變更 (Kijai/KJNodes-Style Topology)
在 `face_refinement.json` 中實作以下關鍵鏈路：
- **精確遮罩**: $\text{SAM (Segment Anything)} \rightarrow \text{Face BBox}$ $\rightarrow$ 建立像素級面部遮罩。
- **特徵強化**: $\text{FaceID-PlusV2}$ $\times$ $\text{Local Inpainting}$ $\rightarrow$ 在遮罩區域內強制執行高權重特徵對齊。
- **邊緣融合**: 利用 `KJNodes` 的 $\text{MaskBlur}$ 與 $\text{ImageBlend}$ 節點，消除局部重繪的接縫感。

## 5. 驗證指標 (Success Metrics)
- **物理層面**: 必須出現 `Zeni_Precision_Core` 目錄及分段 JSON 檔案。
- **邏輯層面**: `Zeni_Engine_v10` 必須能證明其在執行過程中觸發了兩次獨立的 API 調用。
- **視覺層面**: 五官的細節（尤其是眼睛與嘴巴）與源圖的對齊度顯著提升。
