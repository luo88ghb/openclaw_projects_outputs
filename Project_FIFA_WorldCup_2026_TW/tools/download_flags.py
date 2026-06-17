import json
import urllib.request
import os
import ssl

# Disable SSL verification for some servers
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = r"C:\Users\danny\.openclaw\workspace\projects\Project_FIFA_WorldCup_2026_TW"
FLAGS_DIR = os.path.join(BASE, "dashboard", "flags")
TEAMS_PATH = os.path.join(BASE, "data", "teams.json")

# Country code to Wikipedia flag filename (commons)
# Using direct PNG thumbnails from Wikimedia Commons for each flag
FLAG_URLS = {
    "MEX": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Flag_of_Mexico.svg/120px-Flag_of_Mexico.svg.png",
    "RSA": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/Flag_of_South_Africa.svg/120px-Flag_of_South_Africa.svg.png",
    "KOR": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Flag_of_South_Korea.svg/120px-Flag_of_South_Korea.svg.png",
    "CAN": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Flag_of_Canada_%28Pantone%29.svg/120px-Flag_of_Canada_%28Pantone%29.svg.png",
    "QAT": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Flag_of_Qatar.svg/120px-Flag_of_Qatar.svg.png",
    "SUI": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Flag_of_Switzerland.svg/120px-Flag_of_Switzerland.svg.png",
    "BRA": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Flag_of_Brazil.svg/120px-Flag_of_Brazil.svg.png",
    "MAR": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Flag_of_Morocco.svg/120px-Flag_of_Morocco.svg.png",
    "HAI": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Flag_of_Haiti.svg/120px-Flag_of_Haiti.svg.png",
    "SCO": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Flag_of_Scotland.svg/120px-Flag_of_Scotland.svg.png",
    "USA": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Flag_of_the_United_States.svg/120px-Flag_of_the_United_States.svg.png",
    "PAR": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Flag_of_Paraguay.svg/120px-Flag_of_Paraguay.svg.png",
    "AUS": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Flag_of_Australia_%28converted%29.svg/120px-Flag_of_Australia_%28converted%29.svg.png",
    "GER": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Flag_of_Germany.svg/120px-Flag_of_Germany.svg.png",
    "CIV": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fe/Flag_of_C%C3%B4te_d%27Ivoire.svg/120px-Flag_of_C%C3%B4te_d%27Ivoire.svg.png",
    "ECU": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Flag_of_Ecuador.svg/120px-Flag_of_Ecuador.svg.png",
    "CUW": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Flag_of_Cura%C3%A7ao.svg/120px-Flag_of_Cura%C3%A7ao.svg.png",
    "NED": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/Flag_of_the_Netherlands.svg/120px-Flag_of_the_Netherlands.svg.png",
    "JPN": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Flag_of_Japan.svg/120px-Flag_of_Japan.svg.png",
    "TUN": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Flag_of_Tunisia.svg/120px-Flag_of_Tunisia.svg.png",
    "ESP": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Flag_of_Spain.svg/120px-Flag_of_Spain.svg.png",
    "CPV": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Flag_of_Cape_Verde.svg/120px-Flag_of_Cape_Verde.svg.png",
    "KSA": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/Flag_of_Saudi_Arabia.svg/120px-Flag_of_Saudi_Arabia.svg.png",
    "URU": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fe/Flag_of_Uruguay.svg/120px-Flag_of_Uruguay.svg.png",
    "BEL": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Flag_of_Belgium.svg/120px-Flag_of_Belgium.svg.png",
    "EGY": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fe/Flag_of_Egypt.svg/120px-Flag_of_Egypt.svg.png",
    "IRN": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Flag_of_Iran.svg/120px-Flag_of_Iran.svg.png",
    "NZL": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Flag_of_New_Zealand.svg/120px-Flag_of_New_Zealand.svg.png",
    "FRA": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Flag_of_France.svg/120px-Flag_of_France.svg.png",
    "SEN": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/Flag_of_Senegal.svg/120px-Flag_of_Senegal.svg.png",
    "NOR": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Flag_of_Norway.svg/120px-Flag_of_Norway.svg.png",
    "ARG": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Flag_of_Argentina.svg/120px-Flag_of_Argentina.svg.png",
    "ALG": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Flag_of_Algeria.svg/120px-Flag_of_Algeria.svg.png",
    "AUT": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Flag_of_Austria.svg/120px-Flag_of_Austria.svg.png",
    "JOR": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Flag_of_Jordan.svg/120px-Flag_of_Jordan.svg.png",
    "POR": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Flag_of_Portugal.svg/120px-Flag_of_Portugal.svg.png",
    "UZB": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Flag_of_Uzbekistan.svg/120px-Flag_of_Uzbekistan.svg.png",
    "COL": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Flag_of_Colombia.svg/120px-Flag_of_Colombia.svg.png",
    "ENG": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Flag_of_England.svg/120px-Flag_of_England.svg.png",
    "CRO": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Flag_of_Croatia.svg/120px-Flag_of_Croatia.svg.png",
    "GHA": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Flag_of_Ghana.svg/120px-Flag_of_Ghana.svg.png",
    "PAN": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Flag_of_Panama.svg/120px-Flag_of_Panama.svg.png",
    "CZE": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Flag_of_the_Czech_Republic.svg/120px-Flag_of_the_Czech_Republic.svg.png",
    "BIH": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/Flag_of_Bosnia_and_Herzegovina.svg/120px-Flag_of_Bosnia_and_Herzegovina.svg.png",
    "TUR": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Flag_of_Turkey.svg/120px-Flag_of_Turkey.svg.png",
    "SWE": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Flag_of_Sweden.svg/120px-Flag_of_Sweden.svg.png",
    "IRQ": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Flag_of_Iraq.svg/120px-Flag_of_Iraq.svg.png",
    "COD": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Flag_of_the_Democratic_Republic_of_the_Congo.svg/120px-Flag_of_the_Democratic_Republic_of_the_Congo.svg.png",
}

# Country code to flag emoji
FLAG_EMOJIS = {
    "MEX": "🇲🇽", "RSA": "🇿🇦", "KOR": "🇰🇷", "CAN": "🇨🇦", "QAT": "🇶🇦", "SUI": "🇨🇭",
    "BRA": "🇧🇷", "MAR": "🇲🇦", "HAI": "🇭🇹", "SCO": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "USA": "🇺🇸", "PAR": "🇵🇾",
    "AUS": "🇦🇺", "GER": "🇩🇪", "CIV": "🇨🇮", "ECU": "🇪🇨", "CUW": "🇨🇼", "NED": "🇳🇱",
    "JPN": "🇯🇵", "TUN": "🇹🇳", "ESP": "🇪🇸", "CPV": "🇨🇻", "KSA": "🇸🇦", "URU": "🇺🇾",
    "BEL": "🇧🇪", "EGY": "🇪🇬", "IRN": "🇮🇷", "NZL": "🇳🇿", "FRA": "🇫🇷", "SEN": "🇸🇳",
    "NOR": "🇳🇴", "ARG": "🇦🇷", "ALG": "🇩🇿", "AUT": "🇦🇹", "JOR": "🇯🇴", "POR": "🇵🇹",
    "UZB": "🇺🇿", "COL": "🇨🇴", "ENG": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "CRO": "🇭🇷", "GHA": "🇬🇭", "PAN": "🇵🇦",
    "CZE": "🇨🇿", "BIH": "🇧🇦", "TUR": "🇹🇷", "SWE": "🇸🇪", "IRQ": "🇮🇶", "COD": "🇨🇩",
}

# Country code to Wikipedia-style filename
FLAG_FILENAMES = {
    "MEX": "Flag_of_Mexico.png",
    "RSA": "Flag_of_South_Africa.png",
    "KOR": "Flag_of_South_Korea.png",
    "CAN": "Flag_of_Canada.png",
    "QAT": "Flag_of_Qatar.png",
    "SUI": "Flag_of_Switzerland.png",
    "BRA": "Flag_of_Brazil.png",
    "MAR": "Flag_of_Morocco.png",
    "HAI": "Flag_of_Haiti.png",
    "SCO": "Flag_of_Scotland.png",
    "USA": "Flag_of_the_United_States.png",
    "PAR": "Flag_of_Paraguay.png",
    "AUS": "Flag_of_Australia.png",
    "GER": "Flag_of_Germany.png",
    "CIV": "Flag_of_Ivory_Coast.png",
    "ECU": "Flag_of_Ecuador.png",
    "CUW": "Flag_of_Curacao.png",
    "NED": "Flag_of_the_Netherlands.png",
    "JPN": "Flag_of_Japan.png",
    "TUN": "Flag_of_Tunisia.png",
    "ESP": "Flag_of_Spain.png",
    "CPV": "Flag_of_Cape_Verde.png",
    "KSA": "Flag_of_Saudi_Arabia.png",
    "URU": "Flag_of_Uruguay.png",
    "BEL": "Flag_of_Belgium.png",
    "EGY": "Flag_of_Egypt.png",
    "IRN": "Flag_of_Iran.png",
    "NZL": "Flag_of_New_Zealand.png",
    "FRA": "Flag_of_France.png",
    "SEN": "Flag_of_Senegal.png",
    "NOR": "Flag_of_Norway.png",
    "ARG": "Flag_of_Argentina.png",
    "ALG": "Flag_of_Algeria.png",
    "AUT": "Flag_of_Austria.png",
    "JOR": "Flag_of_Jordan.png",
    "POR": "Flag_of_Portugal.png",
    "UZB": "Flag_of_Uzbekistan.png",
    "COL": "Flag_of_Colombia.png",
    "ENG": "Flag_of_England.png",
    "CRO": "Flag_of_Croatia.png",
    "GHA": "Flag_of_Ghana.png",
    "PAN": "Flag_of_Panama.png",
    "CZE": "Flag_of_the_Czech_Republic.png",
    "BIH": "Flag_of_Bosnia_and_Herzegovina.png",
    "TUR": "Flag_of_Turkey.png",
    "SWE": "Flag_of_Sweden.png",
    "IRQ": "Flag_of_Iraq.png",
    "COD": "Flag_of_the_Democratic_Republic_of_the_Congo.png",
}

import time

def download_flag(code, url, filename):
    path = os.path.join(FLAGS_DIR, filename)
    if os.path.exists(path):
        print(f"[SKIP] {code}: {filename} already exists")
        return True
    for attempt in range(4):
        try:
            time.sleep(0.8)  # slow down to avoid 429
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read()
            with open(path, "wb") as f:
                f.write(data)
            print(f"[OK] {code}: downloaded {filename} ({len(data)} bytes)")
            return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 + attempt * 5
                print(f"[RETRY] {code}: 429, waiting {wait}s (attempt {attempt+1})")
                time.sleep(wait)
            else:
                print(f"[FAIL] {code}: {e} (attempt {attempt+1})")
                time.sleep(2)
        except Exception as e:
            print(f"[FAIL] {code}: {e} (attempt {attempt+1})")
            time.sleep(2)
    return False

def main():
    os.makedirs(FLAGS_DIR, exist_ok=True)
    with open(TEAMS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    teams = data["teams"]

    results = {"ok": [], "fail": []}
    for team in teams:
        code = team["id"]
        ok = download_flag(code, FLAG_URLS[code], FLAG_FILENAMES[code])
        if ok:
            results["ok"].append(code)
            team["flag"] = FLAG_EMOJIS[code]
            team["flag_img"] = f"flags/{FLAG_FILENAMES[code]}"
        else:
            results["fail"].append(code)

    with open(TEAMS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nTotal OK: {len(results['ok'])}, Fail: {len(results['fail'])}")
    if results["fail"]:
        print("Failed codes:", results["fail"])

if __name__ == "__main__":
    main()
