#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

from agentic_researcher.config import load_config, resolve_path
from agentic_researcher.workflow import today_label


def collect_pdf_snapshot(pdf_root: Path) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    if not pdf_root.exists():
        return snapshot
    for path in sorted(pdf_root.rglob("*.pdf")):
        stat = path.stat()
        snapshot[str(path.resolve())] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def infer_dates_from_paths(paths: list[str], fallback_date: str) -> list[str]:
    dates = set()
    for raw_path in paths:
        path = Path(raw_path)
        for part in path.parts:
            match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", part)
            if not match:
                continue
            year, month, day = match.groups()
            dates.add(f"{year}-{int(month):02d}-{int(day):02d}")
    if not dates:
        dates.add(fallback_date)
    return sorted(dates)


def refresh_date(date_label: str, config_path: str) -> int:
    command = [sys.executable, str(Path(__file__).resolve().parent / "refresh_notes.py"), "--date", date_label]
    if config_path:
        command.extend(["--config", config_path])
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch data/zotero_pdf and refresh notes when new PDFs arrive.")
    parser.add_argument("--date", default="", help="Fallback date to refresh if no date folder is inferred.")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds.")
    parser.add_argument("--refresh-on-start", action="store_true", help="Refresh once on startup.")
    args = parser.parse_args()

    config = load_config(args.config)
    pdf_root = resolve_path(config, config["paths"]["zotero_pdf_root"])
    fallback_date = today_label(args.date)
    snapshot = collect_pdf_snapshot(pdf_root)

    if args.refresh_on_start:
        for date_label in infer_dates_from_paths(list(snapshot.keys()), fallback_date):
            refresh_date(date_label, args.config)

    print(f"Watching {pdf_root} every {args.interval}s")
    while True:
        time.sleep(max(3, args.interval))
        current = collect_pdf_snapshot(pdf_root)
        changed_paths = [path for path, meta in current.items() if snapshot.get(path) != meta]
        if changed_paths:
            affected_dates = infer_dates_from_paths(changed_paths, fallback_date)
            for date_label in affected_dates:
                print(f"Detected {len(changed_paths)} PDF change(s); refreshing notes for {date_label}")
                refresh_date(date_label, args.config)
        snapshot = current


if __name__ == "__main__":
    raise SystemExit(main())
