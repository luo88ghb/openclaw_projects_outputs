import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'engine'))

from worldcup_engine import WorldCupEngine
from telegram_notifier import _score_prediction_hit

engine = WorldCupEngine()
finished = [m for m in engine.matches if m.get('status') == 'finished']
print('total finished', len(finished))

total = 0
direction = 0
misses = 0
for m in finished:
    pred = m.get('prediction', {})
    hit, score = _score_prediction_hit(pred, m['home_score'], m['away_score'])
    total += score
    if score == 1.0:
        direction += 1
    elif score == -1.0:
        misses += 1

print('total score', total)
print('direction hits', direction)
print('misses', misses)
print('hit rate', round(direction/len(finished)*100,1))
