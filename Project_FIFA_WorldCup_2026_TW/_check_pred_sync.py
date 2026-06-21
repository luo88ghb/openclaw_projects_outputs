import json

# 載入 phase_predictions.json
with open('predictions/phase_predictions.json', encoding='utf-8') as f:
    phase = json.load(f)

# 載入 matches_104.json
with open('data/matches_104.json', encoding='utf-8') as f:
    matches = json.load(f)['matches']

# 找 #29 的預測
for m in phase.get('all_matches', []):
    if m.get('match_id') == 29:
        print("Phase predictions #29:")
        print(f"  預測比分: {m.get('predicted_home_score')} - {m.get('predicted_away_score')}")
        print(f"  勝方預測: {m.get('predicted_winner')}")
        print(f"  置信度: {m.get('confidence')}")
        print(f"  方法: {m.get('method')}")
        print()

# 找 #29 在 matches_104.json 的實際結果
for m in matches:
    if m.get('match_id') == 29:
        print("matches_104.json #29:")
        print(f"  實際比分: {m.get('home_score')} - {m.get('away_score')}")
        print(f"  預測: {m.get('prediction', {}).get('home_score_pred')} - {m.get('prediction', {}).get('away_score_pred')}")
        print(f"  hit: {m.get('prediction', {}).get('hit')}")
        print(f"  實際勝方: {m.get('actual_winner', 'N/A')}")
        break