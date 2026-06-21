import sys, json
from pathlib import Path
ENGINE = Path(__file__).resolve().parent / "engine"
sys.path.insert(0, str(ENGINE))
from worldcup_engine import WorldCupEngine
engine = WorldCupEngine()
print("| 場次 | 主隊 | 比分 | 客隊 | 預測 | hit | score |")
print("|------|------|------|------|------|-----|-------|")
for m in engine.matches:
    if m.get("status") != "finished":
        continue
    p = engine.check_prediction(m["match_id"])
    print(f"| #{m['match_id']} | {m['home_team']} | {m['home_score']}-{m['away_score']} | {m['away_team']} | {p['home_score_pred']}-{p['away_score_pred']} | {p['hit']} | {p.get('score')} |")
