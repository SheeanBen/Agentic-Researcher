#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agentic_researcher.config import load_config
from agentic_researcher.models import PaperRecord
from agentic_researcher.workflow import load_bundle, today_label, write_confirmed_bundle, write_daily_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh confirmed notes and daily report after PDFs sync into zotero_pdf.")
    parser.add_argument("--input", default="", help="Optional path to confirmed JSON.")
    parser.add_argument("--date", default="", help="Override date (YYYY-MM-DD).")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    args = parser.parse_args()

    config = load_config(args.config)
    explicit_date = args.date
    date_label = today_label(explicit_date)
    input_path = Path(args.input) if args.input else Path(config["paths"]["confirmed_root"]) / f"{date_label}.json"
    confirmed_path = input_path
    if not confirmed_path.is_absolute():
        from agentic_researcher.config import resolve_path

        confirmed_path = resolve_path(config, str(confirmed_path))

    bundle = load_bundle(confirmed_path)
    if not explicit_date:
        date_label = today_label(bundle.get("date", ""))
    query = bundle.get("query", "")
    papers = [PaperRecord.from_dict(record) for record in bundle.get("papers", [])]
    outputs = write_confirmed_bundle(config, query, date_label, papers)
    report_path = write_daily_report(config, query, date_label, papers)
    print(f"Refreshed {len(papers)} papers")
    print(f"Confirmed JSON: {outputs['confirmed_json']}")
    print(f"Daily report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
