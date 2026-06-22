from pathlib import Path

files = [
    ("Technical_Report.md", 3),
    ("README.md", 3),
    ("CHANGELOG.md", 7),
    ("dashboard/index.html", 7),
    ("dashboard/predictions_history.html", 1),
]

base = Path(__file__).resolve().parent

for name, lines in files:
    p = base / name
    print(f"=== {name} ===")
    if not p.exists():
        print("(missing)")
        continue
    text = p.read_text(encoding="utf-8")
    print("".join(text.splitlines(keepends=True)[:lines]))
    print()
