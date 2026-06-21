"""
生成預測歷史紀錄頁面 (predictions_history.html)
"""
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"
DASHBOARD_DIR = BASE_DIR / "dashboard"

def main():
    with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
        matches_data = json.load(f)
    
    # 計算預測統計
    total = 0
    hits = 0
    score_3 = 0
    score_1 = 0
    score_neg1 = 0
    pending = 0
    
    finished_matches = []
    
    for m in matches_data["matches"]:
        if m.get("status") == "finished" and m.get("prediction"):
            total += 1
            pred = m["prediction"]
            if pred.get("hit"):
                hits += 1
                if pred.get("score") == 3:
                    score_3 += 1
                elif pred.get("score") == 1:
                    score_1 += 1
            else:
                score_neg1 += 1
            
            finished_matches.append({
                "match_id": m["match_id"],
                "date": m["date"],
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                "home_score": m["home_score"],
                "away_score": m["away_score"],
                "home_score_pred": pred.get("home_score_pred"),
                "away_score_pred": pred.get("away_score_pred"),
                "hit": pred.get("hit"),
                "score": pred.get("score"),
                "reason": pred.get("reason", "")
            })
        elif m.get("status") == "scheduled" and m.get("prediction"):
            pending += 1
    
    hit_rate = (hits / total * 100) if total > 0 else 0
    total_score = score_3 * 3 + score_1 * 1 + score_neg1 * (-1)
    
    # 生成 HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>預測歷史紀錄 - 2026 世界盃</title>
  <link rel="stylesheet" href="css/style.css" />
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: #e0e0e0;
      margin: 0;
      padding: 20px;
      min-height: 100vh;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    h1 {{
      text-align: center;
      color: #fff;
      margin-bottom: 30px;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
      margin-bottom: 30px;
    }}
    .stat-card {{
      background: rgba(255,255,255,0.1);
      border-radius: 12px;
      padding: 20px;
      text-align: center;
    }}
    .stat-value {{
      font-size: 2rem;
      font-weight: bold;
      color: #4fc3f7;
    }}
    .stat-label {{
      font-size: 0.9rem;
      color: #aaa;
      margin-top: 5px;
    }}
    .match-list {{
      background: rgba(255,255,255,0.05);
      border-radius: 12px;
      overflow: hidden;
    }}
    .match-row {{
      display: grid;
      grid-template-columns: 50px 100px 1fr 80px 80px 60px;
      align-items: center;
      padding: 12px 15px;
      border-bottom: 1px solid rgba(255,255,255,0.1);
    }}
    .match-row:nth-child(odd) {{
      background: rgba(255,255,255,0.03);
    }}
    .match-row:hover {{
      background: rgba(255,255,255,0.08);
    }}
    .hit-true {{
      color: #4caf50;
    }}
    .hit-false {{
      color: #f44336;
    }}
    .score-3 {{
      background: linear-gradient(135deg, #ffd700, #ffaa00);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      font-weight: bold;
    }}
    .header-row {{
      background: rgba(255,255,255,0.15) !important;
      font-weight: bold;
      color: #fff;
    }}
    .back-link {{
      display: inline-block;
      margin-bottom: 20px;
      color: #4fc3f7;
      text-decoration: none;
    }}
    .back-link:hover {{
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <div class="container">
    <a href="index.html" class="back-link">← 返回儀表板</a>
    <h1>🔮 預測歷史紀錄</h1>
    
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{total}</div>
        <div class="stat-label">已結束場次</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{hits}</div>
        <div class="stat-label">命中場次</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{hit_rate:.1f}%</div>
        <div class="stat-label">命中率</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{total_score:+.0f}</div>
        <div class="stat-label">總得分</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{score_3}</div>
        <div class="stat-label">🎯 命中比數</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{score_1}</div>
        <div class="stat-label">✅ 命中方向</div>
      </div>
    </div>
    
    <div class="match-list">
      <div class="match-row header-row">
        <div>場次</div>
        <div>日期</div>
        <div>對戰</div>
        <div>比分</div>
        <div>預測</div>
        <div>結果</div>
      </div>
"""
    
    for m in finished_matches:
        hit_class = "hit-true" if m["hit"] else "hit-false"
        score_class = "score-3" if m["score"] == 3 else ""
        result_icon = "🎯" if m["score"] == 3 else ("✅" if m["hit"] else "❌")
        
        html += f"""      <div class="match-row">
        <div>#{m["match_id"]}</div>
        <div>{m["date"][5:]}</div>
        <div>{m["home_team"]} vs {m["away_team"]}</div>
        <div>{m["home_score"]} - {m["away_score"]}</div>
        <div>{m["home_score_pred"]} - {m["away_score_pred"]}</div>
        <div class="{hit_class}">{result_icon} {m["score"]:+.0f}</div>
      </div>
"""
    
    html += """    </div>
  </div>
</body>
</html>"""
    
    with open(DASHBOARD_DIR / "predictions_history.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"已生成預測歷史紀錄頁面")
    print(f"  總場次: {total}")
    print(f"  命中: {hits} ({hit_rate:.1f}%)")
    print(f"  總得分: {total_score:+.0f}")
    print(f"  待賽: {pending}")

if __name__ == "__main__":
    main()