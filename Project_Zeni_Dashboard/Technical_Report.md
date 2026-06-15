# 🛠️ Project_Ollama_Dashboard 技術報告 (Technical Report)
- **核心腳本**: `zeni_ollama_dashboard.py`
- **功能模組**:
  - 智能調度: 自動切換至安全模型 (例如本地 qwen359b)。
  - 監控閾值: 85% $\rightarrow$ 警告, 95% $\rightarrow$ 危險。
  - 通知通道: Telegram。
- **Cron Job ID**: `0e7e03fa-ef9b-4ff9-bc2e-55da-0e8cd1c5`
