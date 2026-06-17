"""
WorldCup 2026 Daily Briefing Cron Tool
- 載入 engine.worldcup_engine.WorldCupEngine
- 抓取接下來 24 小時內賽事
- 產生簡短預測理由與繁體中文 HTML 訊息
- 發送至 Telegram
- 更新 predictions/daily_briefing.md
"""
import sys
import os
from datetime import datetime
from pathlib import Path

# 將專案根目錄加入 path，以便 import engine
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from engine.worldcup_engine import WorldCupEngine
from engine.telegram_notifier import send_telegram

PROJECT_DIR = BASE_DIR
PREDICTIONS_DIR = PROJECT_DIR / "predictions"


def build_reason(pred: dict, home: dict, away: dict, city: str, home_name: str, db: dict = None) -> str:
    """產生一句簡短預測理由，依據 FIFA 排名/近期表現/主場因素。"""
    home_rank = home.get("fifa_ranking", 999)
    away_rank = away.get("fifa_ranking", 999)
    rank_diff = abs(home_rank - away_rank)
    away_name = away.get("name_zh", "")

    # 北美主場三國
    host_nations = {"墨西哥", "加拿大", "美國"}
    home_host = home_name in host_nations
    city_host = city in {"墨西哥城", "瓜達拉哈拉", "薩波潘", "蒙特雷", "多倫多", "溫哥華", "洛杉磯", "紐約", "邁阿密"}

    # 近期表現由 team_vectors 取得（若已有比賽結果）
    if db is None:
        db = WorldCupEngine().predictions_db
    home_vec = db.get("team_vectors", {}).get(home_name, {})
    away_vec = db.get("team_vectors", {}).get(away_name, {})
    home_overall = home_vec.get("overall", 50)
    away_overall = away_vec.get("overall", 50)

    reasons = []
    if home_host:
        reasons.append(f"{home_name} 坐擁北美主場優勢")
    if home_rank <= 20 and away_rank > 30:
        reasons.append(f"{home_name} FIFA 排名大幅領先（{home_rank} vs {away_rank}）")
    elif away_rank <= 20 and home_rank > 30:
        reasons.append(f"{away_name} FIFA 排名大幅領先（{away_rank} vs {home_rank}）")
    elif rank_diff >= 20:
        if home_rank < away_rank:
            reasons.append(f"{home_name} FIFA 排名明顯較高（{home_rank} vs {away_rank}）")
        else:
            reasons.append(f"{away_name} FIFA 排名明顯較高（{away_rank} vs {home_rank}）")

    if home_overall >= 65 and home_overall - away_overall >= 8:
        reasons.append(f"{home_name} 近期狀態火熱（向量評分 {home_overall}）")
    elif away_overall >= 65 and away_overall - home_overall >= 8:
        reasons.append(f"{away_name} 近期狀態火熱（向量評分 {away_overall}）")

    if not reasons:
        if home_rank < away_rank:
            reasons.append(f"雙方實力接近，{home_name} 排名略佔上風（{home_rank} vs {away_rank}）")
        else:
            reasons.append(f"雙方實力接近，{away_name} 排名略佔上風（{away_rank} vs {home_rank}）")

    return reasons[0] if reasons else "雙方實力接近，比賽難以預料。"


def generate_briefing(engine: WorldCupEngine) -> tuple[list[dict], str]:
    """
    回傳 (matches, html_message)
    若無賽事回傳空 list 與空字串
    """
    matches = engine.upcoming_matches(hours=24)
    if not matches:
        return [], ""

    # 確保每場都有預測
    for m in matches:
        if not m.get("prediction"):
            engine.set_prediction(m["match_id"])

    # 重新載入以取得更新後預測
    engine = WorldCupEngine()
    matches = engine.upcoming_matches(hours=24)

    today_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"<b>🏆 2026 世界盃每日重點賽事 ({today_str})</b>",
        ""
    ]

    for m in matches:
        pred = m.get("prediction", {})
        home_name = m["home_team"]
        away_name = m["away_team"]
        home = engine.teams.get(home_name, {})
        away = engine.teams.get(away_name, {})
        home_flag = home.get("flag", "")
        away_flag = away.get("flag", "")
        date_display = m["date"][5:].replace("-", "/")
        reason = build_reason(pred, home, away, m.get("city", ""), home_name, engine.predictions_db)
        home_pred = pred.get("home_score_pred", "-")
        away_pred = pred.get("away_score_pred", "-")
        home_prob = pred.get("home_win_prob", "-")
        draw_prob = pred.get("draw_prob", "-")
        away_prob = pred.get("away_win_prob", "-")

        lines.extend([
            f"<b>{home_flag} {home_name} vs {away_name} {away_flag}</b>",
            f"⏰ {date_display} {m['time_taiwan']}（台北時間） | {m.get('stage', '')} {m.get('group', '')} | 📍 {m.get('city', '')}",
            f"📈 預測比分：{home_pred} - {away_pred}",
            f"🎯 勝率：主 {home_prob}% / 平 {draw_prob}% / 客 {away_prob}%",
            f"📝 {reason}",
            ""
        ])

    html = "\n".join(lines).strip()
    return matches, html


def save_daily_briefing(matches: list[dict], html: str, engine: WorldCupEngine = None) -> Path:
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = PREDICTIONS_DIR / "daily_briefing.md"
    today_str = datetime.now().strftime("%Y-%m-%d")

    if not matches:
        content = f"# 2026 世界盃每日賽事摘要 ({today_str})\n\n今日無 2026 世界盃賽事。\n"
    else:
        lines = [f"# 2026 世界盃每日賽事摘要 ({today_str})", ""]
        for m in matches:
            pred = m.get("prediction", {})
            home_name = m["home_team"]
            away_name = m["away_team"]
            date_display = m["date"][5:].replace("-", "/")
            home_flag = m.get("home_flag", "")
            away_flag = m.get("away_flag", "")
            # 用更口語化的理由覆蓋 engine 內建理由
            home = engine.teams.get(home_name, {}) if engine else {}
            away = engine.teams.get(away_name, {}) if engine else {}
            reason = build_reason(pred, home, away, m.get("city", ""), home_name, engine.predictions_db if engine else None)
            lines.extend([
                f"## 賽事 {m['match_id']}: {home_flag} {home_name} vs {away_flag} {away_name}",
                f"- 時間：{date_display} {m['time_taiwan']}（台北時間）",
                f"- 階段：{m.get('stage', '')} {m.get('group', '')}",
                f"- 地點：{m.get('city', '')}",
                f"- 預測比分：{pred.get('home_score_pred', '-')} - {pred.get('away_score_pred', '-')}",
                f"- 勝率：主 {pred.get('home_win_prob', '-')}% / 平 {pred.get('draw_prob', '-')}% / 客 {pred.get('away_win_prob', '-')}%",
                f"- 預測理由：{reason}",
                ""
            ])
        content = "\n".join(lines).strip() + "\n"

    path.write_text(content, encoding="utf-8")
    return path


def main():
    engine = WorldCupEngine()
    matches, html = generate_briefing(engine)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "8237046348:AAFQuJavHmL_dWu_ot3hciym6UiP7_UTneA")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "8257517978")

    if not matches:
        send_telegram("今日無 2026 世界盃賽事。", token=token, chat_id=chat_id)
        save_daily_briefing([], "")
        print("已發送：今日無賽事")
        return

    # 取得隊伍國旗並寫入 match 物件供 markdown 使用
    for m in matches:
        home = engine.teams.get(m["home_team"], {})
        away = engine.teams.get(m["away_team"], {})
        m["home_flag"] = home.get("flag", "")
        m["away_flag"] = away.get("flag", "")

    success = send_telegram(html, token=token, chat_id=chat_id, parse_mode="HTML")
    saved_path = save_daily_briefing(matches, html, engine=engine)
    print(f"Telegram 發送結果: {success}")
    print(f"摘要已更新: {saved_path}")


if __name__ == "__main__":
    # 避免 Windows 主控台輸出 emoji 時出現 cp950 編碼錯誤
    sys.stdout.reconfigure(encoding="utf-8")
    main()
