import sys
from pathlib import Path
ENGINE = Path(__file__).resolve().parent / "engine"
sys.path.insert(0, str(ENGINE))
from worldcup_engine import WorldCupEngine

engine = WorldCupEngine()
for mid in (1,2,3,4,5,29,30,31):
    m = engine.get_match(mid)
    pred = engine.check_prediction(mid)
    print(f"M{mid}: {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']} pred={pred['home_score_pred']}-{pred['away_score_pred']} hit={pred['hit']} score={pred.get('score')}")
