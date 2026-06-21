"""
同步 matches_104.json 與 phase_predictions.json 的預測結果。
讓儀表板顯示與 Telegram 推播一致。
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DIR = BASE_DIR / "predictions"

def main():
    # 載入資料
    with open(DATA_DIR / "matches_104.json", "r", encoding="utf-8") as f:
        matches_data = json.load(f)
    
    with open(PREDICTIONS_DIR / "phase_predictions.json", "r", encoding="utf-8") as f:
        phase_data = json.load(f)
    
    # 建立 phase_predictions 的 match_id -> prediction 映射
    phase_map = {}
    for m in phase_data.get("all_matches", []):
        phase_map[m["match_id"]] = m
    
    changes = 0
    
    # 同步預測
    for m in matches_data["matches"]:
        mid = m["match_id"]
        if mid in phase_map:
            phase_pred = phase_map[mid]
            if "predicted_home_score" in phase_pred and "predicted_away_score" in phase_pred:
                # 更新 matches_104.json 中的預測
                if "prediction" not in m:
                    m["prediction"] = {}
                
                old_home = m["prediction"].get("home_score_pred")
                old_away = m["prediction"].get("away_score_pred")
                new_home = phase_pred["predicted_home_score"]
                new_away = phase_pred["predicted_away_score"]
                
                if old_home != new_home or old_away != new_away:
                    m["prediction"]["home_score_pred"] = new_home
                    m["prediction"]["away_score_pred"] = new_away
                    print(f"#{mid} 預測更新: {old_home}-{old_away} -> {new_home}-{new_away}")
                    changes += 1
    
    if changes > 0:
        # 備份原檔
        import shutil
        backup_path = DATA_DIR / "matches_104.json.bak_sync"
        shutil.copy(DATA_DIR / "matches_104.json", backup_path)
        
        # 寫入新檔
        with open(DATA_DIR / "matches_104.json", "w", encoding="utf-8") as f:
            json.dump(matches_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n已同步 {changes} 場預測，原檔備份於 {backup_path}")
    else:
        print("所有預測已一致，無需同步")

if __name__ == "__main__":
    main()