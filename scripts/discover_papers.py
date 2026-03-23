#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agentic_researcher.config import load_config
from agentic_researcher.discovery import (
    load_candidates_from_csv,
    load_candidates_from_ris,
    load_fixture_candidates,
    search_crossref,
)
from agentic_researcher.history import check_duplicate, load_workspace_history
from agentic_researcher.workflow import save_candidates_bundle, today_label


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover candidate papers for the daily reading queue.")
    parser.add_argument("--query", default="", help="Keyword query used for discovery and ranking.")
    parser.add_argument("--source", default="", choices=["", "fixture", "crossref", "ris", "csv"])
    parser.add_argument("--input", default="", help="Optional source file when using ris/csv/fixture.")
    parser.add_argument("--date", default="", help="Override run date (YYYY-MM-DD).")
    parser.add_argument("--rows", type=int, default=50, help="Rows to fetch for Crossref discovery.")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    args = parser.parse_args()

    config = load_config(args.config)
    whitelist = config["discovery"]["venue_whitelist"]
    date_label = today_label(args.date)
    source = args.source or config["discovery"]["provider"]

    if source == "fixture":
        input_path = Path(args.input or config["discovery"]["fixture_path"])
        papers = load_fixture_candidates(input_path, whitelist)
    elif source == "crossref":
        if not args.query:
            raise SystemExit("--query is required for Crossref discovery.")
        papers = search_crossref(args.query, whitelist, rows=args.rows)
    elif source == "ris":
        if not args.input:
            raise SystemExit("--input is required for RIS discovery.")
        papers = load_candidates_from_ris(Path(args.input), whitelist)
    elif source == "csv":
        if not args.input:
            raise SystemExit("--input is required for CSV discovery.")
        papers = load_candidates_from_csv(Path(args.input), whitelist)
    else:
        raise SystemExit(f"Unsupported source: {source}")

    history = load_workspace_history(config)
    deduped = []
    duplicate_count = 0
    for paper in papers:
        is_duplicate, reason = check_duplicate(paper, history)
        if is_duplicate:
            duplicate_count += 1
            paper.duplicate_status = "duplicate"
            paper.duplicate_reason = reason
            continue
        paper.duplicate_status = "new"
        deduped.append(paper)

    bundle = save_candidates_bundle(config, args.query, date_label, deduped)
    print(f"Discovered {len(deduped)} new papers")
    print(f"Filtered {duplicate_count} previously seen papers from workspace history")
    print(f"Bundle JSON: {bundle['bundle_json']}")
    print(f"Candidates Markdown: {bundle['candidates_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
