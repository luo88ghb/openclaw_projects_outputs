"""
Telegram notification sender for World Cup 2026.
Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment.
"""
import os
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"


def load_matches():
    with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
        return json.load(f)["matches"]


def load_phase_predictions():
    """載入分階段進階預測（權威預測來源）。"""
    path = PREDICTIONS_DIR / "phase_predictions.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_prediction_for_match(match_id: int) -> dict:
    """取得指定場次的進階預測；若無則回退到 matches_104.json 內的舊預測。"""
    phase_data = load_phase_predictions()
    for m in phase_data.get("all_matches", []):
        if m.get("match_id") == match_id:
            return m
    # 回退
    for m in load_matches():
        if m.get("match_id") == match_id and m.get("prediction"):
            return m["prediction"]
    return {}


def send_telegram(message: str, token: str = None, chat_id: str = None, parse_mode: str = "HTML") -> dict:
    if token is None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if chat_id is None:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# 向後相容：預設使用環境變數的發送入口
def send_telegram_default(message: str) -> dict:
    return send_telegram(message)


def notify_upcoming(minutes_ahead: int = 30, match_id: int = None):
    now = datetime.now()
    matches = load_matches()
    upcoming = []
    for m in matches:
        if m.get("status") == "finished":
            continue
        if match_id is not None and m["match_id"] != match_id:
            continue
        dt = datetime.strptime(f"{m['date']} {m['time_taiwan']}", "%Y-%m-%d %H:%M")
        delta = (dt - now).total_seconds() / 60
        if 0 <= delta <= minutes_ahead:
            upcoming.append((m, delta))

    if not upcoming:
        print(f"No matches in the next {minutes_ahead} minutes.")
        return

    for m, _ in upcoming:
        pred_text = ""
        if m.get("prediction"):
            pred = m["prediction"]
            winner = m["home_team"] if pred["home_win_prob"] >= pred["away_win_prob"] else m["away_team"]
            winner_prob = max(pred["home_win_prob"], pred["away_win_prob"])
            pred_text = f"\n🔮 預測：{winner} 勝 {winner_prob}%"
        msg = (
            f"⚽ <b>2026 世界盃開賽提醒</b>\n"
            f"場次：#{m['match_id']} {m['stage']}{' ' + m['group'] + '組' if m['group'] else ''}\n"
            f"時間：{m['date']} {m['time_taiwan']} (台灣時間)\n"
            f"對戰：{m['home_team']} vs {m['away_team']}\n"
            f"地點：{m['city']}"
            f"{pred_text}\n"
            f"收看：Hami Video / ELTA.tv"
        )
        send_telegram(msg)
        print(f"Notified match {m['match_id']}")


def daily_briefing():
    """每日 08:00 發送當天賽程摘要。"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    matches = load_matches()
    today_matches = [m for m in matches if m["date"] == today and m.get("status") != "finished"]
    tomorrow_matches = [m for m in matches if m["date"] == tomorrow and m.get("status") != "finished"]

    if not today_matches and not tomorrow_matches:
        print("No matches today or tomorrow.")
        return

    lines = ["⚽ <b>2026 世界盃每日賽程摘要</b>\n"]
    if today_matches:
        lines.append("<b>今天（{today}）</b>\n")
        for m in today_matches:
            lines.append(f"• {m['time_taiwan']} {m['home_team']} vs {m['away_team']} ({m['stage']}{' ' + m['group'] + '組' if m['group'] else ''})")
        lines.append("")
    if tomorrow_matches:
        lines.append(f"<b>明天（{tomorrow}）</b>\n")
        for m in tomorrow_matches:
            lines.append(f"• {m['time_taiwan']} {m['home_team']} vs {m['away_team']} ({m['stage']}{' ' + m['group'] + '組' if m['group'] else ''})")
        lines.append("")
    lines.append("收看：Hami Video / ELTA.tv")

    send_telegram("\n".join(lines))
    print("Daily briefing sent.")


def _winner_from_prediction(pred: dict) -> str:
    """根據預測機率最高的結果判斷預測勝方（與儀表板一致）。"""
    probs = {
        "主勝": float(pred.get("home_win_prob", 0) or 0),
        "和局": float(pred.get("draw_prob", 0) or 0),
        "客勝": float(pred.get("away_win_prob", 0) or 0),
    }
    if not any(probs.values()):
        # 回退：嘗試用比數預測判斷勝方（舊資料相容）
        hs = pred.get("home_score_pred") if pred.get("home_score_pred") is not None else pred.get("predicted_home_score")
        aw = pred.get("away_score_pred") if pred.get("away_score_pred") is not None else pred.get("predicted_away_score")
        if hs is None or aw is None:
            return "待預測"
        if hs > aw:
            return "主勝"
        if aw > hs:
            return "客勝"
        return "和局"
    return max(probs, key=probs.get)


def _score_prediction_hit(pred: dict, home_score: int, away_score: int) -> tuple[bool, float]:
    """
    統一計分規則（與儀表板一致）：
    - 預測機率最高的結果 == 實際結果 -> 命中，+1
    - 不同 -> 未命中，-1
    回傳 (是否命中, 得分)。
    """
    pred_winner = _winner_from_prediction(pred)
    if home_score > away_score:
        actual = "主勝"
    elif away_score > home_score:
        actual = "客勝"
    else:
        actual = "和局"

    hit = pred_winner == actual
    score = 1.0 if hit else -1.0
    return hit, score


def notify_daily_pre_match():
    """
    每天第一場開賽前 30 分鐘觸發：
    推播當天所有場次 + 預測勝隊。
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    matches = load_matches()
    today_matches = [
        m for m in matches
        if m["date"] == today and m.get("status") != "finished"
    ]
    if not today_matches:
        print(f"No matches today ({today}).")
        return

    today_matches.sort(key=lambda m: m["time_taiwan"])
    first_match = today_matches[0]
    first_dt = datetime.strptime(f"{first_match['date']} {first_match['time_taiwan']}", "%Y-%m-%d %H:%M")
    minutes_until_first = (first_dt - now).total_seconds() / 60

    # 只在第一場開賽前 0~30 分鐘內觸發一次
    if not (0 <= minutes_until_first <= 30):
        print(f"Not within 30 min window of first match ({minutes_until_first:.1f} min).")
        return

    lines = [f"⚽ <b>2026 世界盃今日賽程預告 ({today})</b>\n"]
    for m in today_matches:
        pred = _get_prediction_for_match(m["match_id"])
        pred_winner = _winner_from_prediction(pred)
        hs = pred.get("predicted_home_score", pred.get("home_score_pred", "?"))
        aw = pred.get("predicted_away_score", pred.get("away_score_pred", "?"))
        stage_label = f"{m['stage']}{' ' + m['group'] + '組' if m['group'] else ''}"
        lines.append(
            f"• #{m['match_id']} {m['time_taiwan']} {stage_label}\n"
            f"  {m['home_team']} vs {m['away_team']} @ {m['city']}\n"
            f"  🔮 預測：{m['home_team']} {hs} - {aw} {m['away_team']} → {pred_winner}"
        )
        lines.append("")

    lines.append("收看：Hami Video / ELTA.tv")
    send_telegram("\n".join(lines))
    print(f"Daily pre-match notification sent for {today} ({len(today_matches)} matches).")


def notify_daily_post_match():
    """
    當天最後一場結束後觸發：
    推播當天所有場次的真實比分 vs 預測結果。
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    matches = load_matches()
    today_matches = [m for m in matches if m["date"] == today]
    if not today_matches:
        print(f"No matches today ({today}).")
        return

    finished = [m for m in today_matches if m.get("status") == "finished"]
    if len(finished) != len(today_matches):
        print(f"Not all matches finished ({len(finished)}/{len(today_matches)}).")
        return

    lines = [f"⚽ <b>2026 世界盃今日賽果 ({today})</b>\n"]
    total_score = 0.0
    for m in finished:
        pred = _get_prediction_for_match(m["match_id"])
        hit, score = _score_prediction_hit(pred, m["home_score"], m["away_score"])
        total_score += score
        hs = pred.get("predicted_home_score", pred.get("home_score_pred", "?"))
        aw = pred.get("predicted_away_score", pred.get("away_score_pred", "?"))
        marker = "✅" if hit else "❌"
        if score == 1.0:
            marker = "✅"
        elif score == -1.0:
            marker = "❌"
        actual_score_text = f"{m['home_score']}-{m['away_score']}"
        pred_score_text = f"{hs}-{aw}"
        if score == 1.0:
            score_summary = "命中勝負方向"
        elif score == -1.0:
            score_summary = "未命中"
        else:
            score_summary = "未知"
        lines.append(
            f"• #{m['match_id']} {m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}\n"
            f"  🔮 預測：{pred_score_text} {marker} {score_summary}（得分：{score:+.1f}）"
        )
    lines.append("")
    lines.append(f"<b>今日預測總分：{total_score:+.1f}</b>")

    send_telegram("\n".join(lines))
    print(f"Daily post-match summary sent for {today} ({len(finished)} matches, score {total_score:+.1f}).")


def notify_match_result(m: dict):
    """發送單場比賽的賽果與預測命中情況（由 scheduler 觸發時呼叫）。"""
    pred = _get_prediction_for_match(m["match_id"])
    hit_text = ""
    if pred and m.get("home_score") is not None and m.get("away_score") is not None:
        hit, score = _score_prediction_hit(pred, m["home_score"], m["away_score"])
        hs = pred.get("predicted_home_score", pred.get("home_score_pred", "?"))
        aw = pred.get("predicted_away_score", pred.get("away_score_pred", "?"))
        marker = "✅" if hit else "❌"
        if score == 1.0:
            marker = "✅"
        elif score == -1.0:
            marker = "❌"
        if score == 1.0:
            score_summary = "命中勝負方向"
        elif score == -1.0:
            score_summary = "未命中"
        else:
            score_summary = "未知"
        winner = "和局" if m["home_score"] == m["away_score"] else (
            m["home_team"] if m["home_score"] > m["away_score"] else m["away_team"]
        )
        hit_text = f"\n🔮 預測：{hs}-{aw} {marker} {score_summary}（得分：{score:+.1f}） | 實際勝方：{winner}"
    msg = (
        f"⚽ <b>2026 世界盃賽果更新</b>\n"
        f"場次：#{m['match_id']} {m['stage']}{' ' + m['group'] + '組' if m['group'] else ''}\n"
        f"對戰：{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}\n"
        f"地點：{m['city']}"
        f"{hit_text}"
    )
    send_telegram(msg)
    print(f"Notified result for match {m['match_id']}")


def notify_results():
    """發送近 3 小時內結束比賽的賽果與預測命中情況（備用手動腳本入口）。"""
    now = datetime.now()
    matches = load_matches()
    recent = []
    for m in matches:
        if m.get("status") != "finished" or not m.get("home_score"):
            continue
        dt = datetime.strptime(f"{m['date']} {m['time_taiwan']}", "%Y-%m-%d %H:%M")
        if (now - dt).total_seconds() / 3600 <= 3:
            recent.append(m)

    if not recent:
        print("No recent finished matches.")
        return

    for m in recent:
        notify_match_result(m)


if __name__ == "__main__":
    notify_upcoming()
