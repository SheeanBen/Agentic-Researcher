#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agentic_researcher.config import load_config
from agentic_researcher.models import PaperRecord
from agentic_researcher.workflow import load_bundle, today_label, write_confirmed_bundle


def _load_selected_ids(args: argparse.Namespace, paper_ids: list[str]) -> list[str]:
    if args.ids:
        return [item.strip() for item in args.ids.split(",") if item.strip()]
    if args.selection_file:
        path = Path(args.selection_file)
        if path.suffix.lower() == ".json":
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return [str(item) for item in payload]
            return [str(item) for item in payload.get("ids", [])]
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.top:
        return paper_ids[: args.top]
    raise SystemExit("Provide --ids, --selection-file, or --top.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Confirm today's final reading set and generate Obsidian notes.")
    parser.add_argument("--input", required=True, help="Path to bundle.json.")
    parser.add_argument("--ids", default="", help="Comma-separated paper IDs to confirm.")
    parser.add_argument("--selection-file", default="", help="Optional file with selected IDs.")
    parser.add_argument("--top", type=int, default=0, help="Confirm the top N scored papers.")
    parser.add_argument("--date", default="", help="Override run date (YYYY-MM-DD).")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    args = parser.parse_args()

    config = load_config(args.config)
    bundle = load_bundle(Path(args.input))
    query = bundle.get("query", "")
    date_label = today_label(args.date or bundle.get("date", ""))
    papers = [PaperRecord.from_dict(record) for record in bundle.get("papers", [])]
    paper_ids = [paper.id for paper in papers]
    selected_ids = set(_load_selected_ids(args, paper_ids))
    confirmed = [paper for paper in papers if paper.id in selected_ids]
    if not confirmed:
        raise SystemExit("No papers were confirmed.")
    outputs = write_confirmed_bundle(config, query, date_label, confirmed)
    print(f"Confirmed {len(confirmed)} papers")
    print(f"Confirmed JSON: {outputs['confirmed_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
