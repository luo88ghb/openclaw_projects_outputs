"""
Scraper for Chinese Wikipedia 2026 FIFA World Cup page.
Fetches the match schedule section and parses score/status for a given match.
"""
from typing import Optional
import re

import urllib.request
from bs4 import BeautifulSoup

WIKI_URL = "https://zh.wikipedia.org/zh-tw/2026%E5%B9%B4%E5%9C%8B%E9%9A%9B%E8%B6%B3%E5%8D%94%E4%B8%96%E7%95%8C%E7%9B%83"

# Chinese numerals used in date headers on zh.wikipedia.org
_CN_NUMBERS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
}


def _chinese_month_to_int(name: str) -> Optional[int]:
    for cn, num in sorted(_CN_NUMBERS.items(), key=lambda x: -len(x[0])):
        if cn in name:
            return num
    return None


def fetch_wiki_html(timeout: int = 30) -> str:
    req = urllib.request.Request(
        WIKI_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


_TEAM_ALIASES = {
    "波士尼亞與赫塞哥維納": "波赫",
    "波士尼亞": "波赫",
    "波斯尼亞": "波赫",
    "波赫": "波赫",
    "捷克共和國": "捷克",
    "剛果民主共和國": "剛果民主共和國",
    "韓國": "南韓",
    "庫拉索": "古拉索",
    "古拉索": "古拉索",
    "維德角": "維德角",
    "美國": "美國",
    "墨西哥": "墨西哥",
    "加拿大": "加拿大",
    "南非": "南非",
    "南韓": "南韓",
    "捷克": "捷克",
    "巴拉圭": "巴拉圭",
    "澳洲": "澳洲",
    "土耳其": "土耳其",
    "卡達": "卡達",
    "瑞士": "瑞士",
    "巴西": "巴西",
    "摩洛哥": "摩洛哥",
    "海地": "海地",
    "蘇格蘭": "蘇格蘭",
    "德國": "德國",
    "象牙海岸": "象牙海岸",
    "厄瓜多": "厄瓜多",
    "荷蘭": "荷蘭",
    "日本": "日本",
    "瑞典": "瑞典",
    "突尼西亞": "突尼西亞",
    "比利時": "比利時",
    "埃及": "埃及",
    "伊朗": "伊朗",
    "紐西蘭": "紐西蘭",
    "西班牙": "西班牙",
    "沙烏地阿拉伯": "沙烏地阿拉伯",
    "烏拉圭": "烏拉圭",
    "法國": "法國",
    "塞內加爾": "塞內加爾",
    "伊拉克": "伊拉克",
    "挪威": "挪威",
    "阿根廷": "阿根廷",
    "阿爾及利亞": "阿爾及利亞",
    "奧地利": "奧地利",
    "約旦": "約旦",
    "葡萄牙": "葡萄牙",
    "烏茲別克": "烏茲別克",
    "哥倫比亞": "哥倫比亞",
    "英格蘭": "英格蘭",
    "克羅埃西亞": "克羅埃西亞",
    "迦納": "迦納",
    "巴拿馬": "巴拿馬",
}


def _normalize_team_name(name: str) -> str:
    """Normalize team name for flexible matching."""
    name = name.strip().replace(" ", "")
    return _TEAM_ALIASES.get(name, name)


def _wiki_text(html: str) -> str:
    """Extract plain text from Wikipedia HTML and normalize whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_all_scores(html_or_text: str) -> dict:
    """
    Extract all match results from the Wikipedia page.
    Returns a dict keyed by (home_norm, away_norm) -> {date, time_utc, home_score, away_score, raw_text}
    Accepts either raw HTML or plain text.
    """
    is_html = "<html" in html_or_text or "<table" in html_or_text or "<tr" in html_or_text
    text = html_or_text
    if is_html:
        text = _wiki_text(html_or_text)

    # Normalize dashes to a single hyphen
    text = text.replace("\u2013", "-").replace("\u2212", "-").replace("\u2014", "-")
    results = {}

    # 1) Regex over full page text for date/time annotated results.
    pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2})\s*\)\s*"
        r"(\d{2}:\d{2})\s*(UTC[+-]?\d{1,2})\s+"
        r"([\u4e00-\u9fa5\u00b7\w\-\u0027]+?)\s+"
        r"(\d+)-(\d+)\s+"
        r"([\u4e00-\u9fa5\u00b7\w\-\u0027]+?)(?=\s+\d{4}年|\s+\d{4}-\d{2}-\d{2}\s*\)|\s+\d+['\u2032]|\s+報告|\s*<|$)"
    )
    for m in pattern.finditer(text):
        home = _normalize_team_name(m.group(4))
        away = _normalize_team_name(m.group(7))
        results[(home, away)] = {
            "date": m.group(1),
            "time_utc": m.group(2),
            "utc_offset": m.group(3),
            "home_score": int(m.group(5)),
            "away_score": int(m.group(6)),
            "raw_text": f"{home} {m.group(5)}-{m.group(6)} {away}",
        }

    # 2) Table parse from the original HTML (best for finished group matches).
    soup = BeautifulSoup(html_or_text, "html.parser")
    for row in soup.find_all("tr", itemprop="name"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 3:
            continue
        score_text = cells[1].get_text(" ", strip=True)
        # 從分數文字中提取第一組 數字-數字 格式，後面若是狀態文字（如「進行中」、「比賽結束」）則接受；
        # 若是其他雜訊（如「進行中」前面還有數字）則拒絕，避免 "1 進行中" 被誤判。
        score_match = re.search(
            r"^(\d+)\s*[\u2013\-]\s*(\d+)\s*(進行中|比賽結束|半場|完場|Finished|FT|HT)?$",
            score_text,
        )
        if not score_match:
            continue
        hs, as_ = score_match.group(1), score_match.group(2)
        home = _normalize_team_name(cells[0].get_text(" ", strip=True))
        away = _normalize_team_name(cells[2].get_text(" ", strip=True))
        results[(home, away)] = {
            "date": "",
            "time_utc": "",
            "utc_offset": "",
            "home_score": int(hs),
            "away_score": int(as_),
            "raw_text": f"{home} {hs}-{as_} {away}",
        }
    return results


def parse_match_score(
    html: str,
    home_team: str,
    away_team: str,
    match_date: str,
    match_time: str,
) -> dict:
    """
    Parse the Wikipedia page for a specific match.
    Returns dict with keys: home_score, away_score, status, raw_text.
    Scores are ints if found, otherwise None.
    """
    scores = _extract_all_scores(html)

    home_norm = _normalize_team_name(home_team)
    away_norm = _normalize_team_name(away_team)

    key = (home_norm, away_norm)
    if key in scores:
        return {
            "home_score": scores[key]["home_score"],
            "away_score": scores[key]["away_score"],
            "status": "finished",
            "raw_text": scores[key]["raw_text"],
        }

    # No score found: treat as scheduled
    return {
        "home_score": None,
        "away_score": None,
        "status": "scheduled",
        "raw_text": "",
    }


def get_match_result(
    home_team: str,
    away_team: str,
    match_date: str,
    match_time: str,
) -> dict:
    """Convenience: fetch page and parse result for one match."""
    html = fetch_wiki_html()
    return parse_match_score(html, home_team, away_team, match_date, match_time)


if __name__ == "__main__":
    # Quick sanity checks
    for home, away in [
        ("美國", "巴拉圭"),
        ("墨西哥", "南非"),
        ("德國", "庫拉索"),
        ("西班牙", "維德角"),
    ]:
        print(home, "vs", away, "=>", get_match_result(home, away, "", ""))
