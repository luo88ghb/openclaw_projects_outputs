import json

# 載入兩個資料來源
with open('predictions/phase_predictions.json', encoding='utf-8') as f:
    phase = json.load(f)

with open('data/matches_104.json', encoding='utf-8') as f:
    matches = json.load(f)['matches']

print("比對 #25-#35 的預測資料:")
print("=" * 80)

for mid in range(25, 36):
    phase_pred = None
    match_pred = None
    
    for m in phase.get('all_matches', []):
        if m.get('match_id') == mid:
            phase_pred = m
            break
    
    for m in matches:
        if m.get('match_id') == mid:
            match_pred = m
            break
    
    print(f"\n#{mid}:")
    if match_pred:
        print(f"  matches_104.json:")
        print(f"    {match_pred['home_team']} vs {match_pred['away_team']}")
        print(f"    比分: {match_pred.get('home_score')} - {match_pred.get('away_score')}")
        p = match_pred.get('prediction', {})
        print(f"    預測: {p.get('home_score_pred')} - {p.get('away_score_pred')} (hit: {p.get('hit')})")
    
    if phase_pred:
        print(f"  phase_predictions.json:")
        print(f"    預測: {phase_pred.get('predicted_home_score')} - {phase_pred.get('predicted_away_score')}")
        print(f"    勝方: {phase_pred.get('predicted_winner')}")
        print(f"    hit: {phase_pred.get('hit')}")