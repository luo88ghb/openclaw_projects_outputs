import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def parse_wiki_datetime(date_text: str, time_text: str) -> tuple:
    date_iso = re.search(r"\((\d{4}-\d{2}-\d{2})\)", date_text)
    if not date_iso:
        raise ValueError(f"Cannot parse date: {date_text}")
    date = date_iso.group(1)
    m = re.search(r"(\d{1,2}:\d{2})\s*(UTC[\u002b\u2212+-]?\d{1,2})", time_text)
    if not m:
        raise ValueError(f"Cannot parse time: {time_text}")
    t, tz = m.group(1), m.group(2)
    sign = tz[3]
    if sign == "\u2212":
        sign = "-"; val = tz[4:]
    elif sign == "+":
        val = tz[4:]
    elif sign == "-":
        val = tz[4:]
    else:
        sign = "+"; val = tz[3:]
    offset = int(f"{sign}{val}")
    dt = datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
    dt_utc = dt - timedelta(hours=offset)
    dt_tw = dt_utc.astimezone(timezone(timedelta(hours=8)))
    return dt_tw.strftime("%Y-%m-%d"), dt_tw.strftime("%H:%M")


def main():
    with open(BASE_DIR / "debug_footballboxes.json", "r", encoding="utf-8") as f:
        boxes = json.load(f)
    with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Match knockout placeholder boxes by sequential index offset: knockout boxes start at i=72 (match 73 in 1-based)
    # We already handled i=0..71 for group matches (up to match 72).
    # Knockout matches in DB are match_id 73..104 (32 matches). Wiki boxes i=72..103 (32 boxes).
    updated = 0
    for idx in range(72, 104):
        b = boxes[idx]
        match_id = idx + 1  # 73..104
        m = next((x for x in data["matches"] if x["match_id"] == match_id), None)
        if m is None:
            print(f"match_id {match_id} not found")
            continue
        new_date, new_time = parse_wiki_datetime(b["date"], b["time"])
        if m["date"] != new_date or m["time_taiwan"] != new_time:
            print(f"Update #{match_id}: {m['date']} {m['time_taiwan']} -> {new_date} {new_time}  ({b['home']} vs {b['away']})")
            m["date"] = new_date
            m["time_taiwan"] = new_time
            updated += 1

    backup = DATA_DIR / "matches_104.json.bak_wiki_knockout_times"
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Backup saved to {backup}")

    with open(DATA_DIR / "matches_104.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Updated {updated} knockout matches")


if __name__ == "__main__":
    main()
