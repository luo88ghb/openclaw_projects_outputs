# 專案總結報告：傑尼 - AI 運作狀態與測試戰情室 (Zeni AI Dashboard)

## 📅 建立日期
2026-02-28

## 🎯 專案概述
這是一個為本機端量身打造的「AI 戰情室」與基準測試 (Benchmark) 平台，旨在幫助使用者即時監控系統資源，並同時對雲端模型 (Gemini 3 系列) 與本地端模型 (Ollama / Gemma 3 等) 進行推論效能對比。

## 🛠️ 核心技術棧
- **後端**: Python, Flask, psutil, requests
- **前端**: HTML5, JavaScript, Bootstrap 5
- **部署**: Docker, Docker Compose (背景常駐運行)
- **API 整合**: Google Gemini API, Ollama 本地 API, Telegram Bot API, OpenClaw Gateway API

## ✨ 關鍵功能與技術突破

### 1. 多維度硬體與服務監控
- 即時顯示本機 CPU 與 RAM 佔用率。
- **GPU VRAM 佔用透視**: 透過解析 Ollama 隱藏 API (`/api/ps`)，實作了 GPU VRAM 佔用率的即時監控 (顯示格式如 `16 GB : 8.1 GB` 或 `未載入`)。
- 監控 OpenClaw Gateway 與 Ollama 服務的在線狀態 (Active/Offline)。

### 2. 雲地模型並行測試 (Benchmarking)
- 自動抓取並列出本機 Ollama 模型（動態計算並標示檔案大小，例如 `8.1 GB`）與雲端 Gemini 模型清單。
- 支援單一 Prompt 同步下發給多個勾選的模型進行跑分。
- **精準計時分離**: 成功將本地模型的「模型載入時間 (Cold Start, 搬運至 VRAM)」與「純推論時間 (Eval Duration)」分離，為效能對比提供最精確、客觀的數據。

### 3. 強大的 Telegram 警報與推播機制
- **任務啟動通知**: 測試開始時推送模型清單與提示詞摘要。
- **API Rate Limit 防護與自癒**: 偵測到 Gemini API 429 限制時，系統會自動暫停 60 秒並推送警報至手機，待冷卻完畢後自動重試並通知恢復。
- **結果總結報表**: 測試完成後，自動彙整各模型的耗時與狀態推播給使用者。
- **高可用性重試機制**: 針對 Telegram 推播加入 3 次 Retry 機制，徹底解決了因瞬間網路波動導致的推播漏發問題 (`409 Conflict` & `fetch failed`)。

## 🚀 專案意義
此專案成功將「盲測」轉變為「視覺化數據管理」。大幅提升了 OpenClaw 平台與本地/雲端大模型的協作透明度。羅哥現在擁有一個現代化、自動化且具備完整容錯與通知機制的 AI 系統監控中心。
