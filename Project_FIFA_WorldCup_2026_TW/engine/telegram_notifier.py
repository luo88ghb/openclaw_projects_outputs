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


def send_telegram(message: str) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def notify_upcoming(minutes_ahead: int = 30):
    now = datetime.now()
    matches = load_matches()
    upcoming = []
    for m in matches:
        if m.get("status") == "finished":
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
            pred_text = f"\n🔮 預測比分：{pred['home_score_pred']}-{pred['away_score_pred']}"
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


def notify_results():
    """發送剛結束比賽的賽果與預測命中情況。"""
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
        pred = m.get("prediction")
        hit_text = ""
        if pred:
            hit = pred.get("hit")
            hit_text = f"\n🔮 賽前預測：{pred['home_score_pred']}-{pred['away_score_pred']} {'✅ 命中' if hit else '❌ 未命中'}" if hit is not None else f"\n🔮 賽前預測：{pred['home_score_pred']}-{pred['away_score_pred']}"
        msg = (
            f"⚽ <b>2026 世界盃賽果</b>\n"
            f"場次：#{m['match_id']} {m['stage']}{' ' + m['group'] + '組' if m['group'] else ''}\n"
            f"對戰：{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}\n"
            f"地點：{m['city']}"
            f"{hit_text}"
        )
        send_telegram(msg)
        print(f"Notified result for match {m['match_id']}")


if __name__ == "__main__":
    notify_upcoming()
