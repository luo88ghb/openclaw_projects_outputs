"""
World Cup 2026 data scraper.
- Designed to collect match results after each game.
- Supports FIFA official / Wikipedia / association sources.
- Uses lightweight HTTP + BeautifulSoup; falls back to manual input if blocked.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


def load_json(filename: str) -> Any:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename: str, data: Any) -> None:
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def http_get(url: str, retries: int = 2, timeout: int = 15) -> requests.Response | None:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "zh-TW,en-US;q=0.9"}
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"[scraper] GET {url} attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    return None


class WorldCupScraper:
    """Fetches match results from trusted public sources."""

    def __init__(self):
        self.matches = load_json("matches_104.json")["matches"]

    def _normalize_team_name(self, name: str) -> str:
        mapping = {
            "United States": "美國",
            "USA": "美國",
            "South Korea": "南韓",
            "Korea Republic": "南韓",
            "Saudi Arabia": "沙烏地阿拉伯",
            "Morocco": "摩洛哥",
            "Mexico": "墨西哥",
            "Canada": "加拿大",
            "Brazil": "巴西",
            "Argentina": "阿根廷",
            "France": "法國",
            "Spain": "西班牙",
            "Germany": "德國",
            "England": "英格蘭",
            "Portugal": "葡萄牙",
            "Netherlands": "荷蘭",
            "Japan": "日本",
            "Croatia": "克羅埃西亞",
            "Switzerland": "瑞士",
            "Belgium": "比利時",
            "Uruguay": "烏拉圭",
            "Ecuador": "厄瓜多",
            "Iran": "伊朗",
            "Ghana": "迦納",
            "Senegal": "塞內加爾",
            "Australia": "澳洲",
            "Poland": "波蘭",
            "Tunisia": "突尼西亞",
            "Serbia": "塞爾維亞",
            "Colombia": "哥倫比亞",
            "Paraguay": "巴拉圭",
            "Peru": "秘魯",
            "Chile": "智利",
            "Venezuela": "委內瑞拉",
            "Austria": "奧地利",
            "Norway": "挪威",
            "Sweden": "瑞典",
            "Denmark": "丹麥",
            "Nigeria": "奈及利亞",
            "Algeria": "阿爾及利亞",
            "Egypt": "埃及",
            "South Africa": "南非",
            "Côte d'Ivoire": "象牙海岸",
            "Ivory Coast": "象牙海岸",
            "Cape Verde": "維德角",
            "Curacao": "庫拉索",
            "Haiti": "海地",
            "Honduras": "宏都拉斯",
            "Panama": "巴拿馬",
            "New Zealand": "紐西蘭",
            "Jordan": "約旦",
            "Uzbekistan": "烏茲別克",
            "Qatar": "卡達",
            "Scotland": "蘇格蘭",
            "Angola": "安哥拉"
        }
        return mapping.get(name.strip(), name.strip())

    def fetch_fifa_matchday(self, url: str) -> list[dict]:
        """Parse FIFA matchday page (requires known HTML structure)."""
        resp = http_get(url)
        if not resp:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        # Generic: look for score elements
        score_spans = soup.find_all("span", class_=re.compile(r"score|result", re.I))
        for span in score_spans:
            text = span.get_text(strip=True)
            m = re.match(r"(\d+)\s*-\s*(\d+)", text)
            if m:
                # Without context, just return raw scores
                results.append({"raw_score": text, "home_score": int(m.group(1)), "away_score": int(m.group(2))})
        return results

    def fetch_wikipedia_results(self) -> list[dict]:
        """Scrape 2026 FIFA World Cup Wikipedia page for match results.
        URL: https://en.wikipedia.org/wiki/2026_FIFA_World_Cup
        """
        url = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"
        resp = http_get(url)
        if not resp:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        # Wikipedia match cells often contain team names and scores in tables
        for table in soup.find_all("table", {"class": "vevent"}):
            tds = table.find_all("td")
            if len(tds) < 4:
                continue
            try:
                home = tds[0].get_text(strip=True)
                score_text = tds[1].get_text(strip=True)
                away = tds[2].get_text(strip=True)
                m = re.match(r"(\d+)\s*–\s*(\d+)", score_text)
                if m:
                    results.append({
                        "home_team": self._normalize_team_name(home),
                        "away_team": self._normalize_team_name(away),
                        "home_score": int(m.group(1)),
                        "away_score": int(m.group(2)),
                        "source": "wikipedia"
                    })
            except Exception:
                continue
        return results

    def find_match_id(self, home_team: str, away_team: str, date: str | None = None) -> int | None:
        """Map scraped team names to internal match_id."""
        for match in self.matches:
            if (match["home_team"] == home_team and match["away_team"] == away_team) or \
               (match["home_team"] == home_team and away_team in match["away_team"]) or \
               (home_team in match["home_team"] and match["away_team"] == away_team):
                if date is None or match["date"] == date:
                    return match["match_id"]
        return None

    def collect_recent_results(self) -> dict:
        """Collect results from multiple sources and return mapped scores."""
        all_results = {}
        # Try Wikipedia first as public, stable source during tournament
        wiki_results = self.fetch_wikipedia_results()
        for r in wiki_results:
            mid = self.find_match_id(r["home_team"], r["away_team"])
            if mid:
                all_results[mid] = {
                    "home_score": r["home_score"],
                    "away_score": r["away_score"],
                    "source": r["source"]
                }
        return {
            "collected_at": datetime.now().isoformat(),
            "results": all_results,
            "count": len(all_results)
        }

    def save_raw_collection(self, data: dict) -> None:
        PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
        path = PREDICTIONS_DIR / "scraped_results.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def run_collection():
    scraper = WorldCupScraper()
    data = scraper.collect_recent_results()
    scraper.save_raw_collection(data)
    print(f"[scraper] Collected {data['count']} results at {data['collected_at']}")
    return data


if __name__ == "__main__":
    run_collection()
