"""
Project_FIFA_WorldCup_2026_TW Engine
- 載入 104 場賽程資料
- 提供分組積分計算、賽果更新、預測比對
- 可被 dashboard 與通知腳本共用
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from .elo_model import predict_by_name
except ImportError:
    from elo_model import predict_by_name

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"


def load_json(filename: str) -> dict | list:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def load_feedback_weights() -> dict:
    """載入用戶對 L1/L2 的反饋獎懲，回傳 {match_id: {l1: float, l2: float}}。"""
    path = DATA_DIR / "user_model_feedback.json"
    if not path.exists():
        return {}
    try:
        data = load_json(str(path.relative_to(DATA_DIR)))
    except Exception:
        return {}
    weights = {}
    for entry in data.get("feedback", []):
        mid = entry.get("match_id")
        model = str(entry.get("model", "")).lower()
        fb = entry.get("feedback")
        if mid is None or model not in ("l1", "l2") or not isinstance(fb, (int, float)):
            continue
        weights.setdefault(mid, {})[model] = float(fb)
    return weights


def get_model_weight_for_match(match_id: int, model: str, weights: dict | None = None) -> float:
    """取得指定場次與模型的用戶反饋權重；無反饋時返回 0.0。"""
    if weights is None:
        weights = load_feedback_weights()
    return weights.get(match_id, {}).get(model, 0.0)


def save_json(filename: str, data: Any) -> None:
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_predictions_db() -> dict:
    path = PREDICTIONS_DIR / "predictions_db.json"
    if not path.exists():
        return {
            "team_vectors": {},
            "player_vectors": {},
            "match_results": [],
            "stage_predictions": {},
            "last_updated": None
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_predictions_db(db: dict) -> None:
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = PREDICTIONS_DIR / "predictions_db.json"
    db["last_updated"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


class WorldCupEngine:
    def __init__(self):
        self.matches_data = load_json("matches_104.json")
        self.teams_data = load_json("teams.json")
        self.matches = self.matches_data["matches"]
        self.teams = {t["name_zh"]: t for t in self.teams_data["teams"]}
        self.predictions_db = load_predictions_db()
        self.feedback_weights = load_feedback_weights()

    def get_match(self, match_id: int) -> dict:
        for m in self.matches:
            if m["match_id"] == match_id:
                return m
        raise ValueError(f"Match {match_id} not found")

    def update_score(self, match_id: int, home_score: int, away_score: int) -> dict:
        match = self.get_match(match_id)
        match["home_score"] = home_score
        match["away_score"] = away_score
        match["status"] = "finished"
        self._save_matches()
        self._record_match_result(match)
        return match

    def _save_matches(self):
        save_json("matches_104.json", self.matches_data)

    def _record_match_result(self, match: dict):
        """比賽結束後將結果寫入預測資料庫，用於滾動更新預測模型。"""
        db = self.predictions_db
        entry = {
            "match_id": match["match_id"],
            "date": match["date"],
            "stage": match["stage"],
            "group": match.get("group"),
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "home_score": match["home_score"],
            "away_score": match["away_score"],
            "recorded_at": datetime.now().astimezone().isoformat()
        }
        # 避免重複寫入
        db["match_results"] = [r for r in db["match_results"] if r["match_id"] != match["match_id"]]
        db["match_results"].append(entry)
        self._update_team_vectors(match)
        save_predictions_db(db)

    def _update_team_vectors(self, match: dict):
        """根據比賽結果更新隊伍向量（滾動預測用）。"""
        db = self.predictions_db
        for team_key, team_name in [("home_team", match["home_team"]), ("away_team", match["away_team"])]:
            if team_name not in db["team_vectors"]:
                db["team_vectors"][team_name] = {
                    "matches_played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "attack_score": 50.0,
                    "defense_score": 50.0,
                    "form_score": 50.0,
                    "overall": 50.0
                }
            vec = db["team_vectors"][team_name]
            is_home = team_key == "home_team"
            gf = match["home_score"] if is_home else match["away_score"]
            ga = match["away_score"] if is_home else match["home_score"]
            vec["matches_played"] += 1
            vec["goals_for"] += gf
            vec["goals_against"] += ga
            if gf > ga:
                vec["wins"] += 1
            elif gf == ga:
                vec["draws"] += 1
            else:
                vec["losses"] += 1

            # 簡單向量更新：攻擊 + 防守 + 狀態
            vec["attack_score"] = min(99, vec["attack_score"] + (gf - 1) * 1.5)
            vec["defense_score"] = min(99, vec["defense_score"] + (2 - ga) * 1.5)
            win_rate = vec["wins"] / vec["matches_played"] if vec["matches_played"] else 0
            vec["form_score"] = 40 + win_rate * 60
            vec["overall"] = round((vec["attack_score"] + vec["defense_score"] + vec["form_score"]) / 3, 1)

    def predict_match(self, match_id: int, model: str = "l1") -> dict:
        """賽前預測。model='l1' 使用 FIFA 排名模型；model='l2' 使用 Elo 模型。
        若用戶對該場次有反饋，正/負反饋會微調最終比數預測（+1/-1 對應 ±0.5 球，+0.5/-0.5 對應 ±0.25 球）。"""
        match = self.get_match(match_id)
        home_name = match["home_team"]
        away_name = match["away_team"]
        fb = get_model_weight_for_match(match_id, model, self.feedback_weights)
        adjustment = fb * 0.5  # +1 -> +0.5 goals, -1 -> -0.5 goals

        if model == "l2":
            elo_probs = predict_by_name(home_name, away_name)
            if elo_probs:
                home_rank = self.teams.get(home_name, {}).get("fifa_ranking", 100)
                away_rank = self.teams.get(away_name, {}).get("fifa_ranking", 100)
                home_expected = max(0.5, 1.0 + (100 - home_rank) * 0.02 + elo_probs["home"] * 1.5 - 0.75)
                away_expected = max(0.5, 1.0 + (100 - away_rank) * 0.02 + elo_probs["away"] * 1.5 - 0.75)
                home_score_pred = round(home_expected + adjustment)
                away_score_pred = round(away_expected - adjustment)
                home_win_prob = round(elo_probs["home"] * 100)
                draw_prob = round(elo_probs["draw"] * 100)
                away_win_prob = round(elo_probs["away"] * 100)
                return {
                    "match_id": match_id,
                    "home_team": home_name,
                    "away_team": away_name,
                    "home_score_pred": home_score_pred,
                    "away_score_pred": away_score_pred,
                    "home_win_prob": home_win_prob,
                    "draw_prob": draw_prob,
                    "away_win_prob": away_win_prob,
                    "reason": f"L2 Elo 模型 ({home_name} vs {away_name})"
                }
            # fallthrough to l1 if Elo data missing

        home = self.teams.get(home_name, {})
        away = self.teams.get(away_name, {})
        home_vec = self.predictions_db["team_vectors"].get(home_name, {"overall": 50, "attack_score": 50, "defense_score": 50})
        away_vec = self.predictions_db["team_vectors"].get(away_name, {"overall": 50, "attack_score": 50, "defense_score": 50})

        # 基礎分數：FIFA 排名 + 隊伍向量
        home_rank = home.get("fifa_ranking", 100)
        away_rank = away.get("fifa_ranking", 100)
        rank_factor = (away_rank - home_rank) * 0.3
        vector_factor = (home_vec["overall"] - away_vec["overall"]) * 0.5
        home_advantage = 3.0  # 主場優勢

        home_expected = max(0.5, 1.2 + (rank_factor + vector_factor + home_advantage) / 30)
        away_expected = max(0.5, 1.0 + (-rank_factor - vector_factor) / 30)

        home_score_pred = round(home_expected + adjustment)
        away_score_pred = round(away_expected - adjustment)

        # 勝率估計
        total = home_expected + away_expected + 0.5
        home_win_prob = round(home_expected / total * 100)
        away_win_prob = round(away_expected / total * 100)
        draw_prob = max(0, 100 - home_win_prob - away_win_prob)

        return {
            "match_id": match_id,
            "home_team": home_name,
            "away_team": away_name,
            "home_score_pred": home_score_pred,
            "away_score_pred": away_score_pred,
            "home_win_prob": home_win_prob,
            "draw_prob": draw_prob,
            "away_win_prob": away_win_prob,
            "reason": f"基於 FIFA 排名({home_rank} vs {away_rank}) 與累積向量({home_vec['overall']} vs {away_vec['overall']})"
        }

    def set_prediction(self, match_id: int, home_pred: int = None, away_pred: int = None, reason: str = "", model: str = "l1") -> dict:
        if home_pred is None or away_pred is None:
            pred = self.predict_match(match_id, model=model)
            home_pred = pred["home_score_pred"]
            away_pred = pred["away_score_pred"]
            reason = pred["reason"]
        match = self.get_match(match_id)
        match["prediction"] = {
            "home_score_pred": home_pred,
            "away_score_pred": away_pred,
            "home_win_prob": pred.get("home_win_prob", 0),
            "draw_prob": pred.get("draw_prob", 0),
            "away_win_prob": pred.get("away_win_prob", 0),
            "reason": reason,
            "model": model,
            "hit": None
        }
        self._save_matches()
        return match["prediction"]

    def check_prediction(self, match_id: int) -> dict | None:
        """
        統一計分邏輯：以預測機率最高的結果為權威預測，不需要命中比分。
        - 主勝 / 和局 / 客勝 三種預測機率取最高者為預測結果。
        - 實際結果與預測結果一致 -> hit=True, score=+1
        - 不一致 -> hit=False, score=-1
        比數預測僅供參考，不納入計分。
        """
        match = self.get_match(match_id)
        pred = match.get("prediction")
        if not pred or match.get("home_score") is None:
            return None
        actual_hs = int(match["home_score"])
        actual_aw = int(match["away_score"])

        # 預測結果：機率最高者（回退到比數預測勝方）
        probs = {
            "home": float(pred.get("home_win_prob", 0) or 0),
            "draw": float(pred.get("draw_prob", 0) or 0),
            "away": float(pred.get("away_win_prob", 0) or 0),
        }
        # 若機率全為 0，回退到比數預測判斷勝方
        if sum(probs.values()) == 0:
            hs = pred.get("home_score_pred") if pred.get("home_score_pred") is not None else pred.get("predicted_home_score")
            aw = pred.get("away_score_pred") if pred.get("away_score_pred") is not None else pred.get("predicted_away_score")
            if hs is not None and aw is not None:
                if hs > aw:
                    probs["home"] = 1
                elif aw > hs:
                    probs["away"] = 1
                else:
                    probs["draw"] = 1
        predicted_outcome = max(probs, key=probs.get)

        # 實際結果
        if actual_hs > actual_aw:
            actual_outcome = "home"
        elif actual_hs == actual_aw:
            actual_outcome = "draw"
        else:
            actual_outcome = "away"

        hit = predicted_outcome == actual_outcome
        score = 1.0 if hit else -1.0

        pred["hit"] = hit
        pred["score"] = score
        pred["predicted_outcome"] = predicted_outcome
        pred["actual_outcome"] = actual_outcome
        match["hit"] = hit
        match["score"] = score
        self._save_matches()
        return pred

    def check_all_finished_predictions(self) -> dict:
        """對所有已結束且尚未正確計分的場次重新執行 check_prediction。"""
        updated = 0
        for m in self.matches:
            if m.get("status") != "finished":
                continue
            if m.get("home_score") is None or m.get("away_score") is None:
                continue
            pred = m.get("prediction")
            if not pred:
                continue
            # 如果已經有完整且一致的計分結果則跳過
            if (
                pred.get("hit") is not None
                and pred.get("score") is not None
                and pred.get("predicted_outcome") is not None
                and pred.get("actual_outcome") is not None
            ):
                continue
            self.check_prediction(m["match_id"])
            updated += 1
        self._save_matches()
        return {"updated": updated}

    def generate_stage_predictions(self, stage: str) -> dict:
        """產生各階段預測，寫入 predictions_db。"""
        db = self.predictions_db
        if stage == "小組賽":
            result = self._predict_group_stage(db)
        elif stage == "32強":
            result = self._predict_32_stage(db)
        elif stage == "16強":
            result = self._predict_16_stage(db)
        elif stage == "8強":
            result = self._predict_8_stage(db)
        elif stage == "4強":
            result = self._predict_4_stage(db)
        elif stage == "冠亞季軍":
            result = self._predict_finals(db)
        else:
            result = {}
        db["stage_predictions"][stage] = result
        save_predictions_db(db)
        return result

    def _predict_group_stage(self, db: dict) -> dict:
        groups = {}
        for m in self.matches:
            if m.get("group"):
                groups.setdefault(m["group"], []).append(m)
        result = {}
        for g, matches in groups.items():
            standings = self.group_standings(g)
            result[g] = [
                {
                    "rank": i + 1,
                    "team": s["team"],
                    "flag": self.teams.get(s["team"], {}).get("flag", ""),
                    "pts": s["pts"],
                    "prob": round(80 - i * 25, 1)
                }
                for i, s in enumerate(standings)
            ]
        return result

    def _get_top_teams(self, n: int) -> list[dict]:
        all_teams = list(self.teams.values())
        # 綜合 FIFA 排名 + 已累積向量
        scored = []
        for t in all_teams:
            name = t["name_zh"]
            rank = t.get("fifa_ranking", 100)
            vec = self.predictions_db["team_vectors"].get(name, {"overall": 50})
            overall = vec.get("overall", 50)
            score = overall * 0.6 + (100 - rank) * 0.4
            scored.append({"team": name, "flag": t.get("flag", ""), "rank": rank, "score": round(score, 1)})
        scored.sort(key=lambda x: -x["score"])
        return scored[:n]

    def _predict_32_stage(self, db: dict) -> dict:
        return {"qualified": self._get_top_teams(32)}

    def _predict_16_stage(self, db: dict) -> dict:
        return {"qualified": self._get_top_teams(16)}

    def _predict_8_stage(self, db: dict) -> dict:
        return {"qualified": self._get_top_teams(8)}

    def _predict_4_stage(self, db: dict) -> dict:
        return {"qualified": self._get_top_teams(4)}

    def _predict_finals(self, db: dict) -> dict:
        top3 = self._get_top_teams(3)
        return {
            "champion": top3[0] if len(top3) > 0 else None,
            "runner_up": top3[1] if len(top3) > 1 else None,
            "third_place": top3[2] if len(top3) > 2 else None
        }

    def group_standings(self, group: str) -> list[dict]:
        matches = [m for m in self.matches if m.get("group") == group]
        standings = {}
        for m in matches:
            for team_key in ("home_team", "away_team"):
                team = m[team_key]
                if team not in standings:
                    standings[team] = {"team": team, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
        for m in matches:
            home, away = m["home_team"], m["away_team"]
            hs = m.get("home_score")
            aws = m.get("away_score")
            if hs is None or aws is None:
                continue
            standings[home]["gf"] += hs
            standings[home]["ga"] += aws
            standings[away]["gf"] += aws
            standings[away]["ga"] += hs
            standings[home]["p"] += 1
            standings[away]["p"] += 1
            if hs > aws:
                standings[home]["w"] += 1
                standings[home]["pts"] += 3
                standings[away]["l"] += 1
            elif hs == aws:
                standings[home]["d"] += 1
                standings[away]["d"] += 1
                standings[home]["pts"] += 1
                standings[away]["pts"] += 1
            else:
                standings[away]["w"] += 1
                standings[away]["pts"] += 3
                standings[home]["l"] += 1
        return sorted(standings.values(), key=lambda x: (-x["pts"], -(x["gf"]-x["ga"]), x["team"]))

    def upcoming_matches(self, hours: int = 24) -> list[dict]:
        now = datetime.now()
        result = []
        for m in self.matches:
            if m.get("status") == "finished":
                continue
            dt = datetime.strptime(f"{m['date']} {m['time_taiwan']}", "%Y-%m-%d %H:%M")
            if now <= dt <= now + timedelta(hours=hours):
                result.append(m)
        return result

    def auto_predictions_for_upcoming(self, hours: int = 48) -> list[dict]:
        """為即將到來的比賽自動產生預測。"""
        predictions = []
        for m in self.upcoming_matches(hours):
            if m.get("prediction"):
                continue
            pred = self.set_prediction(m["match_id"])
            predictions.append(pred)
        return predictions

    def ensure_all_predictions(self) -> list[dict]:
        """為所有尚未產生預測且未結束的比賽建立賽前基礎預測。"""
        predictions = []
        for m in self.matches:
            if m.get("status") == "finished":
                continue
            if m.get("prediction"):
                continue
            pred = self.set_prediction(m["match_id"])
            predictions.append(pred)
        return predictions


if __name__ == "__main__":
    engine = WorldCupEngine()
    print("總場次:", len(engine.matches))
    # 啟動時校正所有已結束場次計分
    result = engine.check_all_finished_predictions()
    if result.get("updated"):
        print("已重新校正場次:", result["updated"])
    print("下一場內即將開賽:", engine.upcoming_matches(48))
