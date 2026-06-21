"""
engine/knockout_simulator.py
2026 FIFA 世界盃淘汰賽推演器

輸入：
- data/matches_104.json (賽程骨架，含 R32/R16/QF/SF/Final 佔位符)
- predictions/advanced_predictions.json (小組賽預測結果)
- data/third_place_combinations.csv (FIFA Annex C 映射表)

輸出：
- predictions/knockout_predictions.json
- predictions/Knockout_Prediction_Report.md

邏輯：
1. 從小組賽預測計算各組 1st/2nd/3rd 排名。
2. 選出 8 支最佳第三名，依 Annex C 填入 R32 的 8 個 "3X" 佔位符。
3. 其餘 R32 佔位符直接由小組 1st/2nd 替換。
4. 使用 ThreeVectorModel 預測每場淘汰賽勝負；和局時依勝率偏置抽籤決定晉級。
5. 逐輪推演至冠軍、亞軍、季軍。
"""
import json
import csv
import re
import random
from pathlib import Path
from datetime import datetime
from typing import Any

from advanced_predictor import ThreeVectorModel, PredictionResearch, load_json, save_json

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"
KNOCKOUT_OUTPUT = PREDICTIONS_DIR / "knockout_predictions.json"
REPORT_OUTPUT = PREDICTIONS_DIR / "Knockout_Prediction_Report.md"
ANNEX_C_PATH = DATA_DIR / "third_place_combinations.csv"

# 淘汰賽對陣骨架（match_id, home_slot, away_slot）
R32_FIXTURES = [
    (73, "2A", "2B"),
    (74, "1E", "3ABCDF"),
    (75, "1F", "2C"),
    (76, "1C", "2F"),
    (77, "1I", "3CDFGH"),
    (78, "2E", "2I"),
    (79, "1A", "3CEFHI"),
    (80, "1L", "3EHIJK"),
    (81, "1D", "3BEFIJ"),
    (82, "1G", "3AEHIJ"),
    (83, "2K", "2L"),
    (84, "1H", "2J"),
    (85, "1B", "3EFGIJ"),
    (86, "1J", "2H"),
    (87, "1K", "3DEIJL"),
    (88, "2D", "2G"),
]

R16_FIXTURES = [
    (89, 74, 77),
    (90, 73, 75),
    (91, 76, 78),
    (92, 79, 80),
    (93, 83, 84),
    (94, 81, 82),
    (95, 86, 88),
    (96, 85, 87),
]

QF_FIXTURES = [
    (97, 89, 90),
    (98, 93, 94),
    (99, 91, 92),
    (100, 95, 96),
]

SF_FIXTURES = [
    (101, 97, 98),
    (102, 99, 100),
]

THIRD_PLACE = (103, 101, 102)
FINAL = (104, 101, 102)


def load_annex_c(path: Path) -> list[dict]:
    """載入 FIFA Annex C 表格，回傳 list of dict。"""
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def find_annex_c_mapping(annex_rows: list[dict], qualifying_groups: set[str]) -> dict:
    """
    根據晉級的 8 個小組，查 Annex C 表，回傳各 match_id 應對應的第三名小組。
    回傳格式: {match_id: 'E', ...}
    """
    # 找出 12 個 group 欄位（Third-placed teams advance from groupsvte...）
    group_cols = [c for c in annex_rows[0].keys() if "Third-placed teams advance from groupsvte" in c]
    match_cols = [c for c in annex_rows[0].keys() if " vs" in c]

    for row in annex_rows:
        row_groups = set()
        for col in group_cols:
            val = row.get(col, "").strip()
            if val:
                row_groups.add(val)
        if row_groups == qualifying_groups:
            mapping = {}
            for col in match_cols:
                # col 例如 "1A vs"，match_id 對應
                val = row.get(col, "").strip()
                if val.startswith("3"):
                    grp = val[1:]
                    # col 形如 "1A vs" -> 找對應 match_id
                    winner_label = col.split()[0]  # "1A"
                    mid = _winner_label_to_match_id(winner_label)
                    if mid:
                        mapping[mid] = grp
            return mapping

    raise ValueError(f"Annex C 找不到對應組合: {qualifying_groups}")


def _winner_label_to_match_id(label: str) -> int | None:
    """把小組第一標籤 (1A, 1B...) 映射到 R32 match_id。"""
    mapping = {
        "1A": 79, "1B": 85, "1C": 76, "1D": 81,
        "1E": 74, "1F": 75, "1G": 82, "1H": 84,
        "1I": 77, "1J": 86, "1K": 87, "1L": 80,
    }
    return mapping.get(label)


class KnockoutSimulator:
    def __init__(self, group_stage_result: dict, teams_db: dict, model: ThreeVectorModel, seed: int = 42):
        self.group_stage = group_stage_result
        self.teams_db = teams_db
        self.model = model
        self.random = random.Random(seed)
        self.standings = group_stage_result["standings"]
        self.round_of_32 = group_stage_result["round_of_32"]
        self.results: dict[int, dict] = {}

    def resolve_slot(self, slot: str) -> str:
        """解析佔位符為實際球隊名稱。"""
        # 小組排名佔位符：1A, 2B, 3C 等
        m = re.match(r"^(1|2|3)([A-L])$", slot)
        if m:
            rank = int(m.group(1))
            group = m.group(2)
            ranked = self.standings.get(group, [])
            if len(ranked) >= rank:
                return ranked[rank - 1]["team"]
            raise ValueError(f"無法解析佔位符 {slot}，小組 {group} 排名不足")

        # 賽事勝方佔位符：例如 "第73場勝方"
        m = re.match(r"第(\d+)場勝方", slot)
        if m:
            mid = int(m.group(1))
            return self.results[mid]["winner"]

        # 賽事敗方佔位符：例如 "第101場敗方"
        m = re.match(r"第(\d+)場敗方", slot)
        if m:
            mid = int(m.group(1))
            return self.results[mid]["loser"]

        # 特殊最佳第三名佔位符：3ABCDF 等，已在 build_r32 處理
        if slot.startswith("3") and len(slot) > 2:
            raise ValueError(f"最佳第三名佔位符 {slot} 應在 build_r32 階段處理")

        raise ValueError(f"無法解析佔位符 {slot}")

    def build_r32(self, annex_rows: list[dict]) -> list[dict]:
        """根據 Annex C 建立 32 強完整對陣。"""
        # 8 支最佳第三名所屬小組
        best_thirds = self.round_of_32["third_place_ranking"][:8]
        qualifying_groups = {t["group"] for t in best_thirds}
        mapping = find_annex_c_mapping(annex_rows, qualifying_groups)

        # 建立 group -> team 映射
        third_team_by_group = {t["group"]: t["team"] for t in best_thirds}

        fixtures = []
        for mid, home_slot, away_slot in R32_FIXTURES:
            # 若 away_slot 是 "3..." 這類最佳第三名池，用 mapping 找對應小組
            if away_slot.startswith("3") and len(away_slot) > 2:
                target_group = mapping[mid]
                away_team = third_team_by_group[target_group]
            else:
                away_team = self.resolve_slot(away_slot)

            home_team = self.resolve_slot(home_slot)
            fixtures.append({
                "match_id": mid,
                "stage": "32強",
                "home_team": home_team,
                "away_team": away_team,
                "home_slot": home_slot,
                "away_slot": away_slot,
            })
        return fixtures

    def simulate_match(self, match: dict) -> dict:
        """使用 ThreeVectorModel 預測單場淘汰賽，並決定勝方。"""
        home = match["home_team"]
        away = match["away_team"]
        pred = self.model.predict(home, away)

        home_prob = pred["home_win_prob"]
        away_prob = pred["away_win_prob"]
        draw_prob = pred["draw_prob"]

        # 淘汰賽採用「最可能晉級」原則：勝率較高者直接晉級
        if home_prob > away_prob:
            winner = home
        elif away_prob > home_prob:
            winner = away
        else:
            winner = home if self.random.random() < 0.5 else away
        loser = away if winner == home else home

        # 產生與勝方一致的「最終」比分（90 分鐘 + 加時/點球）
        home_score = pred["predicted_home_score"]
        away_score = pred["predicted_away_score"]
        if winner == home and home_score <= away_score:
            home_score = away_score + 1
        elif winner == away and away_score <= home_score:
            away_score = home_score + 1

        return {
            "match_id": match["match_id"],
            "stage": match.get("stage", "淘汰賽"),
            "home_team": home,
            "away_team": away,
            "home_score": home_score,
            "away_score": away_score,
            "winner": winner,
            "loser": loser,
            "home_win_prob": home_prob,
            "draw_prob": draw_prob,
            "away_win_prob": away_prob,
            "predicted_home_score": pred["predicted_home_score"],
            "predicted_away_score": pred["predicted_away_score"],
            "vector_breakdown": pred["vector_breakdown"],
            "reason": pred["reason"],
            "home_slot": match.get("home_slot"),
            "away_slot": match.get("away_slot"),
        }

    def simulate_round(self, fixtures: list[dict]) -> list[dict]:
        """推演一輪比賽。"""
        results = []
        for f in fixtures:
            res = self.simulate_match(f)
            self.results[res["match_id"]] = res
            results.append(res)
        return results

    def build_next_round(self, fixtures_spec: list[tuple], stage_name: str) -> list[dict]:
        """根據上一輪結果建立下一輪對陣。"""
        fixtures = []
        for mid, home_prev, away_prev in fixtures_spec:
            home_team = self.results[home_prev]["winner"]
            away_team = self.results[away_prev]["winner"]
            fixtures.append({
                "match_id": mid,
                "stage": stage_name,
                "home_team": home_team,
                "away_team": away_team,
            })
        return fixtures

    def simulate_full_knockout(self, annex_rows: list[dict]) -> dict:
        """推演完整淘汰賽。"""
        r32 = self.build_r32(annex_rows)
        r32_results = self.simulate_round(r32)

        r16 = self.build_next_round(R16_FIXTURES, "16強")
        r16_results = self.simulate_round(r16)

        qf = self.build_next_round(QF_FIXTURES, "8強")
        qf_results = self.simulate_round(qf)

        sf = self.build_next_round(SF_FIXTURES, "4強")
        sf_results = self.simulate_round(sf)

        # 季軍戰
        third_mid, third_home_prev, third_away_prev = THIRD_PLACE
        third_fixture = [{
            "match_id": third_mid,
            "stage": "季軍戰",
            "home_team": self.results[third_home_prev]["loser"],
            "away_team": self.results[third_away_prev]["loser"],
        }]
        third_results = self.simulate_round(third_fixture)

        # 決賽
        final_mid, final_home_prev, final_away_prev = FINAL
        final_fixture = [{
            "match_id": final_mid,
            "stage": "決賽",
            "home_team": self.results[final_home_prev]["winner"],
            "away_team": self.results[final_away_prev]["winner"],
        }]
        final_results = self.simulate_round(final_fixture)

        champion = final_results[0]["winner"]
        runner_up = final_results[0]["loser"]
        third_place = third_results[0]["winner"]

        return {
            "round_of_32": r32_results,
            "round_of_16": r16_results,
            "quarter_finals": qf_results,
            "semi_finals": sf_results,
            "third_place": third_results[0],
            "final": final_results[0],
            "champion": champion,
            "runner_up": runner_up,
            "third_place_team": third_place,
        }


def generate_report(result: dict, output_path: Path) -> None:
    """產生 Markdown 格式的淘汰賽預測報告。"""
    lines = [
        "# 2026 FIFA 世界盃 淘汰賽預測報告",
        "",
        f"- **產生時間**：{datetime.now().isoformat()}",
        "- **方法論**：three-vector-strategy + FIFA Annex C 對陣映射",
        "- **範圍**：32強 → 16強 → 8強 → 4強 → 季軍戰 → 決賽",
        "- **版本**：knockout-v1.0",
        "",
        "---",
        "",
        "## 🏆 最終預測結果",
        "",
        f"| 名次 | 球隊 |",
        f"|:----:|:----:|",
        f"| 冠軍 | {result['champion']} |",
        f"| 亞軍 | {result['runner_up']} |",
        f"| 季軍 | {result['third_place_team']} |",
        "",
        "---",
        "",
    ]

    stage_titles = {
        "round_of_32": "## ⚔️ 32強",
        "round_of_16": "## ⚔️ 16強",
        "quarter_finals": "## ⚔️ 8強",
        "semi_finals": "## ⚔️ 4強",
    }

    for key, title in stage_titles.items():
        lines.extend([title, ""])
        for m in result[key]:
            lines.append(
                f"- **第 {m['match_id']} 場**：{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']} "
                f"→ 勝方：**{m['winner']}** "
                f"(勝率 {m['home_win_prob']}% / 和 {m['draw_prob']}% / 客勝 {m['away_win_prob']}%)")
            lines.append(f"  - 理由：{m['reason']}")
            lines.append("")

    # 季軍戰與決賽
    tp = result["third_place"]
    lines.extend([
        "## 🥉 季軍戰",
        "",
        f"- **第 {tp['match_id']} 場**：{tp['home_team']} {tp['home_score']} - {tp['away_score']} {tp['away_team']} → 季軍：**{tp['winner']}**",
        f"  - 理由：{tp['reason']}",
        "",
        "## 🥇 決賽",
        "",
    ])
    final = result["final"]
    lines.append(
        f"- **第 {final['match_id']} 場**：{final['home_team']} {final['home_score']} - {final['away_score']} {final['away_team']} "
        f"→ 冠軍：**{final['winner']}**")
    lines.append(f"  - 理由：{final['reason']}")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    print("[KnockoutSimulator] 載入小組賽預測...")
    advanced = load_json(PREDICTIONS_DIR / "advanced_predictions.json")
    group_stage = advanced["group_stage"]

    teams_data = load_json(DATA_DIR / "teams.json")
    teams_db = {t["name_zh"]: t for t in teams_data["teams"]}

    research = PredictionResearch()
    model = ThreeVectorModel(research, teams_db)

    print("[KnockoutSimulator] 載入 Annex C 表格...")
    annex_rows = load_annex_c(ANNEX_C_PATH)

    print("[KnockoutSimulator] 開始推演淘汰賽...")
    simulator = KnockoutSimulator(group_stage, teams_db, model, seed=42)
    result = simulator.simulate_full_knockout(annex_rows)

    output = {
        "metadata": {
            "version": "knockout-v1.0",
            "generated_at": datetime.now().isoformat(),
            "source": "engine/knockout_simulator.py",
            "scope": "knockout_stage",
            "method": "three-vector-strategy",
            "note": "基於 advanced_predictions.json 小組賽預測結果，使用 FIFA Annex C 表格決定 32 強對陣，並推演至決賽。",
        },
        "knockout": result,
    }

    save_json(KNOCKOUT_OUTPUT, output)
    generate_report(result, REPORT_OUTPUT)

    print(f"[KnockoutSimulator] 冠軍：{result['champion']}")
    print(f"[KnockoutSimulator] 報告已儲存：{REPORT_OUTPUT}")
    print(f"[KnockoutSimulator] JSON 已儲存：{KNOCKOUT_OUTPUT}")


if __name__ == "__main__":
    main()
