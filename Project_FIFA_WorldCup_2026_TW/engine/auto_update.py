"""
Auto-update pipeline.
1. Scrape match results from trusted sources.
2. Update matches_104.json with scores.
3. Update prediction vectors in predictions_db.json.
4. Regenerate stage predictions.
5. Send Telegram summary.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "engine"))

from worldcup_engine import WorldCupEngine
from scraper import WorldCupScraper


def auto_update():
    engine = WorldCupEngine()
    scraper = WorldCupScraper()

    print("[auto_update] Start collecting results...")
    collection = scraper.collect_recent_results()
    scraper.save_raw_collection(collection)
    print(f"[auto_update] Collected {collection['count']} results")

    updated = 0
    for match_id, score in collection["results"].items():
        try:
            match = engine.update_score(int(match_id), score["home_score"], score["away_score"])
            print(f"[auto_update] Updated match {match_id}: {match['home_team']} {score['home_score']} - {score['away_score']} {match['away_team']}")
            updated += 1
        except Exception as e:
            print(f"[auto_update] Failed to update match {match_id}: {e}")

    # Regenerate predictions for each stage
    stages = ["小組賽", "32強", "16強", "8強", "4強", "冠亞季軍"]
    for stage in stages:
        engine.generate_stage_predictions(stage)
        print(f"[auto_update] Regenerated {stage} predictions")

    # Auto-predict upcoming matches
    upcoming_preds = engine.auto_predictions_for_upcoming(48)
    print(f"[auto_update] Auto-predicted {len(upcoming_preds)} upcoming matches")

    print(f"[auto_update] Done. Updated {updated} matches.")
    return updated


if __name__ == "__main__":
    auto_update()
