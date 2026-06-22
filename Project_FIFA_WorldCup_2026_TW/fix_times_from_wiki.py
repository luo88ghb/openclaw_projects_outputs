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
    m = re.search(r"(\d{1,2}:\d{2})\s*UTC([\u002b\u2212+-]?)\s*(\d{1,2})", time_text)
    if not m:
        raise ValueError(f"Cannot parse time: {time_text}")
    t, sign_in, val = m.group(1), m.group(2), m.group(3)
    # normalize unicode minus sign
    sign = sign_in
    if sign == "\u2212":
        sign = "-"
    elif sign == "":
        # e.g. UTC6 means +6
        sign = "+"
    offset = int(f"{sign}{val}")
    dt = datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
    # local = UTC + offset  =>  UTC = local - offset
    dt_utc = (dt - timedelta(hours=offset)).replace(tzinfo=timezone.utc)
    # Taipei = UTC + 8
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
    name = aliases.get(name, name)
    # 淘汰賽佔位符對應：維基 "X組首名/次名/第三位" / "賽事 N 勝方/負方"
    name = name.replace("首名", "第一名")
    name = name.replace("次名", "第二名")
    name = name.replace("第三位", "第三名")
    name = name.replace("負方", "敗方")
    # 維基 "賽事 73 勝方" → 我們 "第73場勝方"
    import re
    name = re.sub(r"賽事\s+(\d+)\s+(勝方|敗方)", r"第\1場\2", name)
    # 淘汰賽佔位符：維基用 "A/B/C/D/F組第三名"，我們用 "A/B/C/D/F組第三名" (A/B/C/D/F vs A/B/C/D/F)
    # 以及維基 "C/E/F/H/I組第三位" → "C/E/F/H/I組第三名"
    # 但主隊不同導致無法用 frozenset 配對；用模糊配對：若交集相同則視為同一占位符
    return name


def placeholder_match(name_a: str, name_b: str) -> bool:
    """對於 "A/B/X組第三名" 形式的佔位符，忽略組別順序比對。"""
    import re
    pat = re.compile(r"^([A-L/]+)組第三名$")
    ma = pat.match(name_a)
    mb = pat.match(name_b)
    if ma and mb:
        return set(ma.group(1).split("/")) == set(mb.group(1).split("/"))
    return name_a == name_b


def main():
    boxes_path = BASE_DIR / "debug_footballboxes.json"
    boxes = load_footballboxes(boxes_path)

    with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    matches = data["matches"]

    # Build indices for flexible matching
    by_key = {}
    by_team_pair = {}
    for m in matches:
        h = team_alias(m["home_team"])
        a = team_alias(m["away_team"])
        by_key[(h, a, m["date"])] = m
        pair = frozenset([h, a])
        by_team_pair.setdefault(pair, []).append(m)

    def team_pair_match(pair_a: frozenset, pair_b: frozenset) -> bool:
        """對比兩個隊伍集合；若雙方有一方是佔位符，用組別集合比對。"""
        if pair_a == pair_b:
            return True
        # 逐一比對元素
        a_list = list(pair_a)
        b_list = list(pair_b)
        if len(a_list) != 2 or len(b_list) != 2:
            return False
        return (placeholder_match(a_list[0], b_list[0]) and placeholder_match(a_list[1], b_list[1])) or \
               (placeholder_match(a_list[0], b_list[1]) and placeholder_match(a_list[1], b_list[0]))

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
        h = team_alias(b["home"])
        a = team_alias(b["away"])
        # 1. exact (home, away, new_date)
        m = by_key.get((h, a, new_date))
        # 2. same order ignoring date
        if m is None:
            for (hh, aa, d), cand in by_key.items():
                if hh == h and aa == a:
                    m = cand
                    break
        # 3. reverse order ignoring date
        if m is None:
            for (hh, aa, d), cand in by_key.items():
                if hh == a and aa == h:
                    m = cand
                    break
        # 4. flexible team pair with placeholder matching
        if m is None:
            pair_b = frozenset([h, a])
            cands_sorted = sorted(
                matches,
                key=lambda c: abs((datetime.strptime(c["date"], "%Y-%m-%d") - datetime.strptime(new_date, "%Y-%m-%d")).days),
            )
            for cand in cands_sorted:
                pair_c = frozenset([team_alias(cand["home_team"]), team_alias(cand["away_team"])])
                if team_pair_match(pair_b, pair_c):
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
