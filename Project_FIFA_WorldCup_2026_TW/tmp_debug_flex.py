import json, sys
from fix_times_from_wiki import team_alias, placeholder_match, parse_wiki_datetime
from datetime import datetime

def team_pair_match(pair_a, pair_b):
    if pair_a == pair_b:
        return True
    a_list = list(pair_a)
    b_list = list(pair_b)
    if len(a_list) != 2 or len(b_list) != 2:
        return False
    return (placeholder_match(a_list[0], b_list[0]) and placeholder_match(a_list[1], b_list[1])) or \
           (placeholder_match(a_list[0], b_list[1]) and placeholder_match(a_list[1], b_list[0]))

with open('debug_footballboxes.json', encoding='utf-8') as f:
    boxes=json.load(f)
with open('data/matches_104.json', encoding='utf-8') as f:
    data=json.load(f)

for b in boxes:
    if b['i'] not in (74,78,81): continue
    h=team_alias(b['home']); a=team_alias(b['away'])
    new_date, new_time = parse_wiki_datetime(b['date'], b['time'])
    pair_b=frozenset([h,a])
    cands_sorted = sorted(
        data['matches'],
        key=lambda c: abs((datetime.strptime(c['date'], '%Y-%m-%d') - datetime.strptime(new_date, '%Y-%m-%d')).days),
    )
    found=False
    for cand in cands_sorted[:10]:
        pair_c=frozenset([team_alias(cand['home_team']), team_alias(cand['away_team'])])
        if team_pair_match(pair_b, pair_c):
            sys.stdout.buffer.write((f"MATCH i={b['i']} -> mid={cand['match_id']} {cand['date']} {cand['time_taiwan']}\n").encode('utf-8'))
            found=True
            break
        else:
            sys.stdout.buffer.write((f"  no match mid={cand['match_id']} {pair_c} vs {pair_b}\n").encode('utf-8'))
    if not found:
        sys.stdout.buffer.write((f"NOT FOUND i={b['i']}\n").encode('utf-8'))
