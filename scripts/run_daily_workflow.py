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
from agentic_researcher.models import PaperRecord
from agentic_researcher.scoring import command_score_papers, heuristic_score_papers, openai_score_papers
from agentic_researcher.workflow import (
    save_candidates_bundle,
    save_scored_bundle,
    today_label,
    write_confirmed_bundle,
    write_daily_report,
)


def _discover(args: argparse.Namespace, config: dict) -> list[PaperRecord]:
    whitelist = config["discovery"]["venue_whitelist"]
    source = args.source or config["discovery"]["provider"]
    if source == "fixture":
        input_path = Path(args.input or config["discovery"]["fixture_path"])
        return load_fixture_candidates(input_path, whitelist)
    if source == "crossref":
        return search_crossref(args.query, whitelist, rows=args.rows)
    if source == "ris":
        return load_candidates_from_ris(Path(args.input), whitelist)
    if source == "csv":
        return load_candidates_from_csv(Path(args.input), whitelist)
    raise SystemExit(f"Unsupported source: {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full daily Agentic Researcher workflow.")
    parser.add_argument("--query", required=True, help="关键词。")
    parser.add_argument("--source", default="", choices=["", "fixture", "crossref", "ris", "csv"])
    parser.add_argument("--input", default="", help="RIS/CSV/fixture 输入文件。")
    parser.add_argument("--top", type=int, default=10, help="自动确认前 N 篇。")
    parser.add_argument("--rows", type=int, default=50, help="Crossref 拉取条数。")
    parser.add_argument("--date", default="", help="覆盖日期。")
    parser.add_argument("--config", default="", help="配置文件路径。")
    args = parser.parse_args()

    config = load_config(args.config)
    date_label = today_label(args.date)

    papers = _discover(args, config)
    history = load_workspace_history(config)
    new_papers: list[PaperRecord] = []
    duplicate_count = 0
    for paper in papers:
        is_duplicate, reason = check_duplicate(paper, history)
        if is_duplicate:
            duplicate_count += 1
            paper.duplicate_status = "duplicate"
            paper.duplicate_reason = reason
            continue
        paper.duplicate_status = "new"
        new_papers.append(paper)

    discovery_outputs = save_candidates_bundle(config, args.query, date_label, new_papers)

    history = load_workspace_history(config)
    deduped: list[PaperRecord] = []
    for paper in new_papers:
        is_duplicate, reason = check_duplicate(paper, history)
        paper.duplicate_status = "duplicate" if is_duplicate else "new"
        paper.duplicate_reason = reason
        if not is_duplicate:
            deduped.append(paper)

    provider = config["llm"]["provider"]
    if provider == "openai":
        scored = openai_score_papers(deduped, args.query, config["openai"])
    elif provider == "command" and config["llm"]["command"]:
        scored = command_score_papers(deduped, args.query, config["llm"]["command"])
    else:
        scored = heuristic_score_papers(deduped, args.query)
    scored = scored[: int(config.get("candidate_pool_size", 25))]
    scored_outputs = save_scored_bundle(config, args.query, date_label, scored)

    confirmed = scored[: args.top]
    confirmed_outputs = write_confirmed_bundle(config, args.query, date_label, confirmed)
    report_path = write_daily_report(config, args.query, date_label, confirmed)

    print(f"发现到 {len(new_papers)} 篇新文献，过滤历史重复 {duplicate_count} 篇")
    print(f"内部 Bundle JSON: {discovery_outputs['bundle_json']}")
    print(f"候选 Markdown: {discovery_outputs['candidates_md']}")
    print(f"更新后 Bundle JSON: {scored_outputs['bundle_json']}")
    print(f"候选 Markdown: {scored_outputs['candidates_md']}")
    print(f"确认结果: {confirmed_outputs['confirmed_json']}")
    print(f"日报: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
