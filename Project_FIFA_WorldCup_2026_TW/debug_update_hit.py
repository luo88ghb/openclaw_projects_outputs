"""Debug script to backfill hit/score on finished matches."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'engine'))

from worldcup_engine import WorldCupEngine
from telegram_notifier import _score_prediction_hit

engine = WorldCupEngine()
changed = False
for m in engine.matches:
    if m.get('status') != 'finished' or m.get('home_score') is None:
        continue
    pred = m.get('prediction', {})
    if not pred:
        continue
    hit, score = _score_prediction_hit(pred, m['home_score'], m['away_score'])
    if pred.get('hit') != hit or pred.get('score') != score or m.get('hit') != hit:
        pred['hit'] = hit
        pred['score'] = score
        m['hit'] = hit
        changed = True
        print(f"Updated match {m['match_id']} hit={hit} score={score}")

if changed:
    engine._save_matches()
    print('Saved matches_104.json')
else:
    print('No changes needed')
