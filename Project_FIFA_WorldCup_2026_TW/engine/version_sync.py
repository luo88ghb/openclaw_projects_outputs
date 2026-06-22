#!/usr/bin/env python3
"""
Project_FIFA_WorldCup_2026_TW 版本同步工具

用途：
- 以 dashboard/index.html 中的 <span id="version"> 為版本主幹（權威來源）。
- 自動校正 README.md、CHANGELOG.md、Technical_Report.md 頂端的版本註釋與標頭。
- 自動校正 dashboard/predictions_history.html 頂端的版本註釋。
- 在每次執行「下載」類動作時，由前端動態附加當時日期時間與版本資訊。

使用方式：
    python engine/version_sync.py              # 僅同步靜態文件
    python engine/version_sync.py --download dashboard/index.html  # 產生帶版本註釋的可下載副本
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r'v(\d+)\.(\d+)\.(\d+)')
VERSION_COMMENT_RE = re.compile(r'^<!--\s*下載時間：.*版本：.*-->\s*\n?', re.UNICODE)


def find_authoritative_version() -> str | None:
    """從 dashboard/index.html 的 #version span 抓取權威版本號。"""
    html = (BASE_DIR / 'dashboard' / 'index.html').read_text(encoding='utf-8')
    m = re.search(r'<span id="version">\s*(v\d+\.\d+\.\d+)\s*</span>', html)
    return m.group(1) if m else None


def make_version_comment(version: str, label: str = '下載時間') -> str:
    now = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
    return f'<!-- {label}: {now} Asia/Taipei | 版本: {version} -->\n'


def update_static_files(version: str, files: Iterable[Path]) -> dict[Path, bool]:
    """為指定文件更新/插入頂端版本註釋。"""
    results: dict[Path, bool] = {}
    for path in files:
        if not path.exists():
            results[path] = False
            continue
        text = path.read_text(encoding='utf-8')
        # 移除舊版本註釋（匹配簡體/繁體與全形/半形冒號）
        cleaned = re.sub(
            r'^<!--\s*下載時間[：:]\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[^|]*\|\s*版本[：:]\s*v\d+\.\d+\.\d+\s*-->\s*\n?',
            '',
            text,
            flags=re.UNICODE,
        )
        # 如果文件是 HTML，把版本註釋放在 <!DOCTYPE 之前一行
        new_comment = make_version_comment(version)
        if text.lstrip().lower().startswith('<!doctype'):
            new_text = new_comment + cleaned
        else:
            new_text = new_comment + cleaned
        path.write_text(new_text, encoding='utf-8')
        results[path] = True
    return results


def update_html_version_info(version: str) -> bool:
    """更新 dashboard/index.html 的 #last-update 時間戳。"""
    path = BASE_DIR / 'dashboard' / 'index.html'
    text = path.read_text(encoding='utf-8')
    now = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
    new_text, n = re.subn(
        r'(<span id="last-update">)[^<]*(</span>)',
        rf'\g<1>{now}（台北時間）</span>',
        text,
        count=1,
    )
    if n:
        path.write_text(new_text, encoding='utf-8')
        return True
    return False


def create_downloadable_copy(src: Path, version: str, dest: Path | None = None) -> Path:
    """為下載動作產生帶有版本/時間資訊的副本。"""
    text = src.read_text(encoding='utf-8')
    # 若是 HTML，把版本註釋插入到最頂端
    if src.suffix.lower() in ('.html', '.htm'):
        text = make_version_comment(version) + re.sub(
            r'^<!--\s*下載時間[：:]\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[^|]*\|\s*版本[：:]\s*v\d+\.\d+\.\d+\s*-->\s*\n?',
            '',
            text,
            flags=re.UNICODE,
        )
    else:
        # 純文字：頂端加一行 header
        header = make_version_comment(version, label='下載時間').replace('<!--', '#').replace('-->', '')
        text = header + text
    if dest is None:
        dest = src.with_stem(f'{src.stem}_download_{version}')
    dest.write_text(text, encoding='utf-8')
    return dest


def sync_all(version: str | None = None) -> dict:
    if version is None:
        version = find_authoritative_version()
        if not version:
            raise RuntimeError('無法從 dashboard/index.html 取得權威版本號')
    static_files = [
        BASE_DIR / 'README.md',
        BASE_DIR / 'CHANGELOG.md',
        BASE_DIR / 'Technical_Report.md',
        BASE_DIR / 'dashboard' / 'predictions_history.html',
    ]
    results = update_static_files(version, static_files)
    html_ok = update_html_version_info(version)
    return {'version': version, 'static': results, 'html_last_update': html_ok}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='同步專案版本標記')
    parser.add_argument('--version', help='指定版本號（預設從 dashboard/index.html 讀取）')
    parser.add_argument('--download', metavar='FILE', help='產生帶版本註釋的下載副本')
    parser.add_argument('--download-dest', metavar='PATH', help='下載副本輸出路徑')
    args = parser.parse_args(argv)

    version = args.version or find_authoritative_version()
    if not version:
        print('錯誤：無法取得權威版本號', file=sys.stderr)
        return 1

    if args.download:
        src = Path(args.download)
        dest = Path(args.download_dest) if args.download_dest else None
        out = create_downloadable_copy(src, version, dest)
        print(f'下載副本已產生：{out}')
        return 0

    result = sync_all(version)
    print(f'權威版本：{result["version"]}')
    for path, ok in result['static'].items():
        print(f'  {path.name}: {"已更新" if ok else "檔案不存在"}')
    print(f'  index.html last-update: {"已更新" if result["html_last_update"] else "未更新"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
