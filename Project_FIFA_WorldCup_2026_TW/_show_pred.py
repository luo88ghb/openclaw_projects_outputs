import json
with open('data/matches_104.json', encoding='utf-8') as f:
    data = json.load(f)

# 顯示 #28-#32 場次的詳細預測資訊
for m in data['matches']:
    if 28 <= m['match_id'] <= 32:
        pred = m.get('prediction', {})
        print(f"#{m['match_id']:2d} | {m['home_team']} vs {m['away_team']}")
        print(f"   比分: {m.get('home_score')} - {m.get('away_score')} (狀態: {m.get('status')})")
        print(f"   預測: {pred.get('home_score_pred')} - {pred.get('away_score_pred')}")
        print(f"   hit: {pred.get('hit')}, score: {pred.get('score')}")
        print(f"   reason: {pred.get('reason', '')[:50]}...")
        print()