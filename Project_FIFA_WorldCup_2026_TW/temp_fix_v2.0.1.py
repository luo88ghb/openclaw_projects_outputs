import json
import os
import shutil

base = 'C:\\Users\\danny\\.openclaw\\workspace\\projects\\Project_FIFA_WorldCup_2026_TW'
matches_path = os.path.join(base, 'data', 'matches_104.json')
teams_path = os.path.join(base, 'data', 'teams.json')

# Backup
shutil.copy(matches_path, matches_path + '.v201.bak')
shutil.copy(teams_path, teams_path + '.v201.bak')

# Load
with open(matches_path, 'r', encoding='utf-8') as f:
    matches_data = json.load(f)
with open(teams_path, 'r', encoding='utf-8') as f:
    teams_data = json.load(f)

# Mapping placeholder -> real team name
placeholder_map = {
    '附加賽勝者A': '捷克',
    '附加賽勝者B': '波士尼亞',
    '附加賽勝者C': '土耳其',
    '附加賽勝者D': '瑞典',
    '附加賽勝者E': '伊拉克',
    '附加賽勝者F': '剛果民主共和國',
}

# New teams to add
new_teams = [
    {"id": "CZE", "name_zh": "捷克", "name_en": "Czechia", "confederation": "UEFA", "group": "A", "fifa_ranking": 42, "pot": 4, "flag": "🇨🇿"},
    {"id": "BIH", "name_zh": "波士尼亞", "name_en": "Bosnia and Herzegovina", "confederation": "UEFA", "group": "B", "fifa_ranking": 74, "pot": 4, "flag": "🇧🇦"},
    {"id": "TUR", "name_zh": "土耳其", "name_en": "Türkiye", "confederation": "UEFA", "group": "D", "fifa_ranking": 28, "pot": 4, "flag": "🇹🇷"},
    {"id": "SWE", "name_zh": "瑞典", "name_en": "Sweden", "confederation": "UEFA", "group": "F", "fifa_ranking": 27, "pot": 4, "flag": "🇸🇪"},
    {"id": "IRQ", "name_zh": "伊拉克", "name_en": "Iraq", "confederation": "AFC", "group": "I", "fifa_ranking": 55, "pot": 4, "flag": "🇮🇶"},
    {"id": "COD", "name_zh": "剛果民主共和國", "name_en": "DR Congo", "confederation": "CAF", "group": "K", "fifa_ranking": 63, "pot": 4, "flag": "🇨🇩"},
]

# Add new teams if not exists
existing_names = {t['name_zh'] for t in teams_data['teams']}
for t in new_teams:
    if t['name_zh'] not in existing_names:
        teams_data['teams'].append(t)

# Replace placeholders in matches
for m in matches_data['matches']:
    if m['home_team'] in placeholder_map:
        m['home_team'] = placeholder_map[m['home_team']]
    if m['away_team'] in placeholder_map:
        m['away_team'] = placeholder_map[m['away_team']]

# Fix Match 4 score: USA 2-0 Paraguay
for m in matches_data['matches']:
    if m['match_id'] == 4:
        m['home_score'] = 2
        m['away_score'] = 0

# Save
with open(matches_path, 'w', encoding='utf-8') as f:
    json.dump(matches_data, f, ensure_ascii=False, indent=2)
with open(teams_path, 'w', encoding='utf-8') as f:
    json.dump(teams_data, f, ensure_ascii=False, indent=2)

print('v2.0.1 fix applied successfully.')
