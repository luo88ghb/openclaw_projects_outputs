# OpenClaw Projects Outputs

這是羅哥的 OpenClaw 工作區中 `projects/` 資料夾的統一備份倉庫，用於集中管理各類專案輸出、實驗原型與技術文件。

---

## 📁 專案一覽

### 🎯 重要專案

| 專案資料夾 | 狀態 | 說明 |
|---|---|---|
| `chat-arena` | ✅ 已備份 | 重要專案，請參考資料夾內文件 |
| `Project_FIFA_WorldCup_2026_TW` | ✅ 已備份 | 2026 世界盃台灣播放時程儀表板與預測分析 |
| `Project_Qwen2511_Pose_Transfer` | ✅ 已備份 | Qwen2.5-VL 姿態遷移專案 |
| `Project_Zeni_Dashboard` | ✅ 已備份 | Zeni Ollama Dashboard |
| `Lobster_Semantic_Super_Retrieval_System` | 🔗 Submodule | 獨立倉庫：[Lobster-Semantic-Super-Retrieval-System](https://github.com/luo88ghb/Lobster-Semantic-Super-Retrieval-System.git) |
| `Zeni_Creative_Advertising` | 🔗 Submodule | 獨立倉庫：[Zeni_Creative_Advertising](https://github.com/luo88ghb/Zeni_Creative_Advertising.git) |

### 🧪 實驗 / 測試專案

| 專案資料夾 | 狀態 | 說明 |
|---|---|---|
| `Comfyui_Qwen2511_Anti` | ✅ 已備份 | ComfyUI / Qwen 相關對抗/檢測實驗 |
| `Creative_Topics_Project` | ✅ 已備份 | 創意主題企劃與腳本 |
| `Project_Gemma4_E4B_TestTool` | ✅ 已備份 | Gemma4 E4B 測試工具 |
| `Project_Qwen2511_Zeni` | ✅ 已備份 | Qwen2.5-VL 相關實驗 |
| `SafeUpgrade-Guard` | ✅ 已備份 | 安全升級守護相關 |
| `ShortVideo_Research` | ✅ 已備份 | 短影音研究 |
| `Zeni_Brain_Ready` | ✅ 已備份 | 注意：`model.safetensors` 等大型模型檔被 `.gitignore` 排除，未上傳 |

### ⏸️ 暫停 / 未完成

| 專案資料夾 | 狀態 | 說明 |
|---|---|---|
| `visual_script_competition` | ⏸️ 暫停中 | `chat-arena` 的擴展應用任務。主代理將子代理放在沙盒中運作，技術架構的前後端與 Node.js HTTP Server 和外部聯繫不順利，目前無法解決，任務暫停。詳見該資料夾 `README.md`。 |

### 📦 備份 / 歷史版本

| 專案資料夾 | 狀態 | 說明 |
|---|---|---|
| `Project_FIFA_WorldCup_2026_TW_backup_pre_cleanup` | ✅ 已備份 | 世界盃專案清理前的備份版本 |
| `Zeni_Results` | ✅ 已備份 | Zeni 相關結果彙整 |

### ❌ 未納入此 Repo

以下資料夾由 `.gitignore` 排除，不在本倉庫管理範圍內：

- `.npm/` — npm cache
- `.pi/` — 樹莓派相關
- `bot-monitor-py/`
- `data_files/`
- `erina-mano 真野惠里菜/` — 獨立子倉庫
- `logs/`
- `news_search_data/`
- `research_logs/`
- `rollback/`
- `scripts/`
- `workspace/`
- `__pycache__/`

---

## 🔧 使用說明

```bash
# Clone 本倉庫（不含 submodule）
git clone https://github.com/luo88ghb/openclaw_projects_outputs.git

# Clone 包含 submodule
git clone --recurse-submodules https://github.com/luo88ghb/openclaw_projects_outputs.git

# 若已 clone 但未拉 submodule
git submodule update --init --recursive
```

---

## 📝 備份紀錄

- **2026-06-15**: 統一備份所有專案至本倉庫，並以 submodule 引用 `Lobster_Semantic_Super_Retrieval_System` 與 `Zeni_Creative_Advertising`。

---

> 本倉庫由 OpenClaw 助手 傑尼 (Zeni) 維護整理。
