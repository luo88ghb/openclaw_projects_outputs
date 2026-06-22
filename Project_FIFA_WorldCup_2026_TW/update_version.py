"""
Update version stamp across project deliverables.
- Single source of truth: dashboard/index.html <span id="version">
- Propagates to README.md, CHANGELOG.md, Technical_Report.md, predictions_history.html,
  and adds/updates a top HTML comment with date/time/version in downloadable HTML/Markdown files.
"""
import re
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent

VERSION_FILES = {
    "source": BASE / "dashboard" / "index.html",
    "html_downloads": [
        BASE / "dashboard" / "index.html",
        BASE / "dashboard" / "predictions_history.html",
    ],
    "md_downloads": [
        BASE / "README.md",
        BASE / "CHANGELOG.md",
        BASE / "Technical_Report.md",
    ],
}

TAIPEI_TZ_NAME = "Asia/Taipei"


def get_version_from_index(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r'<span id="version">(v[\d.]+)</span>', text)
    if not m:
        raise ValueError(f"Could not find version in {path}")
    return m.group(1)


def update_last_update(path: Path, version: str, dt: datetime) -> None:
    text = path.read_text(encoding="utf-8")
    date_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    # Update HTML span
    if path.suffix == ".html":
        text = re.sub(
            r'<span id="last-update">[^<]*</span>',
            f'<span id="last-update">{date_str}（台北時間）</span>',
            text,
        )
        # Update / add top HTML comment
        comment = f"<!-- 下載時間: {date_str} {TAIPEI_TZ_NAME} | 版本: {version} -->"
        if text.lstrip().startswith("<!--"):
            text = re.sub(r"^<!--.*?-->", comment, text, count=1)
        else:
            text = comment + "\n" + text

    # Update Markdown top comment
    elif path.suffix == ".md":
        comment = f"<!-- 下載時間: {date_str} {TAIPEI_TZ_NAME} | 版本: {version} -->"
        if text.lstrip().startswith("<!--"):
            text = re.sub(r"^<!--.*?-->", comment, text, count=1)
        else:
            text = comment + "\n" + text
        # Update explicit version line
        text = re.sub(
            r"\*\*版本\*\*: v[\d.]+",
            f"**版本**: {version}",
            text,
        )
        text = re.sub(
            r"\*\*更新日期\*\*: \d{4}-\d{2}-\d{2}",
            f"**更新日期**: {dt.strftime('%Y-%m-%d')}",
            text,
        )

    path.write_text(text, encoding="utf-8")


def add_changelog_entry(version: str, dt: datetime) -> None:
    path = BASE / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    header = f"## [{version.lstrip('v')}] - {dt.strftime('%Y-%m-%d')}"
    if header in text:
        return
    new_entry = (
        f"{header}\n\n### 雜項\n- 統一版本標記與下載時間戳。\n\n"
    )
    text = text.replace("## [", new_entry + "## [", 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    now = datetime.now()
    version = get_version_from_index(VERSION_FILES["source"])
    print(f"Detected version: {version}")

    for path in VERSION_FILES["html_downloads"] + VERSION_FILES["md_downloads"]:
        update_last_update(path, version, now)
        print(f"Updated {path.name}")

    add_changelog_entry(version, now)
    print(f"Added CHANGELOG entry for {version}")


if __name__ == "__main__":
    main()
