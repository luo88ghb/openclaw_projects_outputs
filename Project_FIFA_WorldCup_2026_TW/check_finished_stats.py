import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('data/matches_104.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

finished = [m for m in data['matches'] if m.get('status') == 'finished' and m.get('prediction')]
hits = [m for m in finished if m.get('hit')]
total_score = sum(m.get('score', 0) for m in finished)
print(f'已結束有預測場次: {len(finished)}, 命中: {len(hits)}, 總分: {total_score:+.1f}')
