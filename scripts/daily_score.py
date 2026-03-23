#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from agentic_researcher.config import load_config
from agentic_researcher.history import check_duplicate, load_workspace_history
from agentic_researcher.models import PaperRecord
from agentic_researcher.scoring import command_score_papers, heuristic_score_papers, openai_score_papers
from agentic_researcher.workflow import load_bundle, save_scored_bundle, today_label


def main() -> int:
    parser = argparse.ArgumentParser(description="Score and rank candidate papers for daily confirmation.")
    parser.add_argument("--input", required=True, help="Path to bundle.json.")
    parser.add_argument("--query", default="", help="Optional explicit query override.")
    parser.add_argument("--date", default="", help="Override run date (YYYY-MM-DD).")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    args = parser.parse_args()

    config = load_config(args.config)
    bundle = load_bundle(Path(args.input))
    query = args.query or bundle.get("query", "")
    date_label = today_label(args.date or bundle.get("date", ""))
    papers = [PaperRecord.from_dict(record) for record in bundle.get("papers", [])]

    history = load_workspace_history(config, exclude_paths=[Path(args.input)])
    deduped = []
    for paper in papers:
        is_duplicate, reason = check_duplicate(paper, history)
        paper.duplicate_status = "duplicate" if is_duplicate else "new"
        paper.duplicate_reason = reason
        if not is_duplicate:
            deduped.append(paper)

    provider = config["llm"]["provider"]
    if provider == "openai":
        scored = openai_score_papers(deduped, query, config["openai"])
    elif provider == "command" and config["llm"]["command"]:
        scored = command_score_papers(deduped, query, config["llm"]["command"])
    else:
        scored = heuristic_score_papers(deduped, query)

    limit = int(config.get("candidate_pool_size", 25))
    scored = scored[:limit]
    bundle_paths = save_scored_bundle(config, query, date_label, scored)
    print(f"Scored {len(scored)} non-duplicate papers")
    print(f"Bundle JSON: {bundle_paths['bundle_json']}")
    print(f"Candidates Markdown: {bundle_paths['candidates_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
