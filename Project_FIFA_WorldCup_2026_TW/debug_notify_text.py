"""Debug script to print Telegram notification text without sending."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'engine'))

from engine.telegram_notifier import _get_prediction_for_match, _score_prediction_hit
from engine.worldcup_engine import WorldCupEngine

engine = WorldCupEngine()
m = engine.get_match(29)
pred = _get_prediction_for_match(m["match_id"])
hit, score = _score_prediction_hit(pred, m["home_score"], m["away_score"])
hs = pred.get("predicted_home_score", pred.get("home_score_pred", "?"))
aw = pred.get("predicted_away_score", pred.get("away_score_pred", "?"))
winner = "和局" if m["home_score"] == m["away_score"] else (
    m["home_team"] if m["home_score"] > m["away_score"] else m["away_team"]
)
score_summary = "命中勝負方向" if score == 1.0 else ("未命中" if score == -1.0 else "未知")
msg = (
    f"⚽ <b>2026 世界盃賽果更新</b>\n"
    f"場次：#{m['match_id']} {m['stage']}{' ' + m['group'] + '組' if m['group'] else ''}\n"
    f"對戰：{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}\n"
    f"地點：{m['city']}"
    f"\n🔮 預測：{hs}-{aw} {'✅' if hit else '❌'} {score_summary}（得分：{score:+.1f}） | 實際勝方：{winner}"
)
print(msg)
print(f"pred keys: {pred.keys()}")
