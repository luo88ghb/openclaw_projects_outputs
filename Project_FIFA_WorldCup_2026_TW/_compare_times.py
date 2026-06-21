import json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 從 kickoffclock.txt 解析
text = Path('kickoffclock.txt').read_text(encoding='utf-8')
m = re.search(r'\["\$","\$L6",null,\{"matches":(\[\{.*?\}\])\}', text, re.DOTALL)
raw = json.loads(m.group(1).replace('"$undefined"', 'null'))

KICKOFF_EN = {'TÃ¼rkiye': 'Turkey', 'CuraÃ§ao': 'Curacao'}

def _norm(s):
    return KICKOFF_EN.get(s.strip(), s.strip())

# 載入 matches_104.json
with open('data/matches_104.json', encoding='utf-8') as f:
    data = json.load(f)

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

# 建立 kickoffclock 索引
ref = {}
for r in raw:
    a = _norm(r['teamA'])
    b = _norm(r['teamB'])
    if a == 'TBD' or b == 'TBD':
        continue
    ref[(a, b)] = r['date']
    ref[tuple(sorted((a, b)))] = r['date']

# 比對所有小組賽場次
print("比對 matches_104.json 與 kickoffclock.txt:")
print("=" * 80)

discrepancies = []
for m in data['matches']:
    if m['match_id'] > 72:  # 只檢查小組賽
        continue
    
    he = zh_to_en.get(m['home_team'], m['home_team'])
    ae = zh_to_en.get(m['away_team'], m['away_team'])
    he = _norm(he)
    ae = _norm(ae)
    
    utc_str = ref.get((he, ae)) or ref.get(tuple(sorted((he, ae))))
    
    if not utc_str:
        print(f"#{m['match_id']:2d} ⚠️ 找不到對應: {he} vs {ae}")
        continue
    
    dt = datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    taipei = dt.astimezone(timezone(timedelta(hours=8)))
    expected_date = taipei.strftime('%Y-%m-%d')
    expected_time = taipei.strftime('%H:%M')
    
    if m['date'] != expected_date or m['time_taiwan'] != expected_time:
        discrepancies.append({
            'match_id': m['match_id'],
            'home': m['home_team'],
            'away': m['away_team'],
            'old': f"{m['date']} {m['time_taiwan']}",
            'new': f"{expected_date} {expected_time}",
            'utc': utc_str
        })

if discrepancies:
    print(f"\n發現 {len(discrepancies)} 場時間不一致:")
    for d in discrepancies:
        print(f"#{d['match_id']:2d} {d['home']} vs {d['away']}: {d['old']} -> {d['new']} (UTC {d['utc']})")
else:
    print("\n[OK] 所有小組賽場次時間一致")

# 額外檢查：列出 kickoffclock 中有 Turkey 的場次
print("\n\nkickoffclock 中 Turkey 相關場次:")
for r in raw:
    ta, tb = _norm(r['teamA']), _norm(r['teamB'])
    if 'Turkey' in (ta, tb) and 'TBD' not in (ta, tb):
        dt = datetime.strptime(r['date'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        taipei = dt.astimezone(timezone(timedelta(hours=8)))
        opp = tb if ta == 'Turkey' else ta
        print(f"  Turkey vs {opp}: UTC {r['date']} -> 台北 {taipei.strftime('%Y-%m-%d %H:%M')}")