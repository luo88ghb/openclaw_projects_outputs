"""
Score Updater - World Cup 2026 Live Score Calibration Tool
==========================================================
校正時間工具：追蹤已過期比賽的比分資料。

規則：
- 每場比賽以台灣時間（Asia/Taipei UTC+8）的開賽時間為基準。
- 開賽後 2 小時視為比賽結束觸發點（正規 90 分鐘 + 中場休息 + 補時）。
- 對於 status 不為 'finished' 且已超過 2 小時的比賽：
  - 嘗試從外部來源抓取最新比分（預留 fetch_live_score 接口）。
  - 若無外部來源，則標記為 "需人工確認" 並等待人工輸入。
  - 取得比分後更新 matches_104.json、比對預測結果（hit/miss）。
- 提供手動輸入入口 update_score(match_id, home_score, away_score)。

用法：
    python engine/score_updater.py           # 自動檢查並更新
    python engine/score_updater.py --dry-run # 只檢查，不寫檔
    python engine/score_updater.py --manual 15 2 1  # 手動更新單場比分
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 讓 engine 目錄可被 import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from worldcup_engine import WorldCupEngine, save_json, DATA_DIR

TAIPEI_TZ = timezone(timedelta(hours=8))


def taipei_now():
    """回傳目前的台灣時間。"""
    return datetime.now(tz=TAIPEI_TZ)


def kickoff_dt(match):
    """將 match 的 date + time_taiwan 轉為台灣時間 datetime。"""
    return datetime.strptime(
        f"{match['date']} {match['time_taiwan']}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=TAIPEI_TZ)


def should_update(match, now=None):
    """判斷這場比賽是否已經到了該更新的時機（開賽後 2 小時且尚未完成）。"""
    if match.get("status") == "finished":
        return False
    if match.get("home_score") is not None and match.get("away_score") is not None:
        return False
    now = now or taipei_now()
    return now >= kickoff_dt(match) + timedelta(hours=2)


def fetch_live_score(match_id):
    """
    從外部來源抓取最新比分。
    目前為預留接口，未來可接 FIFA API 或第三方體育資料源。
    回傳 (home_score, away_score) 或 None。
    """
    # TODO: 接入外部 API / 網頁爬蟲
    return None


def check_hit(prediction, home_score, away_score):
    """比對預測與實際結果，回傳是否命中勝方。"""
    if not prediction:
        return None
    pred_home = prediction.get("home_score_pred")
    pred_away = prediction.get("away_score_pred")
    if pred_home is None or pred_away is None:
        return None

    pred_winner = "home" if pred_home > pred_away else "away" if pred_away > pred_home else "draw"
    actual_winner = "home" if home_score > away_score else "away" if away_score > home_score else "draw"
    return pred_winner == actual_winner


def resolve_score(match, dry_run=False):
    """
    嘗試取得比賽比分。優先使用外部來源，若無則標記為待人工確認。
    回傳 dict：{ 'updated': bool, 'home_score': int|None, 'away_score': int|None, 'source': str }
    """
    result = fetch_live_score(match["match_id"])
    if result is not None:
        home_score, away_score = result
        return {
            "updated": True,
            "home_score": home_score,
            "away_score": away_score,
            "source": "live_api",
        }
    return {
        "updated": False,
        "home_score": None,
        "away_score": None,
        "source": "pending_manual",
    }


def run_calibration(dry_run=False, now=None):
    """執行一次校正掃描。"""
    engine = WorldCupEngine()
    now = now or taipei_now()
    due_matches = [m for m in engine.matches if should_update(m, now)]

    if not due_matches:
        print(f"[{now.isoformat()}] 沒有需要更新的比賽。")
        return []

    results = []
    for m in due_matches:
        result = resolve_score(m, dry_run=dry_run)
        if result["updated"] and result["home_score"] is not None:
            if not dry_run:
                engine.update_score(m["match_id"], result["home_score"], result["away_score"])
                # 比對預測命中狀態
                match = engine.get_match(m["match_id"])
                hit = check_hit(match.get("prediction"), result["home_score"], result["away_score"])
                if match.get("prediction"):
                    match["prediction"]["hit"] = hit
                    engine._save_matches()
            results.append({
                "match_id": m["match_id"],
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                "home_score": result["home_score"],
                "away_score": result["away_score"],
                "source": result["source"],
                "dry_run": dry_run,
            })
            print(
                f"[{'DRY-RUN ' if dry_run else ''}UPDATED] "
                f"#{m['match_id']} {m['home_team']} {result['home_score']} - {result['away_score']} {m['away_team']}"
            )
        else:
            results.append({
                "match_id": m["match_id"],
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                "status": "pending_manual",
                "kickoff": kickoff_dt(m).isoformat(),
            })
            print(
                f"[PENDING] #{m['match_id']} {m['home_team']} vs {m['away_team']} "
                f"開賽於 {kickoff_dt(m).isoformat()}，等待人工輸入比分"
            )

    return results


def manual_update(match_id, home_score, away_score):
    """手動更新單場比分，並同步比對預測結果。"""
    engine = WorldCupEngine()
    match = engine.update_score(match_id, home_score, away_score)
    hit = check_hit(match.get("prediction"), home_score, away_score)
    if match.get("prediction"):
        match["prediction"]["hit"] = hit
        engine._save_matches()
    status_text = "[OK] 預測命中" if hit else ("[X] 預測未中" if hit is False else "[-] 無預測")
    print(
        f"[MANUAL UPDATED] #{match['match_id']} "
        f"{match['home_team']} {match['home_score']} - {match['away_score']} {match['away_team']} | {status_text}"
    )
    return match


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="World Cup 2026 Score Calibration Tool")
    parser.add_argument("--dry-run", action="store_true", help="只檢查不寫檔")
    parser.add_argument("--manual", nargs=3, metavar=("MATCH_ID", "HOME", "AWAY"), help="手動更新單場比分")
    args = parser.parse_args()

    if args.manual:
        manual_update(int(args.manual[0]), int(args.manual[1]), int(args.manual[2]))
    else:
        run_calibration(dry_run=args.dry_run)
