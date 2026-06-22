#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version bump script for Project_FIFA_WorldCup_2026_TW.

Rules:
- index.html is the authoritative source for the current version and last-update
  datetime (Asia/Taipei). The script reads those values from index.html.
- Other files are corrected to match index.html.
- Downloaded files get a header line with date/time/version stamp if they don't
  already have one.

Usage:
    python tools/bump_version.py
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_INFO_ID = "version-info"
VERSION_SPAN_ID = "version"
LAST_UPDATE_SPAN_ID = "last-update"

# Files to synchronise. Each entry: (relative_path, regex_pattern, replacement_template)
# Templates can use {version} and {date} and {datetime}.
# For HTML/JS we use literal replacement of known strings via regex capture.
SYNC_TARGETS = [
    # index.html is authoritative; only read, not written by this list.
    # README.md
    (
        "README.md",
        r"(\*\*版本\*\*:\s*)v2\.2\.\d+",
        r"\g<1>{version}",
    ),
    (
        "README.md",
        r"(\*\*更新日期\*\*:\s*)\d{4}-\d{2}-\d{2}",
        r"\g<1>{date}",
    ),
    # Technical_Report.md
    (
        "Technical_Report.md",
        r"(\*\*版本\*\*:\s*)v2\.2\.\d+",
        r"\g<1>{version}",
    ),
    (
        "Technical_Report.md",
        r"(\*\*日期\*\*:\s*)\d{4}-\d{2}-\d{2}",
        r"\g<1>{date}",
    ),
    # engine/server.py
    (
        "engine/server.py",
        r'("version":\s*)"v2\.2\.\d+"',
        r'\g<1>"{version}"',
    ),
]

DOWNLOAD_HEADER_PREFIXES = {
    ".md": "<!--",
    ".txt": "#",
    ".html": "<!--",
}
DOWNLOAD_HEADER_SUFFIXES = {
    ".md": "-->",
    ".txt": "",
    ".html": "-->",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def parse_index_html() -> tuple[str, str]:
    html = read_text(PROJECT_ROOT / "dashboard" / "index.html")
    version_match = re.search(
        rf'<span\s+id="{VERSION_SPAN_ID}">\s*(v2\.2\.\d+)\s*</span>',
        html,
        re.IGNORECASE,
    )
    if not version_match:
        raise RuntimeError("Could not find version span in dashboard/index.html")
    version = version_match.group(1)
    last_update_match = re.search(
        rf'<span\s+id="{LAST_UPDATE_SPAN_ID}">\s*([^\n<]+?)\s*</span>',
        html,
        re.IGNORECASE,
    )
    if not last_update_match:
        raise RuntimeError("Could not find last-update span in dashboard/index.html")
    last_update_raw = last_update_match.group(1).strip()
    # Try to extract YYYY-MM-DD
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", last_update_raw)
    if not date_match:
        raise RuntimeError(f"Could not parse date from last-update: {last_update_raw}")
    return version, date_match.group(1)


def bump_file(path: Path, pattern: str, replacement: str, version: str, date: str, dt: str) -> bool:
    text = read_text(path)
    new_text = re.sub(pattern, replacement.format(version=version, date=date, datetime=dt), text)
    if new_text != text:
        write_text(path, new_text)
        return True
    return False


def add_download_header(path: Path, version: str, dt: str) -> bool:
    """
    For files that might be downloaded (e.g. report .md/.txt/.html), ensure the
    top of the file has exactly one date/time/version stamp.
    """
    ext = path.suffix.lower()
    if ext not in DOWNLOAD_HEADER_PREFIXES:
        return False
    text = read_text(path)
    prefix = DOWNLOAD_HEADER_PREFIXES[ext]
    suffix = DOWNLOAD_HEADER_SUFFIXES[ext]
    stamp = f"{prefix} 下載時間: {dt} Asia/Taipei | 版本: {version} {suffix}"
    # Find any existing stamp line at the very top of the file
    existing_pattern = re.compile(
        rf"^{re.escape(prefix)}\s*下載時間:\s*\d{{4}}-\d{{2}}-\d{{2}}.*?{re.escape(suffix)}\n?",
        re.MULTILINE,
    )
    text, count = existing_pattern.subn("", text, count=1)
    # Also remove stale versions with different version numbers at top
    stale_pattern = re.compile(
        rf"^{re.escape(prefix)}\s*下載時間:.*?版本:\s*v2\.2\.\d+\s*{re.escape(suffix)}\n?",
        re.MULTILINE,
    )
    text, stale_count = stale_pattern.subn("", text)
    # Insert fresh stamp at top (after frontmatter for markdown)
    if ext == ".md" and text.startswith("---"):
        end_fm = text.find("---", 3)
        if end_fm != -1:
            insert_pos = end_fm + 3
            if text[insert_pos] == "\n":
                insert_pos += 1
            new_text = text[:insert_pos] + stamp + "\n" + text[insert_pos:]
        else:
            new_text = stamp + "\n" + text
    else:
        new_text = stamp + "\n" + text
    if new_text != text or count or stale_count:
        write_text(path, new_text)
        return True
    return False


def update_index_html(version: str, date: str, dt: str) -> None:
    """
    Keep index.html authoritative; optionally update its last-update time to now.
    This is separate from the sync targets and is called explicitly when bumping.
    """
    path = PROJECT_ROOT / "dashboard" / "index.html"
    text = read_text(path)
    # Update version span (should already be current)
    new_text = re.sub(
        rf'(<span\s+id="{VERSION_SPAN_ID}">)\s*v2\.2\.\d+\s*(</span>)',
        rf"\g<1>{version}\g<2>",
        text,
        flags=re.IGNORECASE,
    )
    # Update last-update span to now
    taipei_str = f"{dt}（台北時間）"
    new_text = re.sub(
        rf'(<span\s+id="{LAST_UPDATE_SPAN_ID}">)\s*[^<]+\s*(</span>)',
        rf"\g<1>{taipei_str}\g<2>",
        new_text,
        flags=re.IGNORECASE,
    )
    if new_text != text:
        write_text(path, new_text)
        print(f"[updated] {path.relative_to(PROJECT_ROOT)}")
    else:
        print(f"[ok]      {path.relative_to(PROJECT_ROOT)}")


def main() -> int:
    try:
        version, date = parse_index_html()
    except RuntimeError as e:
        print(f"Error parsing index.html: {e}")
        return 1

    # We want today's date (Taipei) for README/Technical_Report, not the old date from index.html.
    now = datetime.now().astimezone()
    date = now.strftime("%Y-%m-%d")
    dt = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Authoritative version: {version}")
    print(f"Authoritative date: {date}")
    print(f"Current stamp datetime: {dt}")

    update_index_html(version, date, dt)

    for rel, pattern, replacement in SYNC_TARGETS:
        path = PROJECT_ROOT / rel
        if not path.exists():
            print(f"[skip]    {rel} (not found)")
            continue
        changed = bump_file(path, pattern, replacement, version, date, dt)
        status = "[updated]" if changed else "[ok]     "
        print(f"{status} {rel}")

    # Add download headers to exported/downloadable reports
    for report in [
        "Technical_Report.md",
        "README.md",
        "CHANGELOG.md",
        "predictions/Advanced_Prediction_Report.md",
        "data/WorldCup2026_預測_32強.txt",
        "data/WorldCup2026_預測_16強.txt",
        "data/WorldCup2026_預測_8強.txt",
        "data/WorldCup2026_預測_4強.txt",
        "data/WorldCup2026_預測_冠亞季軍.txt",
    ]:
        path = PROJECT_ROOT / report
        if path.exists():
            changed = add_download_header(path, version, dt)
            status = "[stamped]" if changed else "[ok]      "
            print(f"{status} {report}")

    print("\nDone. Review changes before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
