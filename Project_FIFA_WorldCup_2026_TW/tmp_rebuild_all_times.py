import json, re
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent

def load_ref(path: Path):
    text = open(path, 'r', encoding='utf-8').read()
    # Try the StickyWatchBar full schedule payload first
    pattern = re.compile(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', re.DOTALL)
    m = pattern.search(text)
    if not m:
        # Fallback to per-country countryMatches JSON
        pattern = re.compile(r'"countryMatches":(\[\{.*?\}\])', re.DOTALL)
        m = pattern.search(text)
        if not m:
            raise RuntimeError(f'Could not find matches JSON in {path}')
    matches_json = m.group(1).replace('"$undefined"', 'null')
    ref_matches = json.loads(matches_json)
    out = {}
    for r in ref_matches:
        raw = r.get('date')
        if not raw:
            continue
        dt = datetime.strptime(raw, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        taipei = dt.astimezone(timezone(timedelta(hours=8)))
        key = (r['teamA'], r['teamB'])
        out[key] = {
            'utc_date': raw[:10],
            'utc_time': raw[11:16],
            'taipei_date': taipei.strftime('%Y-%m-%d'),
            'taipei_time': taipei.strftime('%H:%M'),
        }
    return out

ref = {}
for name in ['kickoffclock_united-states.txt', 'kickoffclock_uruguay.txt', 'kickoffclock_new-zealand.txt',
             'kickoffclock_saudi-arabia.txt', 'kickoffclock_iran.txt']:
    ref.update(load_ref(BASE / name))

data = json.load(open(BASE / 'data' / 'matches_104.json', 'r', encoding='utf-8'))

zh_to_en = {
    '墨西哥': 'Mexico', '南非': 'South Africa', '南韓': 'South Korea', '韓國': 'South Korea',
    '捷克': 'Czechia', '捷克共和國': 'Czechia', '加拿大': 'Canada', '波士尼亞與赫塞哥維納': 'Bosnia & Herzegovina',
    '波赫': 'Bosnia & Herzegovina', '美國': 'United States', '巴拉圭': 'Paraguay',
    '卡達': 'Qatar', '瑞士': 'Switzerland', '巴西': 'Brazil', '摩洛哥': 'Morocco',
    '海地': 'Haiti', '蘇格蘭': 'Scotland', '澳洲': 'Australia', '澳大利亞': 'Australia',
    '土耳其': 'Türkiye', '德國': 'Germany', '庫拉索': 'Curaçao', '荷蘭': 'Netherlands',
    '日本': 'Japan', '象牙海岸': 'Ivory Coast', '厄瓜多': 'Ecuador', '瑞典': 'Sweden',
    '突尼西亞': 'Tunisia', '西班牙': 'Spain', '維德角': 'Cape Verde', '比利時': 'Belgium',
    '埃及': 'Egypt', '沙烏地阿拉伯': 'Saudi Arabia', '烏拉圭': 'Uruguay', '伊朗': 'Iran',
    '紐西蘭': 'New Zealand', '法國': 'France', '塞內加爾': 'Senegal', '伊拉克': 'Iraq',
    '挪威': 'Norway', '阿根廷': 'Argentina', '阿爾及利亞': 'Algeria', '奧地利': 'Austria',
    '約旦': 'Jordan', '葡萄牙': 'Portugal', '剛果民主共和國': 'DR Congo', '英格蘭': 'England',
    '克羅埃西亞': 'Croatia', '迦納': 'Ghana', '巴拿馬': 'Panama', '烏茲別克': 'Uzbekistan',
    '哥倫比亞': 'Colombia',
}

updated = 0
for m in data['matches']:
    home_en = zh_to_en.get(m['home_team'], m['home_team'])
    away_en = zh_to_en.get(m['away_team'], m['away_team'])
    key = (home_en, away_en)
    r = ref.get(key)
    if not r:
        if m['match_id'] <= 72:
            print(f'WARN: no reference for {m["match_id"]} {home_en} vs {away_en}')
        continue
    m['date'] = r['taipei_date']
    m['time_taiwan'] = r['taipei_time']
    updated += 1

json.dump(data, open(BASE / 'data' / 'matches_104.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'updated {updated} matches')
