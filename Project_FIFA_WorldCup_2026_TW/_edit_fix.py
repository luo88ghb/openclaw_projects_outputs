from pathlib import Path
p = Path('fix_match_times.py')
text = p.read_text(encoding='utf-8')
text = text.replace("    home_en = zh_to_en.get(match['home_team'], match['home_team'])\n    away_en = zh_to_en.get(match['away_team'], match['away_team'])", """    home_en = zh_to_en.get(match['home_team'], match['home_team'])
    home_en = KICKOFF_EN.get(home_en, home_en)
    away_en = zh_to_en.get(match['away_team'], match['away_team'])
    away_en = KICKOFF_EN.get(away_en, away_en)""")
p.write_text(text, encoding='utf-8')
