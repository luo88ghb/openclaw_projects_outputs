"""
engine/generate_prediction_report.py
將 predictions/advanced_predictions.json 轉換為人類可讀的 Markdown 報告。

輸出：predictions/Advanced_Prediction_Report.md
"""
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = BASE_DIR / "predictions"
REPORT_PATH = PREDICTIONS_DIR / "Advanced_Prediction_Report.md"


def load_predictions() -> dict:
    path = PREDICTIONS_DIR / "advanced_predictions.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_report(data: dict) -> str:
    meta = data.get("metadata", {})
    group_stage = data.get("group_stage", {})
    predictions = group_stage.get("predictions", [])
    standings = group_stage.get("standings", {})
    round_of_32 = group_stage.get("round_of_32", {})

    lines = []
    lines.append("# 2026 FIFA 世界盃 進階預測報告")
    lines.append("")
    lines.append(f"- **產生時間**：{meta.get('generated_at', '未知')}")
    lines.append(f"- **方法論**：{meta.get('method', '三視角策略模型')}")
    lines.append(f"- **範圍**：{meta.get('scope', '小組賽 72 場')}")
    lines.append(f"- **版本**：{meta.get('version', 'advanced-v1.0')}")
    lines.append(f"- **備註**：{meta.get('note', '')}")
    lines.append("")

    # 一、32 強晉級名單
    lines.append("## 一、預測 32 強晉級名單")
    lines.append("")
    qualified = round_of_32.get("qualified_teams", [])
    lines.append(f"共 **{len(qualified)}** 支球隊：")
    lines.append("")
    lines.append(", ".join(qualified))
    lines.append("")

    # 最佳第三名
    best_third = round_of_32.get("best_third_teams", [])
    if best_third:
        lines.append("### 最佳第三名晉級")
        lines.append("")
        for i, t in enumerate(best_third, 1):
            # t 可能是字串或 dict
            if isinstance(t, dict):
                lines.append(f"{i}. {t['team']}（{t['group']} 組，{t['points']} 分）")
            else:
                lines.append(f"{i}. {t}")
        lines.append("")

    # 二、各組積分排名
    lines.append("## 二、各組積分排名預測")
    lines.append("")
    for group in sorted(standings.keys()):
        lines.append(f"### {group} 組")
        lines.append("")
        lines.append("| 排名 | 球隊 | 賽 | 勝 | 平 | 負 | 進球 | 失球 | 淨球 | 積分 |")
        lines.append("|:----:|:----:|:-:|:--:|:--:|:--:|:----:|:----:|:----:|:----:|")
        for i, t in enumerate(standings[group], 1):
            lines.append(
                f"| {i} | {t['team']} | {t['played']} | {t['wins']} | {t['draws']} | "
                f"{t['losses']} | {t['gf']} | {t['ga']} | {t['gf'] - t['ga']} | {t['points']} |"
            )
        lines.append("")

    # 三、小組賽逐場預測
    lines.append("## 三、小組賽逐場預測")
    lines.append("")

    current_group = None
    for p in predictions:
        g = p.get("group")
        if g != current_group:
            current_group = g
            lines.append(f"### {g} 組")
            lines.append("")

        home = p["home_team"]
        away = p["away_team"]
        h_score = p["predicted_home_score"]
        a_score = p["predicted_away_score"]
        h_prob = p["home_win_prob"]
        d_prob = p["draw_prob"]
        a_prob = p["away_win_prob"]
        reason = p.get("reason", "")
        vectors = p.get("vector_breakdown", {})

        lines.append(f"**Match {p['match_id']}：{home} {h_score}-{a_score} {away}**")
        lines.append("")
        lines.append(f"- 主勝 {h_prob}% / 和局 {d_prob}% / 客勝 {a_prob}%")
        lines.append(f"- 三視角：A（量化）{vectors.get('A', {}).get('home')} vs {vectors.get('A', {}).get('away')}；"
                     f"B（戰術）{vectors.get('B', {}).get('home')} vs {vectors.get('B', {}).get('away')}；"
                     f"C（外部）{vectors.get('C', {}).get('home')} vs {vectors.get('C', {}).get('away')}")
        lines.append(f"- 理由：{reason}")
        lines.append("")

    # 四、方法說明
    lines.append("## 四、方法論說明")
    lines.append("")
    lines.append("本預測採用 **三視角策略模型**：")
    lines.append("")
    lines.append("- **Vector A（量化數據，40%）**：FIFA 排名、近期重大賽事成績、陣容身價與攻防數據。")
    lines.append("- **Vector B（戰術相剋，35%）**：教練體系、陣型對位、風格剋制與歷史交手。")
    lines.append("- **Vector C（外部變數，25%）**：北美主場效應、氣候適應度、博彩賠率共識、旅行負荷。")
    lines.append("")
    lines.append("所有預測均基於 search 工具搜集的真實資料，並快取於 `cache/prediction_research_cache.json`，避免重複搜尋。")
    lines.append("")

    # 五、免責聲明
    lines.append("## 五、免責聲明")
    lines.append("")
    lines.append("此報告僅供娛樂與策略參考，足球比賽結果受眾多不可預測因素影響，不構成任何投注建議。")
    lines.append("")

    return "\n".join(lines)


def main():
    data = load_predictions()
    report = build_report(data)
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[Report] Generated: {REPORT_PATH}")


if __name__ == "__main__":
    main()
