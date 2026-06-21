"""
重新計算已結束場次的預測命中狀態。
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def calculate_hit(pred, home_score, away_score):
    """計算預測命中狀態和得分（使用預測機率最高的結果判定）。

    規則（與儀表板 / engine 一致）：
    - 主勝 / 和局 / 客勝 三種預測機率取最高者為預測結果。
    - 實際結果與預測結果一致 -> hit=True, score=+1
    - 不一致 -> hit=False, score=-1
    比數預測不再納入計分。
    """
    probs = {
        "home": float(pred.get("home_win_prob", 0) or 0),
        "draw": float(pred.get("draw_prob", 0) or 0),
        "away": float(pred.get("away_win_prob", 0) or 0),
    }
    predicted_outcome = max(probs, key=probs.get)

    if home_score > away_score:
        actual_outcome = "home"
    elif home_score == away_score:
        actual_outcome = "draw"
    else:
        actual_outcome = "away"

    hit = predicted_outcome == actual_outcome
    score = 1 if hit else -1
    return hit, score, predicted_outcome, actual_outcome

def main():
    with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
        matches_data = json.load(f)
    
    changes = 0
    
    for m in matches_data["matches"]:
        if m.get("status") != "finished":
            continue
        
        if m.get("home_score") is None or m.get("away_score") is None:
            continue
        
        if "prediction" not in m:
            continue
        
        hit, score, predicted_outcome, actual_outcome = calculate_hit(m["prediction"], m["home_score"], m["away_score"])
        
        old_hit = m["prediction"].get("hit")
        old_score = m["prediction"].get("score")
        
        if hit != old_hit or score != old_score:
            m["prediction"]["hit"] = hit
            m["prediction"]["score"] = score
            m["prediction"]["predicted_outcome"] = predicted_outcome
            m["prediction"]["actual_outcome"] = actual_outcome
            print(f"#{m['match_id']} {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']}: "
                  f"預測:{predicted_outcome} 實際:{actual_outcome} "
                  f"hit: {old_hit}->{hit}, score: {old_score}->{score}")
            changes += 1
    
    if changes > 0:
        with open(DATA_DIR / "matches_104.json", "w", encoding="utf-8") as f:
            json.dump(matches_data, f, ensure_ascii=False, indent=2)
        print(f"\n已更新 {changes} 場預測命中狀態")
    else:
        print("所有已結束場次的預測命中狀態已正確")

if __name__ == "__main__":
    main()