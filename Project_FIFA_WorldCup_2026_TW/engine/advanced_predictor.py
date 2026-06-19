"""
engine/advanced_predictor.py
進階版 2026 FIFA 世界盃預測引擎

設計原則：
- 完全獨立於主系統，不影響 worldcup_engine.py / scheduler.py
- 輸入：data/teams.json, data/matches_104.json
- 輸出：predictions/advanced_predictions.json
- 分階段推演：先完成小組賽 72 場，產出 32 強後再繼續淘汰賽
- 所有預測必須基於 search 工具搜集的真實資料

作者：Zeni (OpenClaw)
日期：2026-06-18
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 資料路徑
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PREDICTION_OUTPUT = PREDICTIONS_DIR / "advanced_predictions.json"
RESEARCH_CACHE = CACHE_DIR / "prediction_research_cache.json"
MEMORY_FILE = PREDICTIONS_DIR / "prediction_memory.md"


def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_cache() -> dict:
    if not RESEARCH_CACHE.exists():
        return {}
    try:
        with open(RESEARCH_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache: dict) -> None:
    with open(RESEARCH_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def append_memory(note: str) -> None:
    """模擬持久化記憶複利：將發現的模式寫入 prediction_memory.md。"""
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat()
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n---\n[{timestamp}]\n{note}\n")


class PredictionResearch:
    """
    資料搜集層。
    負責用搜尋工具補充各隊最新狀態、傷病、戰術、賠率等資料。
    所有資料會快取到 cache/prediction_research_cache.json，避免重複搜尋。
    """

    def __init__(self):
        self.cache = load_cache()

    def get_team_research(self, team_name: str, team_en: str) -> dict:
        """取得單一球隊的研究資料，優先從快取讀取，沒有才搜尋。"""
        key = f"team:{team_name}"
        if key in self.cache:
            return self.cache[key]

        # 初始資料結構
        research = {
            "team_name": team_name,
            "team_en": team_en,
            "fifa_ranking": None,
            "squad_value": None,
            "recent_tournaments": [],
            "injuries": [],
            "tactics": {
                "style": None,
                "formation": None,
                "strengths": [],
                "weaknesses": []
            },
            "head_to_head": {},
            "external_factors": {
                "home_advantage": False,
                "climate_adaptation": None,
                "travel_burden": None
            },
            "odds": {},
            "sources": [],
            "searched_at": None
        }

        # 暫時先標記為待搜尋，實際搜尋由外部 search 工具完成後回填
        self.cache[key] = research
        save_cache(self.cache)
        return research

    def update_team_research(self, team_name: str, updates: dict) -> dict:
        """外部搜尋工具回填資料用。"""
        key = f"team:{team_name}"
        if key not in self.cache:
            self.cache[key] = {"team_name": team_name}
        self.cache[key].update(updates)
        self.cache[key]["searched_at"] = datetime.now().isoformat()
        save_cache(self.cache)
        return self.cache[key]

    def get_match_research(self, home: str, away: str) -> dict:
        """取得單一比賽對戰資料。"""
        key = f"match:{home}_vs_{away}"
        if key in self.cache:
            return self.cache[key]
        return {"head_to_head": None, "odds": None}

    def update_match_research(self, home: str, away: str, updates: dict) -> dict:
        key = f"match:{home}_vs_{away}"
        if key not in self.cache:
            self.cache[key] = {}
        self.cache[key].update(updates)
        self.cache[key]["searched_at"] = datetime.now().isoformat()
        save_cache(self.cache)
        return self.cache[key]

    def get_all_teams(self) -> dict:
        """回傳所有已快取的研究資料。"""
        return {k: v for k, v in self.cache.items() if k.startswith("team:")}


class ThreeVectorModel:
    """
    三視角評分模型。
    Vector_A：量化數據 (40%)
    Vector_B：戰術相剋 (35%)
    Vector_C：外部變數 (25%)
    """

    WEIGHTS = {
        "A": 0.40,
        "B": 0.35,
        "C": 0.25
    }

    def __init__(self, research: PredictionResearch, teams_db: dict):
        self.research = research
        self.teams_db = teams_db  # name_zh -> team info

    def _vector_a_quantitative(self, home: dict, away: dict, home_r: dict, away_r: dict) -> tuple[float, float]:
        """
        量化視角：FIFA排名、身價、近期賽事成績、攻防數據。
        分數範圍：0 ~ 1
        """
        # FIFA 排名差距：排名越低（數字越大）越弱
        home_rank = home.get("fifa_ranking", 100)
        away_rank = away.get("fifa_ranking", 100)
        rank_diff = away_rank - home_rank  # 正數表示主隊排名較高
        rank_score_home = 0.5 + (rank_diff / 200.0)
        rank_score_home = max(0.1, min(0.9, rank_score_home))
        rank_score_away = 1.0 - rank_score_home

        # 身價差距（資料可用時）
        home_value = home_r.get("squad_value") or 0
        away_value = away_r.get("squad_value") or 0
        if home_value + away_value > 0:
            value_score_home = home_value / (home_value + away_value)
            value_score_away = 1.0 - value_score_home
        else:
            value_score_home = 0.5
            value_score_away = 0.5

        # 近期賽事積分（資料可用時）
        home_recent = home_r.get("recent_tournaments", [])
        away_recent = away_r.get("recent_tournaments", [])
        home_form = self._parse_recent_form(home_recent)
        away_form = self._parse_recent_form(away_recent)
        form_total = home_form + away_form
        if form_total > 0:
            form_score_home = home_form / form_total
            form_score_away = away_form / form_total
        else:
            form_score_home = 0.5
            form_score_away = 0.5

        # 綜合
        home_score = (rank_score_home * 0.5 + value_score_home * 0.2 + form_score_home * 0.3)
        away_score = (rank_score_away * 0.5 + value_score_away * 0.2 + form_score_away * 0.3)

        # 正規化
        total = home_score + away_score
        if total == 0:
            return 0.5, 0.5
        return home_score / total, away_score / total

    def _parse_recent_form(self, recent_tournaments: list) -> float:
        """簡化解析近期成績，回傳 0~100 的狀態分數。"""
        if not recent_tournaments:
            return 50.0
        total = 0.0
        count = 0
        for t in recent_tournaments:
            result = t.get("result", "")
            if "冠軍" in result or "winner" in result.lower():
                total += 90
            elif "亞軍" in result or "finalist" in result.lower():
                total += 80
            elif "四強" in result or "semifinal" in result.lower():
                total += 70
            elif "八強" in result or "quarterfinal" in result.lower():
                total += 60
            elif "十六強" in result or "round of 16" in result.lower():
                total += 50
            elif "小組出局" in result or "group" in result.lower():
                total += 30
            else:
                total += 45
            count += 1
        return total / max(count, 1)

    def _vector_b_tactical(self, home: dict, away: dict, home_r: dict, away_r: dict) -> tuple[float, float]:
        """
        戰術視角：教練體系、陣型對位、歷史交手。
        """
        # 教練體系對位：簡化為風格標籤評分
        home_tactics = home_r.get("tactics", {})
        away_tactics = away_r.get("tactics", {})
        home_style = home_tactics.get("style", "balanced")
        away_style = away_tactics.get("style", "balanced")
        home_score, away_score = self._style_matchup(home_style, away_style)

        # 陣型對位：暫時簡化為平衡值
        home_formation = home_tactics.get("formation", "4-3-3")
        away_formation = away_tactics.get("formation", "4-3-3")
        # 更複雜的陣型剋制可後續擴充
        formation_score = 0.5

        # 歷史交手
        h2h = home_r.get("head_to_head", {}).get(away.get("name_zh"), {})
        if h2h:
            home_wins = h2h.get("home_wins", 0)
            away_wins = h2h.get("away_wins", 0)
            draws = h2h.get("draws", 0)
            total = home_wins + away_wins + draws
            if total > 0:
                h2h_home = (home_wins + draws * 0.5) / total
                h2h_away = (away_wins + draws * 0.5) / total
            else:
                h2h_home = 0.5
                h2h_away = 0.5
        else:
            h2h_home = 0.5
            h2h_away = 0.5

        final_home = (home_score * 0.4 + formation_score * 0.2 + h2h_home * 0.4)
        final_away = (away_score * 0.4 + (1 - formation_score) * 0.2 + h2h_away * 0.4)

        total = final_home + final_away
        if total == 0:
            return 0.5, 0.5
        return final_home / total, final_away / total

    def _style_matchup(self, home_style: str, away_style: str) -> tuple[float, float]:
        """簡化風格剋制矩陣。"""
        styles = ["possession", "counter_attack", "high_press", "defensive", "balanced"]
        home_style = home_style.lower() if home_style else "balanced"
        away_style = away_style.lower() if away_style else "balanced"

        # 簡單剋制表：攻擊型 > 防守型 > 傳控 > 防反 > 高位逼搶
        matchup = {
            "possession": {"counter_attack": -0.1, "defensive": 0.05, "high_press": -0.05},
            "counter_attack": {"high_press": 0.1, "possession": 0.1, "defensive": -0.05},
            "high_press": {"possession": 0.05, "counter_attack": -0.1, "defensive": 0.05},
            "defensive": {"counter_attack": 0.05, "high_press": -0.05, "possession": -0.05},
            "balanced": {}
        }

        home_bonus = matchup.get(home_style, {}).get(away_style, 0.0)
        away_bonus = matchup.get(away_style, {}).get(home_style, 0.0)

        home_score = 0.5 + home_bonus - away_bonus
        home_score = max(0.1, min(0.9, home_score))
        return home_score, 1.0 - home_score

    def _parse_odds(self, odds_value, default: float = 2.5) -> float:
        """將賠率轉換為 decimal odds。支援英式 x-y、純數字、美式 +/-。"""
        if odds_value is None:
            return default
        if isinstance(odds_value, (int, float)):
            return float(odds_value)
        s = str(odds_value).strip()
        if not s:
            return default
        # 英式 x-y (profit:stake, decimal = x + y)
        if "-" in s:
            parts = s.replace("/", "-").split("-")
            if len(parts) == 2:
                try:
                    x, y = float(parts[0]), float(parts[1])
                    if x >= 0 and y > 0:
                        return x + y
                except ValueError:
                    pass
        # 美式 +/-
        if s.startswith("+"):
            try:
                v = float(s[1:])
                return v / 100 + 1 if v > 0 else default
            except ValueError:
                pass
        if s.startswith("-"):
            try:
                v = float(s[1:])
                return 100 / v + 1 if v > 0 else default
            except ValueError:
                pass
        # 純數字
        try:
            return float(s)
        except ValueError:
            return default

    def _vector_c_external(self, home: dict, away: dict, home_r: dict, away_r: dict) -> tuple[float, float]:
        """
        外部變數：北美主客場效應、氣候、博彩賠率、旅行負荷。
        """
        home_ext = home_r.get("external_factors", {})
        away_ext = away_r.get("external_factors", {})

        # 主場優勢
        home_adv = 1.0 if home_ext.get("home_advantage") else 0.0
        away_adv = 1.0 if away_ext.get("home_advantage") else 0.0

        # 氣候適應度
        home_climate = home_ext.get("climate_adaptation", 50) or 50
        away_climate = away_ext.get("climate_adaptation", 50) or 50

        # 博彩賠率（分別使用主客隊各自的奪冠賠率作為實力 proxy）
        home_odds = self._parse_odds(home_r.get("odds", {}).get("win"), 2.5)
        away_odds = self._parse_odds(away_r.get("odds", {}).get("win"), 2.5)
        odds_home_score = away_odds / (home_odds + away_odds)
        odds_away_score = home_odds / (home_odds + away_odds)

        # 旅行負荷（數字越大負擔越重，反而越不利；所以取 100 - travel 作為有利分數）
        home_travel = home_ext.get("travel_burden", 50) or 50
        away_travel = away_ext.get("travel_burden", 50) or 50
        travel_total = (100 - home_travel) + (100 - away_travel)
        if travel_total > 0:
            travel_home = (100 - home_travel) / travel_total
            travel_away = (100 - away_travel) / travel_total
        else:
            travel_home = 0.5
            travel_away = 0.5

        final_home = (home_adv * 0.25 + (home_climate / 100) * 0.20 + odds_home_score * 0.35 + travel_home * 0.20)
        final_away = (away_adv * 0.25 + (away_climate / 100) * 0.20 + odds_away_score * 0.35 + travel_away * 0.20)

        total = final_home + final_away
        if total == 0:
            return 0.5, 0.5
        return final_home / total, final_away / total

    def predict(self, home_name: str, away_name: str) -> dict:
        """對單場比賽進行三視角預測。"""
        home = self.teams_db.get(home_name, {})
        away = self.teams_db.get(away_name, {})
        home_r = self.research.get_team_research(home_name, home.get("name_en", ""))
        away_r = self.research.get_team_research(away_name, away.get("name_en", ""))

        a_home, a_away = self._vector_a_quantitative(home, away, home_r, away_r)
        b_home, b_away = self._vector_b_tactical(home, away, home_r, away_r)
        c_home, c_away = self._vector_c_external(home, away, home_r, away_r)

        # 加權綜合
        home_score = (
            a_home * self.WEIGHTS["A"] +
            b_home * self.WEIGHTS["B"] +
            c_home * self.WEIGHTS["C"]
        )
        away_score = (
            a_away * self.WEIGHTS["A"] +
            b_away * self.WEIGHTS["B"] +
            c_away * self.WEIGHTS["C"]
        )

        # 加入和局機率：實力接近時和局機率上升
        score_diff = abs(home_score - away_score)
        draw_base = 0.18
        draw_factor = max(0, 0.25 - score_diff * 0.5)
        draw_prob_raw = draw_base + draw_factor

        # 正規化勝率
        remaining = 1.0 - draw_prob_raw
        total = home_score + away_score
        home_win_prob = remaining * (home_score / total) if total > 0 else remaining * 0.5
        away_win_prob = remaining * (away_score / total) if total > 0 else remaining * 0.5

        # 轉換為最可能比分
        expected_home_goals = self._expected_goals(home_score, away_score, is_home=True)
        expected_away_goals = self._expected_goals(away_score, home_score, is_home=False)

        return {
            "home_win_prob": round(home_win_prob * 100),
            "draw_prob": round(draw_prob_raw * 100),
            "away_win_prob": round(away_win_prob * 100),
            "predicted_home_score": round(expected_home_goals),
            "predicted_away_score": round(expected_away_goals),
            "vector_breakdown": {
                "A": {"home": round(a_home, 3), "away": round(a_away, 3)},
                "B": {"home": round(b_home, 3), "away": round(b_away, 3)},
                "C": {"home": round(c_home, 3), "away": round(c_away, 3)}
            },
            "reason": self._build_reason(home_name, away_name, home_r, away_r, a_home, b_home, c_home)
        }

    def _expected_goals(self, team_score: float, opponent_score: float, is_home: bool) -> float:
        """根據綜合實力差距預測進球數。"""
        base = 1.1
        advantage = 0.25 if is_home else 0.0
        diff = team_score - opponent_score
        return max(0.3, base + advantage + diff * 2.0)

    def _build_reason(self, home_name: str, away_name: str, home_r: dict, away_r: dict,
                      a_home: float, b_home: float, c_home: float) -> str:
        """產生可解釋的預測理由。"""
        factors = []
        home_rank = home_r.get("fifa_ranking")
        away_rank = away_r.get("fifa_ranking")
        if home_rank and away_rank:
            factors.append(f"FIFA排名 {home_rank} vs {away_rank}")

        home_style = home_r.get("tactics", {}).get("style")
        away_style = away_r.get("tactics", {}).get("style")
        if home_style and away_style:
            factors.append(f"戰術風格 {home_style} vs {away_style}")

        if home_r.get("external_factors", {}).get("home_advantage"):
            factors.append(f"{home_name} 具北美主場優勢")
        if away_r.get("external_factors", {}).get("home_advantage"):
            factors.append(f"{away_name} 具北美主場優勢")

        dominant_vector = max([("A", a_home), ("B", b_home), ("C", c_home)], key=lambda x: x[1])
        vector_label = {"A": "量化數據", "B": "戰術相剋", "C": "外部變數"}[dominant_vector[0]]
        factors.append(f"主要優勢來自{vector_label}")

        return "；".join(factors) if factors else "基於綜合三視角評分"


class GroupStageSimulator:
    """
    小組賽推演器。
    根據預測結果計算積分、淨勝球、產出 32 強名單。
    """

    def __init__(self, matches: list, teams_db: dict, model: ThreeVectorModel):
        self.matches = [m for m in matches if m.get("stage") == "小組賽"]
        self.teams_db = teams_db
        self.model = model
        self.predictions = []

    def simulate(self) -> dict:
        """推演全部小組賽並產出排名。"""
        for m in self.matches:
            pred = self.model.predict(m["home_team"], m["away_team"])
            self.predictions.append({
                "match_id": m["match_id"],
                "stage": m["stage"],
                "group": m["group"],
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                **pred
            })

        # 計算小組積分
        standings = self._compute_standings()

        # 產出 32 強名單
        round_of_32 = self._build_round_of_32(standings)

        return {
            "predictions": self.predictions,
            "standings": standings,
            "round_of_32": round_of_32
        }

    def _compute_standings(self) -> dict:
        """計算 12 個小組的積分排名。"""
        groups = {}
        for p in self.predictions:
            g = p["group"]
            if g not in groups:
                groups[g] = {}
            for team_key, team_name, score_key, opp_score_key in [
                ("home_team", p["home_team"], "predicted_home_score", "predicted_away_score"),
                ("away_team", p["away_team"], "predicted_away_score", "predicted_home_score")
            ]:
                if team_name not in groups[g]:
                    groups[g][team_name] = {
                        "team": team_name,
                        "played": 0, "wins": 0, "draws": 0, "losses": 0,
                        "gf": 0, "ga": 0, "points": 0
                    }
                team = groups[g][team_name]
                team["played"] += 1
                gf = p[score_key]
                ga = p[opp_score_key]
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

        # 排名
        standings = {}
        for g, teams in groups.items():
            ranked = sorted(
                teams.values(),
                key=lambda t: (t["points"], t["gf"] - t["ga"], t["gf"]),
                reverse=True
            )
            standings[g] = ranked
        return standings

    def _build_round_of_32(self, standings: dict) -> dict:
        """產出 32 強名單（各組前兩名 + 8 支最佳第三名）。"""
        qualifiers = []
        third_places = []
        for g, ranked in standings.items():
            qualifiers.extend([t["team"] for t in ranked[:2]])
            if len(ranked) > 2:
                third = ranked[2].copy()
                third["group"] = g
                third_places.append(third)

        # 選出 8 支最佳第三名
        third_places_sorted = sorted(
            third_places,
            key=lambda t: (t["points"], t["gf"] - t["ga"], t["gf"]),
            reverse=True
        )
        best_third = [t["team"] for t in third_places_sorted[:8]]
        qualifiers.extend(best_third)

        return {
            "qualified_teams": qualifiers,
            "third_place_ranking": third_places_sorted,
            "best_third_teams": best_third
        }


class AdvancedPredictor:
    """
    進階預測控制器。
    負責載入資料、執行研究、分階段推演、輸出結果。
    """

    def __init__(self, scope: str = "group_stage"):
        self.scope = scope
        self.matches_data = load_json(DATA_DIR / "matches_104.json")
        self.teams_data = load_json(DATA_DIR / "teams.json")
        self.matches = self.matches_data["matches"]
        self.teams_db = {t["name_zh"]: t for t in self.teams_data["teams"]}
        self.research = PredictionResearch()
        self.model = ThreeVectorModel(self.research, self.teams_db)

    def run(self) -> dict:
        """執行預測流程。"""
        print(f"[AdvancedPredictor] Scope={self.scope}, starting...")

        if self.scope == "group_stage":
            simulator = GroupStageSimulator(self.matches, self.teams_db, self.model)
            result = simulator.simulate()
            output = {
                "metadata": {
                    "version": "advanced-v1.0",
                    "generated_at": datetime.now().isoformat(),
                    "source": "engine/advanced_predictor.py",
                    "scope": "group_stage",
                    "total_matches": 72,
                    "method": "three-vector-strategy",
                    "note": "小組賽 72 場預測，產出 32 強名單。淘汰賽需等待真實或預測小組賽結果後再推演。"
                },
                "group_stage": result
            }
        else:
            raise NotImplementedError("目前僅支援 group_stage 推演")

        # 儲存結果
        save_json(PREDICTION_OUTPUT, output)
        print(f"[AdvancedPredictor] Saved to {PREDICTION_OUTPUT}")

        # 記憶複利
        append_memory(f"完成小組賽 72 場推演，產出 32 強名單共 {len(output['group_stage']['round_of_32']['qualified_teams'])} 隊。")

        return output


def main():
    predictor = AdvancedPredictor(scope="group_stage")
    result = predictor.run()
    print(f"[AdvancedPredictor] Completed. Qualified teams: {len(result['group_stage']['round_of_32']['qualified_teams'])}")


if __name__ == "__main__":
    main()
