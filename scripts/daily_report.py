#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agentic_researcher.config import load_config
from agentic_researcher.models import PaperRecord
from agentic_researcher.workflow import load_bundle, today_label, write_daily_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the daily research report from confirmed papers.")
    parser.add_argument("--input", required=True, help="Path to confirmed bundle JSON.")
    parser.add_argument("--date", default="", help="Override run date (YYYY-MM-DD).")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    args = parser.parse_args()

    config = load_config(args.config)
    bundle = load_bundle(Path(args.input))
    date_label = today_label(args.date or bundle.get("date", ""))
    papers = [PaperRecord.from_dict(record) for record in bundle.get("papers", [])]
    report_path = write_daily_report(config, bundle.get("query", ""), date_label, papers)
    print(f"Daily report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

