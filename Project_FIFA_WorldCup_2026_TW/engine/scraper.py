"""
World Cup 2026 data scraper v2.
- Multi-source result collection: Wikipedia (primary) + FIFA Taiwan (fallback).
- Cross-validation across sources; conflicts are flagged, not silently merged.
- Robust team-name normalization (English/Chinese/abbreviations/aliases).
- Structured warnings so callers can tell when scraping is broken.
"""
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"
FIFA_TW_URL = "https://xn--fifa-tc5fq65k1ju.tw/world-cup-2026-schedule/"


def load_json(filename: str) -> Any:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename: str, data: Any) -> None:
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def http_get(url: str, retries: int = 2, timeout: int = 20) -> requests.Response | None:
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
    """Fetches match results from multiple public sources with validation."""

    # Canonical Chinese names used in matches_104.json
    TEAM_ALIASES: dict[str, str] = {
        # English variants
        "United States": "美國",
        "USA": "美國",
        "South Korea": "南韓",
        "Korea Republic": "南韓",
        "Korea": "南韓",
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
        "Turkey": "土耳其",
        "加納": "迦納",
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
        "Curaçao": "庫拉索",
        "Haiti": "海地",
        "Honduras": "宏都拉斯",
        "Panama": "巴拿馬",
        "New Zealand": "紐西蘭",
        "Jordan": "約旦",
        "Uzbekistan": "烏茲別克",
        "Qatar": "卡達",
        "Scotland": "蘇格蘭",
        "Angola": "安哥拉",
        "Czech Republic": "捷克",
        "Czechia": "捷克",
        "Bosnia and Herzegovina": "波赫",
        "Bosnia": "波赫",
        "Democratic Republic of the Congo": "剛果民主共和國",
        "DR Congo": "剛果民主共和國",
        "Congo DR": "剛果民主共和國",
        "Iraq": "伊拉克",
        # FIFA-TW Chinese variants / full names
        "韓國": "南韓",
        "沙烏地阿拉伯": "沙烏地阿拉伯",
        "波士尼亞與赫塞哥維納": "波赫",
        "維德角": "維德角",
        "庫拉索": "庫拉索",
        "宏都拉斯": "宏都拉斯",
        "巴拿馬": "巴拿馬",
        "紐西蘭": "紐西蘭",
        "烏茲別克": "烏茲別克",
        "蘇格蘭": "蘇格蘭",
        "安哥拉": "安哥拉",
        "捷克": "捷克",
        "剛果民主共和國": "剛果民主共和國",
        "伊拉克": "伊拉克",
    }

    FIFA_TW_ABBREVIATION_TO_NAME: dict[str, str] = {
        "MEX": "墨西哥", "RSA": "南非", "KOR": "南韓", "CZE": "捷克",
        "CAN": "加拿大", "BOS": "波赫", "USA": "美國",
        "PAR": "巴拉圭", "QAT": "卡達", "SUI": "瑞士", "BRA": "巴西",
        "MAR": "摩洛哥", "HAI": "海地", "SCO": "蘇格蘭", "AUS": "澳洲",
        "TUR": "土耳其", "GER": "德國", "CUW": "庫拉索", "NED": "荷蘭",
        "JPN": "日本", "CIV": "象牙海岸", "ECU": "厄瓜多", "SWE": "瑞典",
        "TUN": "突尼西亞", "ESP": "西班牙", "CPV": "維德角", "BEL": "比利時",
        "EGY": "埃及", "KSA": "沙烏地阿拉伯", "URU": "烏拉圭", "IRN": "伊朗",
        "NZL": "紐西蘭", "FRA": "法國", "SEN": "塞內加爾", "NOR": "挪威",
        "IRQ": "伊拉克", "ARG": "阿根廷", "ALG": "阿爾及利亞", "AUT": "奧地利",
        "JOR": "約旦", "POR": "葡萄牙", "COD": "剛果民主共和國", "ENG": "英格蘭",
        "CRO": "克羅埃西亞", "POL": "波蘭", "SRB": "塞爾維亞", "COL": "哥倫比亞",
        "VEN": "委內瑞拉", "CHI": "智利", "PER": "秘魯", "DEN": "丹麥",
        "NGA": "奈及利亞", "GHA": "迦納", "PAN": "巴拿馬", "HON": "宏都拉斯",
        "UZB": "烏茲別克", "ANG": "安哥拉",
    }

    def __init__(self):
        self.matches = load_json("matches_104.json")["matches"]
        self.warnings: list[dict] = []

    def _warn(self, category: str, message: str, details: dict | None = None):
        self.warnings.append({
            "category": category,
            "message": message,
            "details": details or {},
            "at": datetime.now().isoformat(),
        })
        print(f"[scraper][warn] {category}: {message}")

    def _normalize_team_name(self, name: str) -> str:
        name = name.strip()
        # Direct alias
        if name in self.TEAM_ALIASES:
            return self.TEAM_ALIASES[name]
        # FIFA-TW pattern: "中文名 CODE" or "中文名" alone
        m = re.match(r"^([^A-Za-z\s]+)\s*([A-Z]{3})?$", name)
        if m:
            chinese = m.group(1).strip()
            if chinese in self.TEAM_ALIASES:
                return self.TEAM_ALIASES[chinese]
            return chinese
        # FIFA-TW reverse pattern: "CODE 中文名" (rare)
        m2 = re.match(r"^([A-Z]{3})\s+([^A-Za-z\s]+)$", name)
        if m2:
            chinese = m2.group(2).strip()
            if chinese in self.TEAM_ALIASES:
                return self.TEAM_ALIASES[chinese]
            return chinese
        # Direct FIFA abbreviation
        if name.upper() in self.FIFA_TW_ABBREVIATION_TO_NAME:
            return self.FIFA_TW_ABBREVIATION_TO_NAME[name.upper()]
        return name

    def _extract_score(self, text: str) -> tuple[int, int] | None:
        """Extract home/away score from text like '2–0', '2 : 0', '2-0'."""
        text = text.strip()
        # en-dash / em-dash / colon / hyphen
        m = re.match(r"^(\d+)\s*[–—:\-]\s*(\d+)$", text)
        if m:
            return int(m.group(1)), int(m.group(2))
        return None

    def _is_real_score(self, text: str) -> bool:
        """Exclude placeholders like 'Match 53', 'v', '—'."""
        return bool(re.match(r"^\d+\s*[–—:\-]\s*\d+$", text.strip()))

    def _map_team_to_canonical(self, home: str, away: str) -> tuple[str | None, str | None]:
        """Normalize both team names and warn if unknown."""
        home_norm = self._normalize_team_name(home)
        away_norm = self._normalize_team_name(away)
        return home_norm, away_norm

    def fetch_wikipedia_results(self) -> list[dict]:
        """Scrape 2026 FIFA World Cup Wikipedia page for match results."""
        resp = http_get(WIKIPEDIA_URL, retries=2, timeout=25)
        if not resp:
            self._warn("source_failed", f"Wikipedia request failed: {WIKIPEDIA_URL}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        boxes = soup.find_all("div", class_=re.compile(r"footballbox", re.I))
        if not boxes:
            self._warn("source_empty", "Wikipedia returned no footballbox divs; page structure may have changed")
            return []

        results = []
        for box in boxes:
            try:
                home_el = box.find(["th", "td"], class_=re.compile(r"fhome|home", re.I))
                away_el = box.find(["th", "td"], class_=re.compile(r"faway|away", re.I))
                score_el = box.find(["th", "td"], class_=re.compile(r"fscore|score", re.I))

                if not (home_el and away_el and score_el):
                    # Fallback: scan text for teams/score inside the box
                    txt = box.get_text(" | ", strip=True)
                    continue

                home_raw = home_el.get_text(strip=True)
                away_raw = away_el.get_text(strip=True)
                score_text = score_el.get_text(strip=True)

                if not self._is_real_score(score_text):
                    continue  # match not played yet

                score = self._extract_score(score_text)
                if not score:
                    continue

                home_team, away_team = self._map_team_to_canonical(home_raw, away_raw)
                if home_team is None or away_team is None:
                    continue

                results.append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": score[0],
                    "away_score": score[1],
                    "source": "wikipedia",
                    "raw_score": score_text,
                })
            except Exception as e:
                self._warn("parse_error", f"Wikipedia box parse failed: {e}")
                continue

        print(f"[scraper] Wikipedia parsed {len(results)} finished matches")
        return results

    def fetch_fifa_tw_results(self) -> list[dict]:
        """Scrape FIFA Taiwan schedule page for match results."""
        resp = http_get(FIFA_TW_URL, retries=2, timeout=25)
        if not resp:
            self._warn("source_failed", f"FIFA-TW request failed: {FIFA_TW_URL}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.select_one("#full-schedule table")
        if not table:
            self._warn("source_empty", "FIFA-TW #full-schedule table not found")
            return []

        rows = table.find_all("tr")
        results = []
        for r in rows:
            cells = r.find_all(["td", "th"])
            if len(cells) < 7:
                continue
            try:
                # Skip header row
                header_text = cells[0].get_text(strip=True)
                if "日期" in header_text or "時間" in header_text:
                    continue

                home_raw = cells[1].get_text(" ", strip=True)
                score_text = cells[2].get_text(strip=True)
                away_raw = cells[3].get_text(" ", strip=True)
                status_text = cells[4].get_text(strip=True)

                if not self._is_real_score(score_text):
                    continue
                score = self._extract_score(score_text)
                if not score:
                    continue

                home_team, away_team = self._map_team_to_canonical(home_raw, away_raw)
                if home_team is None or away_team is None:
                    continue

                results.append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": score[0],
                    "away_score": score[1],
                    "source": "fifa_tw",
                    "raw_score": score_text,
                    "status": status_text,
                })
            except Exception as e:
                self._warn("parse_error", f"FIFA-TW row parse failed: {e}")
                continue

        print(f"[scraper] FIFA-TW parsed {len(results)} finished matches")
        return results

    def find_match_id(self, home_team: str, away_team: str, date: str | None = None) -> int | None:
        """Map scraped team names to internal match_id.

        Names must already be canonical (matching matches_104.json).
        Allows exact or swapped pairing in case some sources flip home/away.
        """
        home_team = home_team.strip()
        away_team = away_team.strip()

        candidates = []
        for match in self.matches:
            m_home = match["home_team"].strip()
            m_away = match["away_team"].strip()
            exact = m_home == home_team and m_away == away_team
            swapped = m_home == away_team and m_away == home_team
            if exact or swapped:
                candidates.append(match)
                if exact:
                    return match["match_id"]
        if candidates:
            # Return first matching match id (prefer same-date if date provided)
            if date:
                for match in candidates:
                    if match.get("date") == date:
                        return match["match_id"]
            return candidates[0]["match_id"]
        return None

    def collect_recent_results(self) -> dict:
        """
        Collect results from multiple sources, cross-validate, and return mapped scores.
        Strategy:
          1. Fetch Wikipedia results.
          2. Fetch FIFA-TW fallback results.
          3. Merge by match_id; if both sources agree on score, accept it.
          4. If sources disagree, keep Wikipedia value but flag conflict.
          5. Report unmapped teams and source-empty situations as warnings.
        """
        self.warnings = []
        source_results: dict[str, list[dict]] = {
            "wikipedia": self.fetch_wikipedia_results(),
            "fifa_tw": self.fetch_fifa_tw_results(),
        }

        by_id: dict[int, dict[str, dict]] = {}
        unmapped: list[dict] = []

        for source, results in source_results.items():
            for r in results:
                mid = self.find_match_id(r["home_team"], r["away_team"])
                if mid is None:
                    unmapped.append({
                        "source": source,
                        "home_team": r["home_team"],
                        "away_team": r["away_team"],
                        "score": f"{r['home_score']}-{r['away_score']}",
                    })
                    continue
                by_id.setdefault(mid, {})[source] = {
                    "home_score": r["home_score"],
                    "away_score": r["away_score"],
                    "raw_score": r.get("raw_score"),
                    "status": r.get("status"),
                }

        if unmapped:
            self._warn("unmapped_teams", f"{len(unmapped)} scraped results could not be mapped to match_id", {"items": unmapped})

        # Check global source health
        total_from_sources = sum(len(v) for v in source_results.values())
        for source, results in source_results.items():
            if not results:
                self._warn("source_empty", f"Source '{source}' returned zero finished matches")
        if total_from_sources == 0:
            self._warn("all_sources_empty", "All scraping sources returned zero finished matches; pipeline is likely broken")

        # Merge with cross-validation
        merged: dict[int, dict] = {}
        for mid, sources in by_id.items():
            wiki = sources.get("wikipedia")
            fifa = sources.get("fifa_tw")

            def _score_tuple(src):
                return (src["home_score"], src["away_score"])

            scores = {_score_tuple(src) for src in sources.values()}
            if len(scores) == 1:
                home_score, away_score = scores.pop()
                verified = len(sources) > 1
                merged[mid] = {
                    "home_score": home_score,
                    "away_score": away_score,
                    "source": "+".join(sorted(sources.keys())),
                    "verified": verified,
                }
            else:
                # Conflict: keep the score from the highest-priority source, flag it
                priority = ["wikipedia", "fifa_tw"]
                chosen_src = next((s for s in priority if s in sources), list(sources.keys())[0])
                chosen = sources[chosen_src]
                conflict = {src: f"{v['home_score']}-{v['away_score']}" for src, v in sources.items()}
                merged[mid] = {
                    "home_score": chosen["home_score"],
                    "away_score": chosen["away_score"],
                    "source": chosen_src,
                    "verified": False,
                    "conflict": conflict,
                }
                self._warn("score_conflict", f"Match {mid}: sources disagree", conflict)

        return {
            "collected_at": datetime.now().isoformat(),
            "results": merged,
            "count": len(merged),
            "source_counts": {
                "wikipedia": len(source_results["wikipedia"]),
                "fifa_tw": len(source_results["fifa_tw"]),
            },
            "warnings": self.warnings,
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
    print(f"[scraper] Merged {data['count']} verified/available results at {data['collected_at']}")
    if data["warnings"]:
        print(f"[scraper] {len(data['warnings'])} warning(s):")
        for w in data["warnings"]:
            print(f"  - {w['category']}: {w['message']}")
    return data


if __name__ == "__main__":
    run_collection()
