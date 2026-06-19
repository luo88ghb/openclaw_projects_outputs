import sys
sys.path.insert(0, 'engine')
from datetime import datetime
from scheduler import trigger_time

m = {
    'date': '2026-06-18',
    'time_taiwan': '04:00',
}
t = trigger_time(m)
print('match_dt:', datetime.strptime(f"{m['date']} {m['time_taiwan']}", "%Y-%m-%d %H:%M"))
print('trigger :', t)
print('now     :', datetime.now().astimezone())
print('wait_s  :', (t - datetime.now().astimezone()).total_seconds())
