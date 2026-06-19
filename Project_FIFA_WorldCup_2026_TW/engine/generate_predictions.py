"""
Generate pre-match predictions for all scheduled matches without prediction.
Run once or on demand to backfill missing predictions.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "engine"))

from worldcup_engine import WorldCupEngine


def main():
    engine = WorldCupEngine()
    count = 0

    for m in engine.matches:
        if m.get("status") == "finished":
            continue
        if m.get("prediction"):
            continue
        # Only generate for scheduled matches
        if m.get("status") != "scheduled":
            continue

        print(f"Generating prediction for match {m['match_id']}: {m['home_team']} vs {m['away_team']}")
        pred = engine.set_prediction(m["match_id"])
        print(f"  -> {pred['home_score_pred']}-{pred['away_score_pred']} | {pred['reason']}")
        count += 1

    if count == 0:
        print("All scheduled matches already have predictions.")
    else:
        print(f"Generated predictions for {count} matches.")


if __name__ == "__main__":
    main()