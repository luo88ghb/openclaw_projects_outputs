"""
engine/phase_predictor.py
2026 FIFA 世界盃「分階段滾動預測器」

設計理念（羅哥 2026-06-19 指示）：
- 每一單場都要預測，不是只預測晉級隊伍。
- 切成 6 個階段：
  Phase 1: #1–#72  小組賽單場預測 + 32 強名單
  Phase 2: #73–#88 32強單場預測 + 16 強名單
  Phase 3: #89–#96 16強單場預測 + 8  強名單
  Phase 4: #97–#100 8強單場預測 + 4  強名單
  Phase 5: #101–#102 4強單場預測 + 決賽隊伍
  Phase 6: #103 季軍戰 + #104 決賽預測
- 開賽後採用「滾動式修正」：每一場真實結果出爐，即更新積分與模型狀態；
  若預測未命中，調整後重新預測該階段剩餘場次與下一階段對陣。

輸出：
- predictions/phase_predictions.json
- predictions/Phase_Prediction_Report.md
"""
import json
import csv
import re
from pathlib import Path
from datetime import datetime
from typing import Any

from advanced_predictor import ThreeVectorModel, PredictionResearch, load_json, save_json
from knockout_simulator import (
    KnockoutSimulator,
    load_annex_c,
    R32_FIXTURES,
    R16_FIXTURES,
    QF_FIXTURES,
    SF_FIXTURES,
    THIRD_PLACE,
    FINAL,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"
PHASE_OUTPUT = PREDICTIONS_DIR / "phase_predictions.json"
PHASE_REPORT = PREDICTIONS_DIR / "Phase_Prediction_Report.md"
MATCHES_PATH = DATA_DIR / "matches_104.json"
ANNEX_C_PATH = DATA_DIR / "third_place_combinations.csv"


PHASES = [
    {
        "id": 1,
        "name": "小組賽",
        "match_ids": list(range(1, 73)),
        "output": "round_of_32",
        "description": "預測 #1–#72 每場小組賽，計算積分排名，產出 32 強名單。",
    },
    {
        "id": 2,
        "name": "32 強",
        "match_ids": list(range(73, 89)),
        "output": "round_of_16",
        "description": "根據 32 強名單預測 #73–#88 每場，產出 16 強名單。",
    },
    {
        "id": 3,
        "name": "16 強",
        "match_ids": list(range(89, 97)),
        "output": "quarter_finals",
        "description": "根據 16 強名單預測 #89–#96 每場，產出 8 強名單。",
    },
    {
        "id": 4,
        "name": "8 強",
        "match_ids": list(range(97, 101)),
        "output": "semi_finals",
        "description": "根據 8 強名單預測 #97–#100 每場，產出 4 強名單。",
    },
    {
        "id": 5,
        "name": "4 強",
        "match_ids": list(range(101, 103)),
        "output": "finalists",
        "description": "根據 4 強名單預測 #101–#102 每場，產出決賽與季軍戰隊伍。",
    },
    {
        "id": 6,
        "name": "決賽 / 季軍戰",
        "match_ids": [103, 104],
        "output": "champion",
        "description": "預測 #103 季軍戰與 #104 決賽，產出冠軍、亞軍、季軍。",
    },
]


def _compute_group_standings(match_predictions: list[dict]) -> dict:
    """根據已賽/預測結果計算小組積分排名。"""
    groups = {}
    for p in match_predictions:
        g = p.get("group")
        if not g:
            continue
        if g not in groups:
            groups[g] = {}
        for team_key, team_name, score_key, opp_score_key in [
            ("home_team", p["home_team"], "predicted_home_score", "predicted_away_score"),
            ("away_team", p["away_team"], "predicted_away_score", "predicted_home_score"),
        ]:
            if team_name not in groups[g]:
                groups[g][team_name] = {
                    "team": team_name,
                    "played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "gf": 0, "ga": 0, "points": 0,
                }
            team = groups[g][team_name]
            team["played"] += 1
            gf = p.get(score_key, 0)
            ga = p.get(opp_score_key, 0)
            team["gf"] += gf
            team["ga"] += ga
            if gf > ga:
                team["wins"] += 1
                team["points"] += 3
            elif gf == ga:
                team["draws"] += 1
                team["points"] += 1
            else:
                team["losses"] += 1

    standings = {}
    for g, teams in groups.items():
        ranked = sorted(
            teams.values(),
            key=lambda t: (t["points"], t["gf"] - t["ga"], t["gf"]),
            reverse=True,
        )
        standings[g] = ranked
    return standings


def _build_round_of_32(standings: dict) -> dict:
    """產出 32 強名單（各組前兩名 + 8 支最佳第三名）。"""
    qualifiers = []
    third_places = []
    for g, ranked in standings.items():
        qualifiers.extend([t["team"] for t in ranked[:2]])
        if len(ranked) > 2:
            third = ranked[2].copy()
            third["group"] = g
            third_places.append(third)

    third_places_sorted = sorted(
        third_places,
        key=lambda t: (t["points"], t["gf"] - t["ga"], t["gf"]),
        reverse=True,
    )
    best_third = [t["team"] for t in third_places_sorted[:8]]
    qualifiers.extend(best_third)

    return {
        "qualified_teams": qualifiers,
        "third_place_ranking": third_places_sorted,
        "best_third_teams": best_third,
    }


class PhasePredictor:
    """
    分階段滾動預測器。
    現階段只產出 Phase 1（小組賽 #1–#72 + 32 強預測）。
    Phase 2–6 必須等到 32 強真實名單確定後才解鎖。
    開賽後可呼叫 rolling_update 根據真實結果滾動修正 Phase 1，
    當 Phase 1 全部確認後再解鎖 Phase 2。
    """

    # 命中評分規則：正確=1，和局命中=0.5，錯誤=-1
    SCORE_HIT = 1.0
    SCORE_DRAW_HIT = 0.5
    SCORE_MISS = -1.0

    def __init__(self, matches_path: Path = MATCHES_PATH, annex_path: Path = ANNEX_C_PATH):
        self.matches_data = load_json(matches_path)
        self.matches = {m["match_id"]: m for m in self.matches_data["matches"]}
        self.teams_data = load_json(DATA_DIR / "teams.json")
        self.teams_db = {t["name_zh"]: t for t in self.teams_data["teams"]}
        self.research = PredictionResearch()
        self.model = ThreeVectorModel(self.research, self.teams_db)
        self.annex_rows = load_annex_c(annex_path)

        # 預測結果池：match_id -> prediction dict
        self.predictions: dict[int, dict] = {}
        # 真實結果池：match_id -> {home_score, away_score}
        self.actual_results: dict[int, dict] = {}
        # 未命中記錄，用於滾動修正
        self.misses: list[dict] = []

        # 載入現有預測
        self._load_existing_predictions()

    def _load_existing_predictions(self):
        """載入 advanced_predictions.json 與 knockout_predictions.json 的預測。"""
        # 小組賽預測
        adv_path = PREDICTIONS_DIR / "advanced_predictions.json"
        if adv_path.exists():
            adv = load_json(adv_path)
            for p in adv.get("group_stage", {}).get("predictions", []):
                self.predictions[p["match_id"]] = p

        # 淘汰賽預測
        ko_path = PREDICTIONS_DIR / "knockout_predictions.json"
        if ko_path.exists():
            ko = load_json(ko_path)
            ko_result = ko.get("knockout", {})
            for key in ["round_of_32", "round_of_16", "quarter_finals", "semi_finals"]:
                for m in ko_result.get(key, []):
                    self.predictions[m["match_id"]] = m
            for m in [ko_result.get("third_place"), ko_result.get("final")]:
                if m:
                    self.predictions[m["match_id"]] = m

    def _predict_single_match(self, match_id: int) -> dict:
        """對單場比賽進行預測。"""
        if match_id in self.predictions:
            return self.predictions[match_id]

        m = self.matches[match_id]
        pred = self.model.predict(m["home_team"], m["away_team"])
        pred["match_id"] = match_id
        pred["stage"] = m.get("stage", "")
        pred["group"] = m.get("group")
        pred["home_team"] = m["home_team"]
        pred["away_team"] = m["away_team"]
        pred["date"] = m.get("date")
        pred["time_taiwan"] = m.get("time_taiwan")
        pred["city"] = m.get("city")
        pred["rolling_status"] = "predicted"
        self.predictions[match_id] = pred
        return pred

    def predict_phase_1(self) -> dict:
        """Phase 1: #1–#72 小組賽單場預測 + 32 強名單。"""
        match_preds = [self._predict_single_match(mid) for mid in PHASES[0]["match_ids"]]
        standings = _compute_group_standings(match_preds)
        round_of_32 = _build_round_of_32(standings)
        return {
            "matches": match_preds,
            "standings": standings,
            "round_of_32": round_of_32,
        }

    def predict_knockout_phases(self, group_stage_result: dict) -> dict:
        """Phase 2–6: 基於 32 強名單，逐場預測淘汰賽。"""
        simulator = KnockoutSimulator(group_stage_result, self.teams_db, self.model, seed=42)
        full = simulator.simulate_full_knockout(self.annex_rows)

        # 把淘汰賽結果標註到 predictions 池
        for key in ["round_of_32", "round_of_16", "quarter_finals", "semi_finals"]:
            for m in full.get(key, []):
                m["rolling_status"] = "predicted"
                self.predictions[m["match_id"]] = m
        for m in [full.get("third_place"), full.get("final")]:
            if m:
                m["rolling_status"] = "predicted"
                self.predictions[m["match_id"]] = m

        return full

    def predict_all_phases(self) -> dict:
        """
        產出 Phase 1 預測（小組賽 #1–#72 + 32 強）。
        Phase 2–6 不預測，因為在 32 強真實名單確定前不合理。
        """
        phase_1 = self.predict_phase_1()

        phases = [
            {
                **PHASES[0],
                "matches": phase_1["matches"],
                "standings": phase_1["standings"],
                "round_of_32": phase_1["round_of_32"],
            }
        ]

        # Phase 2–6 僅保留結構佔位，不填入預測
        for phase in PHASES[1:]:
            phases.append({
                **phase,
                "matches": [],
                "locked": True,
                "unlock_condition": "32 強真實名單確定後解鎖（Phase 1 全部確認）",
            })

        output = {
            "metadata": {
                "version": "phase-v1.1",
                "generated_at": datetime.now().isoformat(),
                "source": "engine/phase_predictor.py",
                "method": "three-vector-strategy + rolling-update",
                "note": "現階段僅預測 Phase 1（#1–#72 小組賽 + 32 強）。Phase 2–6 需等待 32 強真實名單確定後解鎖。",
                "scoring_rule": "預測正確=+1，和局命中=+0.5，錯誤=-1",
            },
            "phases": phases,
            "all_matches": [self.predictions[mid] for mid in sorted(self.predictions.keys()) if mid <= 72],
        }
        return output

    def unlock_phase_2(self, confirmed_round_of_32: list[str]) -> dict:
        """
        當 32 強真實名單確定後，解鎖 Phase 2（#73–#88）。
        輸入 confirmed_round_of_32: 32 支隊伍名稱。
        注意：此方法僅在 32 強名單確定後呼叫，現階段不實作完整推演。
        """
        raise NotImplementedError(
            "unlock_phase_2 需等待 32 強真實名單確定後實作。"
            "現階段請先使用 predict_all_phases() 產出 Phase 1。"
        )

    def _extract_teams_from_knockout(self, knockout: dict, next_key: str) -> list[str]:
        """從淘汰賽結果中提取下一輪隊伍名單。"""
        key_map = {
            "round_of_16": "round_of_32",
            "quarter_finals": "round_of_16",
            "semi_finals": "quarter_finals",
        }
        prev_key = key_map[next_key]
        return [m["winner"] for m in knockout.get(prev_key, [])]

    def rolling_update(self, match_id: int, home_score: int, away_score: int) -> dict:
        """
        滾動修正入口：輸入一場已完成的真實結果。
        1. 記錄真實結果。
        2. 比對預測勝方 vs 實際勝方。
        3. 若未命中，記錄 miss 並觸發該階段剩餘場次重新預測。
        4. 若該場為階段最後一場，重新計算下一階段對陣。
        目前實作：記錄 miss、標記需要重跑、回傳狀態。
        具體權重調整算法可後續擴充。
        """
        self.actual_results[match_id] = {"home_score": home_score, "away_score": away_score}
        pred = self.predictions.get(match_id)
        if not pred:
            return {"status": "no_prediction", "match_id": match_id}

        pred_home = pred.get("predicted_home_score", pred.get("home_score"))
        pred_away = pred.get("predicted_away_score", pred.get("away_score"))
        pred_winner = self._winner_from_score(pred_home, pred_away)
        actual_winner = self._winner_from_score(home_score, away_score)
        hit = pred_winner == actual_winner

        # 計分：正確=1，和局命中=0.5，錯誤=-1
        score = self.SCORE_HIT
        if actual_winner == "draw":
            score = self.SCORE_DRAW_HIT
        elif not hit:
            score = self.SCORE_MISS

        if not hit:
            self.misses.append({
                "match_id": match_id,
                "predicted": {"home": pred_home, "away": pred_away, "winner": pred_winner},
                "actual": {"home": home_score, "away": away_score, "winner": actual_winner},
                "reason": pred.get("reason"),
                "score": score,
            })

        # 標記該場為已確認
        pred["rolling_status"] = "confirmed"
        pred["actual_home_score"] = home_score
        pred["actual_away_score"] = away_score
        pred["hit"] = hit
        pred["score"] = score

        return {
            "status": "confirmed",
            "match_id": match_id,
            "hit": hit,
            "score": score,
            "predicted_winner": pred_winner,
            "actual_winner": actual_winner,
            "miss_count": len(self.misses),
        }

    @staticmethod
    def _winner_from_score(home_score: int, away_score: int) -> str | None:
        if home_score is None or away_score is None:
            return None
        if home_score > away_score:
            return "home"
        if away_score > home_score:
            return "away"
        return "draw"


def generate_report(output: dict, output_path: Path) -> None:
    """產生 Markdown 格式的分階段預測報告。現階段只顯示 Phase 1。"""
    meta = output["metadata"]
    lines = [
        "# 2026 FIFA 世界盃 分階段滾動預測報告",
        "",
        f"- **產生時間**：{meta['generated_at']}",
        f"- **方法論**：{meta['method']}",
        "- **階段**：6 階段（小組賽 → 32強 → 16強 → 8強 → 4強 → 決賽/季軍戰）",
        f"- **版本**：{meta['version']}",
        f"- **備註**：{meta['note']}",
        f"- **計分規則**：{meta['scoring_rule']}",
        "",
        "---",
        "",
    ]

    for phase in output["phases"]:
        lines.extend([
            f"## Phase {phase['id']}：{phase['name']}",
            "",
            f"{phase['description']}",
            "",
        ])

        if phase.get("locked"):
            lines.append(
                f"🔒 **本階段已鎖定**：{phase['unlock_condition']}"
            )
            lines.append("")
            continue

        lines.append("### 單場預測")
        lines.append("")
        for m in phase["matches"]:
            home = m["home_team"]
            away = m["away_team"]
            hs = m.get("predicted_home_score", m.get("home_score"))
            aw = m.get("predicted_away_score", m.get("away_score"))
            hwp = m.get("home_win_prob")
            dwp = m.get("draw_prob")
            awp = m.get("away_win_prob")
            winner = m.get("winner")
            # 小組賽沒有 winner 欄位，根據預測比數判斷
            if winner is None:
                if hs > aw:
                    winner = home
                elif aw > hs:
                    winner = away
                else:
                    winner = "和局"
            label = "結果" if phase["id"] == 6 else "勝方" if phase["id"] > 1 else "預測勝方"
            lines.append(
                f"- **第 {m['match_id']} 場**：{home} {hs} - {aw} {away} "
                f"→ {label}：**{winner}** "
                f"(勝率 {hwp}% / 和 {dwp}% / 客勝 {awp}%)"
            )
            lines.append(f"  - 理由：{m.get('reason', '')}")
            lines.append("")

        if "standings" in phase:
            lines.append("### 小組積分排名")
            lines.append("")
            for g, ranked in sorted(phase["standings"].items()):
                lines.append(f"- **{g} 組**：")
                for i, t in enumerate(ranked, 1):
                    lines.append(
                        f"  {i}. {t['team']} — {t['points']} 分 / 淨勝 {t['gf']-t['ga']} / 進 {t['gf']} 失 {t['ga']}"
                    )
                lines.append("")

        if "round_of_32" in phase:
            r32 = phase["round_of_32"]
            lines.append("### 32 強晉級名單")
            lines.append("")
            lines.append(f"- 各組前兩名 + 8 支最佳第三名，共 {len(r32['qualified_teams'])} 隊")
            lines.append(f"- 最佳第三名：{', '.join(r32['best_third_teams'])}")
            lines.append("")

        if "round_of_16" in phase:
            lines.append("### 16 強晉級名單")
            lines.append("")
            lines.append(f"- {', '.join(phase['round_of_16'])}")
            lines.append("")

        if "quarter_finals" in phase:
            lines.append("### 8 強晉級名單")
            lines.append("")
            lines.append(f"- {', '.join(phase['quarter_finals'])}")
            lines.append("")

        if "semi_finals" in phase:
            lines.append("### 4 強晉級名單")
            lines.append("")
            lines.append(f"- {', '.join(phase['semi_finals'])}")
            lines.append("")

        if "finalists" in phase:
            f = phase["finalists"]
            lines.append("### 決賽 / 季軍戰隊伍")
            lines.append("")
            lines.append(f"- 決賽：{f['final'][0]} vs {f['final'][1]}")
            lines.append(f"- 季軍戰：{f['third_place'][0]} vs {f['third_place'][1]}")
            lines.append("")

        if "champion" in phase:
            lines.append("### 🏆 最終結果")
            lines.append("")
            lines.append(f"| 名次 | 球隊 |")
            lines.append(f"|:--:|:--:|")
            lines.append(f"| 冠軍 | {phase['champion']} |")
            lines.append(f"| 亞軍 | {phase['runner_up']} |")
            lines.append(f"| 季軍 | {phase['third_place_team']} |")
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    print("[PhasePredictor] 載入賽程與現有預測...")
    predictor = PhasePredictor()

    print("[PhasePredictor] 產出 Phase 1 預測（小組賽 #1–#72 + 32 強）...")
    output = predictor.predict_all_phases()

    save_json(PHASE_OUTPUT, output)
    generate_report(output, PHASE_REPORT)

    print(f"[PhasePredictor] JSON 已儲存：{PHASE_OUTPUT}")
    print(f"[PhasePredictor] 報告已儲存：{PHASE_REPORT}")
    print("[PhasePredictor] Phase 2–6 已鎖定，等待 32 強真實名單確定後解鎖。")


if __name__ == "__main__":
    main()
