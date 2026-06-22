import json, sys
from fix_times_from_wiki import team_alias, parse_wiki_datetime

with open('debug_footballboxes.json', encoding='utf-8') as f:
    boxes=json.load(f)
with open('data/matches_104.json', encoding='utf-8') as f:
    data=json.load(f)

# Debug not found boxes
for b in boxes:
    h=team_alias(b['home']); a=team_alias(b['away'])
    nd, nt=parse_wiki_datetime(b['date'], b['time'])
    pair=frozenset([h,a])
    # find candidate matches by team pair
    cands=[m for m in data['matches'] if frozenset([team_alias(m['home_team']),team_alias(m['away_team'])])==pair]
    if not cands:
        sys.stdout.buffer.write((f"NO_CANDIDATE: i={b['i']} {b['home']} vs {b['away']} aliased={h} vs {a} pair={pair}\n").encode('utf-8'))
    else:
        sys.stdout.buffer.write((f"FOUND_CANDIDATES: i={b['i']} new={nd} {nt}\n").encode('utf-8'))
        for m in cands:
            sys.stdout.buffer.write((f"  mid={m['match_id']} {m['date']} {m['time_taiwan']} {m['home_team']} vs {m['away_team']}\n").encode('utf-8'))
