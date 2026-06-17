"""
Time-correction scheduler for FIFA World Cup 2026 auto-updates.

Scans matches_104.json against Asia/Taipei (UTC+8) current time.
Triggers an update at: match kickoff time + 120 minutes.
On trigger:
  1. Generate pre-match prediction for the match if not already set.
  2. Scrape Wikipedia for the match result.
  3. If no score yet, retry every 5 minutes up to 60 minutes.
  4. Update matches_104.json with score/status.
  5. Mark match with a `scrape_checked` flag so historic backfill can skip it.
  6. Check prediction hit.
  7. Notify dashboard via SSE and Telegram.
  8. Compute next trigger from the next upcoming match + 120 minutes.

On startup, an automatic backfill scans all matches whose trigger time has
passed and that are not yet marked as checked/finished, then attempts to
fetch their results from Wikipedia.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# Allow importing sibling engine modules
BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = BASE_DIR / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from worldcup_engine import WorldCupEngine
from telegram_notifier import notify_match_result
from wiki_scraper import get_match_result

DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"
SSE_CLIENTS_FILE = PREDICTIONS_DIR / "sse_clients.json"

# SSE notification endpoint URL
SSE_NOTIFY_URL = "http://localhost:8765/notify-update"

# Retry configuration when Wikipedia has no score yet
RETRY_DELAY_SECONDS = 300  # 5 minutes
MAX_RETRY_MINUTES = 60


def load_matches_data():
    path = DATA_DIR / "matches_104.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_matches_data(data: dict):
    path = DATA_DIR / "matches_104.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def taipei_now():
    """Return current naive datetime in Asia/Taipei (UTC+8)."""
    return datetime.now()


def match_datetime(m: dict) -> datetime:
    return datetime.strptime(f"{m['date']} {m['time_taiwan']}", "%Y-%m-%d %H:%M")


def trigger_time(m: dict) -> datetime:
    """Kickoff time + 120 minutes."""
    return match_datetime(m) + timedelta(minutes=120)


def find_next_trigger(matches: list) -> tuple[dict | None, datetime | None]:
    """
    Find the next match that has not finished and whose trigger time is in the future.
    Returns (match, trigger_time). If none, returns (None, None).
    """
    now = taipei_now()
    candidates = []
    for m in matches:
        if m.get("status") == "finished":
            continue
        if m.get("home_score") is not None and m.get("away_score") is not None:
            continue
        if m.get("scrape_checked"):
            continue
        t = trigger_time(m)
        if t > now:
            candidates.append((t, m))
    if not candidates:
        return None, None
    candidates.sort()
    return candidates[0][1], candidates[0][0]


def find_backfill_matches(matches: list) -> list[dict]:
    """
    Return all matches whose trigger time has passed, are not finished,
    and have not been scrape-checked yet. Sorted by kickoff time ascending.
    """
    now = taipei_now()
    result = []
    for m in matches:
        if m.get("status") == "finished":
            continue
        if m.get("home_score") is not None and m.get("away_score") is not None:
            continue
        if m.get("scrape_checked"):
            continue
        t = trigger_time(m)
        if t <= now:
            result.append((t, m))
    result.sort()
    return [m for _, m in result]


def notify_dashboard():
    """Ping the dashboard server to push an SSE update."""
    try:
        urllib.request.urlopen(SSE_NOTIFY_URL, timeout=5)
    except Exception as e:
        print(f"SSE notify failed: {e}", flush=True)


def set_match_checked(engine: WorldCupEngine, m: dict) -> None:
    """Mark a match as scrape-checked so it won't be re-scraped by backfill."""
    match = engine.get_match(m["match_id"])
    match["scrape_checked"] = True
    engine._save_matches()


def process_match(engine: WorldCupEngine, m: dict, retry_until_score: bool = True) -> dict:
    """
    Scrape result and update a single match.
    Returns a short summary for logging/Telegram.
    """
    match_id = m["match_id"]

    # 1. Ensure pre-match prediction exists
    if not m.get("prediction"):
        engine.set_prediction(match_id)
        print(f"[Scheduler] Generated pre-match prediction for match {match_id}", flush=True)

    # 2. Scrape Wikipedia
    result = get_match_result(
        m["home_team"], m["away_team"], m["date"], m["time_taiwan"]
    )

    # 3. Retry loop if Wikipedia has no score yet
    if result["home_score"] is None and retry_until_score:
        deadline = taipei_now() + timedelta(minutes=MAX_RETRY_MINUTES)
        while result["home_score"] is None and taipei_now() < deadline:
            print(
                f"[Scheduler] Match {match_id}: 維基百科尚未公布比分，"
                f"{RETRY_DELAY_SECONDS // 60} 分鐘後重試...",
                flush=True,
            )
            time.sleep(RETRY_DELAY_SECONDS)
            result = get_match_result(
                m["home_team"], m["away_team"], m["date"], m["time_taiwan"]
            )

    # 4. Mark checked regardless of whether score was found.
    set_match_checked(engine, m)

    if result["home_score"] is None:
        return {
            "match_id": match_id,
            "updated": False,
            "message": f"Match {match_id}: 維基百科尚未公布比分，已標記為檢查過。",
        }

    # 5. Update score and check prediction
    engine.update_score(match_id, result["home_score"], result["away_score"])
    pred = engine.check_prediction(match_id)

    hit_text = ""
    if pred:
        hit = pred.get("hit")
        hit_text = f" {'✅ 命中' if hit else '❌ 未命中'}"

    # 6. Telegram notification
    try:
        notify_match_result(m)
    except Exception as e:
        print(f"[Scheduler] Telegram send failed: {e}", flush=True)

    # 7. Push dashboard update
    notify_dashboard()

    return {
        "match_id": match_id,
        "updated": True,
        "message": f"Match {match_id}: 更新 {m['home_team']} {result['home_score']}-{result['away_score']} {m['away_team']}{hit_text}",
    }


def run_backfill(engine: WorldCupEngine) -> None:
    """Backfill historic matches on startup."""
    backfill = find_backfill_matches(engine.matches)
    if not backfill:
        print("[Scheduler] No historic matches need backfill.", flush=True)
        return

    print(f"[Scheduler] Backfill: {len(backfill)} past match(es) to check.", flush=True)
    for m in backfill:
        print(f"[Scheduler] Backfill match {m['match_id']}...", flush=True)
        summary = process_match(engine, m, retry_until_score=False)
        print(f"[Scheduler] {summary['message']}", flush=True)


def run_scheduler():
    print("[Scheduler] Time-correction scheduler started (Asia/Taipei UTC+8)", flush=True)
    engine = WorldCupEngine()

    # Startup backfill: catch up any missed historic matches
    run_backfill(engine)

    while True:
        engine = WorldCupEngine()  # reload data each cycle
        matches = engine.matches

        next_match, next_t = find_next_trigger(matches)
        if next_match is None or next_t is None:
            print("[Scheduler] No more upcoming matches. Sleeping 1 hour.", flush=True)
            time.sleep(3600)
            continue

        wait_seconds = (next_t - taipei_now()).total_seconds()
        if wait_seconds > 0:
            print(
                f"[Scheduler] Next trigger: match {next_match['match_id']} "
                f"at {next_t.strftime('%Y-%m-%d %H:%M')} "
                f"(kickoff {next_match['date']} {next_match['time_taiwan']} +120min). "
                f"Sleeping {int(wait_seconds)}s.",
                flush=True,
            )
            time.sleep(wait_seconds)

        # Re-evaluate after sleep in case data was updated externally
        engine = WorldCupEngine()
        next_match = engine.get_match(next_match["match_id"])
        if next_match.get("status") == "finished":
            print(f"[Scheduler] Match {next_match['match_id']} already finished. Skipping.", flush=True)
            continue

        print(f"[Scheduler] Triggering update for match {next_match['match_id']}...", flush=True)
        summary = process_match(engine, next_match, retry_until_score=True)
        print(f"[Scheduler] {summary['message']}", flush=True)


if __name__ == "__main__":
    run_scheduler()
