# 短影音平台成功案例研究與簡報製作 - 專案總指揮文件

## 專案概述
- **專案名稱**: 短影音平台成功案例研究
- **起始時間**: 2026-04-04 13:05 GMT+8
- **目標**: 研究 TikTok/YouTube Shorts/Instagram Reels 三大平台 12 個成功典範，輸出圖文簡報
- **最終交付**: 12-18頁結構化簡報

## 團隊組成

| 角色 | Agent ID | 模型 | 核心職責 |
|------|----------|------|----------|
| bot1 總控PM | main | minimax-m2.7:cloud | 制定流程、分配任務、整合輸出 |
| bot2 平台研究員 | platform-researcher | kimi-k2.5:cloud | 研究三大平台邏輯與特性 |
| bot3 案例分析師 | case-analyst | kimi-k2.5:cloud | 蒐集篩選12個案例、建立案例卡 |
| bot4 內容策略師 | content-strategist | glm-5:cloud | 歸納策略框架、腳本建議 |
| bot5 簡報設計師 | presentation-designer | minimax-m2.7:cloud | 產出圖文簡報 |

## 工作流程

### Phase 1: 平台研究 (bot2)
- 研究 TikTok/YouTube Shorts/Instagram Reels 平台特性
- 整理成功訊號與內容偏好
- 輸出: platform_analysis.md

### Phase 2: 案例蒐集與分析 (bot3)
- 依篩選標準提出12個候選案例
- 完成12份案例卡 (每案例13個欄位)
- 輸出: case_cards.md + case_summary_table.md

### Phase 3: 策略框架建構 (bot4)
- 跨案例分析萃取出成功公式
- 回答8個核心問題
- 輸出: strategy_framework.md

### Phase 4: 簡報製作 (bot5)
- 依研究結論產出12-18頁圖文簡報
- 製作圖表、案例卡、流程圖
- 輸出: ShortVideo_Research_Presentation.md

### Phase 5: 品質審查 (bot1)
- 檢查邏輯一致性與完整度
- 確認結論有案例支撐
- 輸出: quality_review.md

## 里程碑

| 階段 | 負責 | 產出 | 狀態 |
|------|------|------|------|
| M1: 團隊建立 | bot1 | 各bot工作目錄 | ✅ |
| M2: 平台研究 | bot2 | platform_analysis.md | 🔄 |
| M3: 案例分析 | bot3 | case_cards.md | ⏳ |
| M4: 策略框架 | bot4 | strategy_framework.md | ⏳ |
| M5: 簡報製作 | bot5 | 簡報檔案 | ⏳ |
| M6: 品質審查 | bot1 | quality_review.md | ⏳ |

## 12個案例分配

### TikTok (4個)
1. 個人創作者 - 美食/生活
2. 品牌帳號 - 電商導購
3. 教育型內容 - 技能教學
4. 娛樂型 - 挑戰/系列

### YouTube Shorts (4個)
1. 個人創作者 - 知識型
2. 品牌帳號 - 娛樂行銷
3. 新聞/資訊型
4. 系列實驗型

### Instagram Reels (4個)
1. 個人創作者 - 生活方式
2. 品牌帳號 - 審美導向
3. 商品導購型
4. 故事敘事型

## 成功標準
- 每個結論都有案例或資料支撐
- 簡報視覺清楚可直接用於匯報
- 涵蓋平台通用與平台特有成功因素
- 區分可複製與需調整元素
