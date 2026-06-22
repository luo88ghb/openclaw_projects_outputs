"""
engine/elo_model.py - L2 Elo 預測模型

資料來源: worldcupelo.com (截至 2026-06-22 抓取)
提供基於 Elo 評分的勝/平/負機率，供儀表板切換使用。

公式參考 worldcupelo.com 標準做法:
- 主場優勢 ~ +100 Elo points
- 勝率 = 1 / (1 + 10^((away_elo - home_elo)/400))
- 和局機率使用簡化常數 ~ 25% (可調)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# 2026-06-22 從 https://worldcupelo.com/rankings 抓取的世界盃 48 隊 Elo 評分
# 以 teams.json 的 name_zh 為 key
ELO_RATINGS: Dict[str, int] = {
    "墨西哥": 1834,
    "南非": 1529,
    "南韓": 1784,
    "捷克": 1731,
    "加拿大": 1806,
    "卡達": 1427,
    "瑞士": 1897,
    "波赫": 1571,
    "巴西": 1979,
    "摩洛哥": 1806,
    "海地": 1542,
    "蘇格蘭": 1790,
    "美國": 1747,
    "巴拉圭": 1833,
    "澳洲": 1774,
    "土耳其": 1880,
    "德國": 1910,
    "象牙海岸": 1637,
    "厄瓜多": 1933,
    "庫拉索": 1467,
    "荷蘭": 1959,
    "日本": 1879,
    "突尼西亞": 1614,
    "瑞典": 1660,
    "西班牙": 2171,
    "維德角": 1561,
    "沙烏地阿拉伯": 1592,
    "烏拉圭": 1890,
    "比利時": 1849,
    "埃及": 1660,
    "伊朗": 1754,
    "紐西蘭": 1586,
    "法國": 2063,
    "塞內加爾": 1869,
    "挪威": 1922,
    "伊拉克": 1583,
    "阿根廷": 2113,
    "阿爾及利亞": 1728,
    "奧地利": 1818,
    "約旦": 1691,
    "塞爾維亞": 1769,
    "葡萄牙": 1976,
    "烏茲別克": 1735,
    "哥倫比亞": 1998,
    "剛果民主共和國": 1639,
    "英格蘭": 2042,
    "克羅埃西亞": 1933,
    "迦納": 1509,
    "巴拿馬": 1743,
}


def load_teams():
    with open(DATA_DIR / "teams.json", "r", encoding="utf-8") as f:
        return json.load(f)["teams"]


def get_elo(name_zh: str) -> int | None:
    return ELO_RATINGS.get(name_zh)


def win_prob(home_elo: int, away_elo: int, home_advantage: int = 100) -> float:
    """回傳主隊勝率 (不含和局)。"""
    diff = home_elo - away_elo + home_advantage
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def predict_match(home_elo: int, away_elo: int, draw_prob: float = 0.25) -> Dict[str, float]:
    """回傳 {home, draw, away} 機率。"""
    w = win_prob(home_elo, away_elo)
    adj = 1.0 - draw_prob
    return {
        "home": round(w * adj, 4),
        "draw": round(draw_prob, 4),
        "away": round((1.0 - w) * adj, 4),
    }


def predict_by_name(home_name: str, away_name: str) -> Dict[str, float] | None:
    home_elo = get_elo(home_name)
    away_elo = get_elo(away_name)
    if home_elo is None or away_elo is None:
        return None
    return predict_match(home_elo, away_elo)


def coverage() -> Dict[str, int | list]:
    teams = load_teams()
    covered = [t["name_zh"] for t in teams if get_elo(t["name_zh"]) is not None]
    missing = [t["name_zh"] for t in teams if get_elo(t["name_zh"]) is None]
    return {"total": len(teams), "covered": len(covered), "missing": missing}


if __name__ == "__main__":
    print("Elo 模型載入成功，覆蓋率:", coverage())
    print("阿根廷 vs 塞爾維亞:", predict_by_name("阿根廷", "塞爾維亞"))
