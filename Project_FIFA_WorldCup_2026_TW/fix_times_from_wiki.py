import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"

# Load latest Wikipedia football boxes
def load_footballboxes(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_wiki_datetime(date_text: str, time_text: str) -> tuple:
    """Return (date_iso, time_taiwan_24h) from Wikipedia footballbox strings."""
    # date: "2026年6月11日(2026-06-11)"
    date_iso = re.search(r"\((\d{4}-\d{2}-\d{2})\)", date_text)
    if not date_iso:
        raise ValueError(f"Cannot parse date: {date_text}")
    date = date_iso.group(1)

    # time: "13:00UTC−6" or "13:00 UTC−6"
    m = re.search(r"(\d{1,2}:\d{2})\s*(UTC[\u002b\u2212+-]?\d{1,2})", time_text)
    if not m:
        raise ValueError(f"Cannot parse time: {time_text}")
    t, tz = m.group(1), m.group(2)
    # normalize unicode minus sign
    sign = tz[3]
    if sign == "\u2212":
        sign = "-"
        val = tz[4:]
    elif sign == "+":
        val = tz[4:]
    elif sign == "-":
        val = tz[4:]
    else:
        # e.g. UTC6 means +6
        sign = "+"
        val = tz[3:]
    offset = int(f"{sign}{val}")
    dt = datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
    dt_utc = dt - timedelta(hours=offset)
    dt_tw = dt_utc.astimezone(timezone(timedelta(hours=8)))
    return dt_tw.strftime("%Y-%m-%d"), dt_tw.strftime("%H:%M")


def team_alias(name: str) -> str:
    # map common variations from Wikipedia to our DB
    aliases = {
        "南非共和国": "南非",
        "韓國": "南韓",
        "捷克共和国": "捷克",
        "美利堅合眾國": "美國",
        "澳洲": "澳大利亞",
        "伊朗伊斯蘭共和國": "伊朗",
        "德國": "德國",
        "沙烏地阿拉伯": "沙烏地阿拉伯",
        "古拉索": "庫拉索",
        "伊朗": "伊朗",
    }
    return aliases.get(name, name)


def main():
    boxes_path = BASE_DIR / "debug_footballboxes.json"
    boxes = load_footballboxes(boxes_path)

    with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    matches = data["matches"]

    # Build index by (home_alias, away_alias, wiki_date)
    by_key = {}
    for m in matches:
        key = (team_alias(m["home_team"]), team_alias(m["away_team"]), m["date"])
        by_key[key] = m

    updated = 0
    not_found = []
    for b in boxes:
        try:
            new_date, new_time = parse_wiki_datetime(b["date"], b["time"])
        except Exception as e:
            import traceback
            print(f"parse fail {b.get('home')} vs {b.get('away')}: {e}")
            traceback.print_exc()
            continue
        key = (team_alias(b["home"]), team_alias(b["away"]), new_date)
        m = by_key.get(key)
        if m is None:
            # try without date constraint
            for (h, a, d), cand in by_key.items():
                if h == team_alias(b["home"]) and a == team_alias(b["away"]):
                    m = cand
                    break
        if m is None:
            not_found.append(b)
            continue
        if m["date"] != new_date or m["time_taiwan"] != new_time:
            print(f"Update #{m['match_id']}: {m['date']} {m['time_taiwan']} -> {new_date} {new_time}  ({b['home']} vs {b['away']})")
            m["date"] = new_date
            m["time_taiwan"] = new_time
            updated += 1

    # Save backup
    backup = DATA_DIR / "matches_104.json.bak_wiki_times"
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Backup saved to {backup}")

    with open(DATA_DIR / "matches_104.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Updated {updated} matches. Not found: {len(not_found)}")
    if not_found:
        with open("debug_not_found.json","w",encoding="utf-8") as f:
            json.dump(not_found, f, ensure_ascii=False, indent=2)
        print(f"Not found details saved to debug_not_found.json")

if __name__ == "__main__":
    main()
