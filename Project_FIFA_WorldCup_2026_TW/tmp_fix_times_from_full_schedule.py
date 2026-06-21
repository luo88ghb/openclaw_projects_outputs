import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent

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

en_to_zh = {v: k for k, v in zh_to_en.items()}

# Load full schedule from a single source that contains all 72 group matches
# KickoffClock /schedule/united-states.txt has the full matches list in $L6 payload.
text = open(BASE / 'kickoffclock_uruguay.txt', 'r', encoding='utf-8').read()
m = re.search(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', text, re.DOTALL)
if not m:
    raise RuntimeError('full schedule not found')
raw = json.loads(m.group(1).replace('"$undefined"', 'null'))

ref = {}
for r in raw:
    if r['teamA'] == 'TBD' or r['teamB'] == 'TBD':
        continue
    dt = datetime.strptime(r['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    taipei = dt.astimezone(timezone(timedelta(hours=8)))
    rec = {
        'utc_date': r['date'][:10],
        'utc_time': r['date'][11:16],
        'taipei_date': taipei.strftime('%Y-%m-%d'),
        'taipei_time': taipei.strftime('%H:%M'),
    }
    ref[(r['teamA'], r['teamB'])] = rec
    ref[tuple(sorted((r['teamA'], r['teamB'])))] = rec

print(f'loaded {len(ref)} reference matches')

data = json.load(open(BASE / 'data' / 'matches_104.json', 'r', encoding='utf-8'))
updated = 0
missing = []
for m in data['matches']:
    home_en = zh_to_en.get(m['home_team'], m['home_team'])
    away_en = zh_to_en.get(m['away_team'], m['away_team'])
    # KickoffClock lists teams in a consistent "home/away" order but may swap names;
    # look up by unordered pair.
    key = tuple(sorted((home_en, away_en)))
    r = ref.get(key)
    if not r:
        key2 = (home_en, away_en)
        r = ref.get(key2)
    if not r:
        if m['match_id'] <= 72:
            missing.append((m['match_id'], home_en, away_en))
        continue
    old = (m['date'], m['time_taiwan'])
    m['date'] = r['taipei_date']
    m['time_taiwan'] = r['taipei_time']
    new = (m['date'], m['time_taiwan'])
    if old != new:
        updated += 1
        print(f"#{m['match_id']} {home_en} v {away_en}: {old[0]} {old[1]} -> {new[0]} {new[1]} (UTC {r['utc_date']} {r['utc_time']})")

json.dump(data, open(BASE / 'data' / 'matches_104.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'updated {updated} matches')
if missing:
    print('missing:', missing)
