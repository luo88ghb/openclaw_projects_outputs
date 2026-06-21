import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).resolve().parent

# Load full schedule from kickoffclock .txt file
text = (BASE / 'kickoffclock.txt').read_text(encoding='utf-8')
import re
m = re.search(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', text, re.DOTALL)
raw = json.loads(m.group(1).replace('"$undefined"', 'null'))

# kickoffclock uses mojibake for some names when saved as UTF-8 text
# TÃ¼rkiye = Türkiye, CuraÃ§ao = Curaçao
KICKOFF_EN = {'TÃ¼rkiye': 'Turkey', 'CuraÃ§ao': 'Curacao'}

def _norm_name(s: str) -> str:
    s = s.strip()
    s = KICKOFF_EN.get(s, s)
    return s

# Build reference lookup
ref = {}
for r in raw:
    if r['teamA'] == 'TBD' or r['teamB'] == 'TBD':
        continue
    dt = datetime.strptime(r['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    taipei = dt.astimezone(timezone(timedelta(hours=8)))
    rec = {
        'utc': r['date'],
        'taipei_date': taipei.strftime('%Y-%m-%d'),
        'taipei_time': taipei.strftime('%H:%M'),
    }
    a = _norm_name(r['teamA'])
    b = _norm_name(r['teamB'])
    # Store both (teamA, teamB) and sorted pair for flexible lookup
    ref[(a, b)] = rec
    ref[tuple(sorted((a, b)))] = rec

with open(BASE / 'data' / 'matches_104.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Chinese to English team name mapping
zh_to_en = {
    '墨西哥': 'Mexico', '南非': 'South Africa', '南韓': 'South Korea', '韓國': 'South Korea',
    '捷克': 'Czechia', '加拿大': 'Canada', '波士尼亞與赫塞哥維納': 'Bosnia & Herzegovina', '波赫': 'Bosnia & Herzegovina',
    '美國': 'United States', '巴拉圭': 'Paraguay', '卡達': 'Qatar', '瑞士': 'Switzerland',
    '巴西': 'Brazil', '摩洛哥': 'Morocco', '海地': 'Haiti', '蘇格蘭': 'Scotland',
    '澳洲': 'Australia', '澳大利亞': 'Australia', '土耳其': 'Turkey', '德國': 'Germany',
    '庫拉索': 'Curacao', '荷蘭': 'Netherlands', '日本': 'Japan', '象牙海岸': 'Ivory Coast',
    '厄瓜多': 'Ecuador', '瑞典': 'Sweden', '突尼西亞': 'Tunisia', '西班牙': 'Spain',
    '維德角': 'Cape Verde', '比利時': 'Belgium', '埃及': 'Egypt', '沙烏地阿拉伯': 'Saudi Arabia',
    '烏拉圭': 'Uruguay', '伊朗': 'Iran', '紐西蘭': 'New Zealand', '法國': 'France',
    '塞內加爾': 'Senegal', '伊拉克': 'Iraq', '挪威': 'Norway', '阿根廷': 'Argentina',
    '阿爾及利亞': 'Algeria', '奧地利': 'Austria', '約旦': 'Jordan', '葡萄牙': 'Portugal',
    '剛果民主共和國': 'DR Congo', '英格蘭': 'England', '克羅埃西亞': 'Croatia', '迦納': 'Ghana',
    '巴拿馬': 'Panama', '烏茲別克': 'Uzbekistan', '哥倫比亞': 'Colombia',
}

updated = 0
missing = []
for match in data['matches']:
    home_en = zh_to_en.get(match['home_team'], match['home_team'])
    away_en = zh_to_en.get(match['away_team'], match['away_team'])
    home_en = _norm_name(home_en)
    away_en = _norm_name(away_en)
    
    # Try direct lookup first, then sorted pair
    home_sort, away_sort = sorted((home_en, away_en))
    r = ref.get((home_en, away_en)) or ref.get((home_sort, away_sort))
    
    if not r:
        if match['match_id'] <= 72:
            missing.append((match['match_id'], home_en, away_en))
        continue
    
    old = (match['date'], match['time_taiwan'])
    new = (r['taipei_date'], r['taipei_time'])
    if old != new:
        match['date'] = r['taipei_date']
        match['time_taiwan'] = r['taipei_time']
        updated += 1
        print(f"#{match['match_id']} {match['home_team']} vs {match['away_team']}: {old[0]} {old[1]} -> {new[0]} {new[1]} (UTC {r['utc']})")

with open(BASE / 'data' / 'matches_104.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'\n總計更新 {updated} 場次')
if missing:
    print(f'\n⚠️ 找不到對應的場次 ({len(missing)} 場):')
    for item in missing:
        print(f'  #{item[0]}: {item[1]} vs {item[2]}')