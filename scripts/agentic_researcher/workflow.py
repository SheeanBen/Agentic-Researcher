from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List

from .config import resolve_path
from .fulltext import load_local_full_text
from .io_utils import read_json, write_json, write_text
from .markdown import note_filename, render_candidates_markdown, render_daily_report, render_note
from .models import PaperRecord
from .openai_client import generate_note_sections_with_openai
from .query_expansion import describe_query_strategy, expand_query_for_is


def resolve_run_dir(config: Dict[str, object], date_label: str) -> Path:
    discovery_root = resolve_path(config, config["paths"]["discovery_root"])
    run_dir = discovery_root / date_label
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_candidates_bundle(config: Dict[str, object], query: str, date_label: str, papers: List[PaperRecord]) -> Dict[str, str]:
    run_dir = resolve_run_dir(config, date_label)
    bundle_json = run_dir / "bundle.json"
    candidates_md = run_dir / "candidates.md"
    query_variants = expand_query_for_is(query)
    payload = {
        "query": query,
        "date": date_label,
        "query_strategy": describe_query_strategy(query, query_variants),
        "papers": [paper.to_dict() for paper in papers],
    }
    write_json(bundle_json, payload)
    write_text(candidates_md, render_candidates_markdown(query, papers, date_label, query_variants))
    legacy_csv = run_dir / "candidates.csv"
    legacy_zotero_ris = run_dir / "zotero_import.ris"
    if legacy_csv.exists():
        legacy_csv.unlink()
    if legacy_zotero_ris.exists():
        legacy_zotero_ris.unlink()
    return {
        "bundle_json": str(bundle_json),
        "candidates_md": str(candidates_md),
    }


def save_scored_bundle(config: Dict[str, object], query: str, date_label: str, papers: List[PaperRecord]) -> Dict[str, str]:
    run_dir = resolve_run_dir(config, date_label)
    bundle_json = run_dir / "bundle.json"
    candidates_md = run_dir / "candidates.md"
    query_variants = expand_query_for_is(query)
    payload = {
        "query": query,
        "date": date_label,
        "query_strategy": describe_query_strategy(query, query_variants),
        "papers": [paper.to_dict() for paper in papers],
    }
    write_json(bundle_json, payload)
    write_text(candidates_md, render_candidates_markdown(query, papers, date_label, query_variants))
    legacy_csv = run_dir / "candidates.csv"
    if legacy_csv.exists():
        legacy_csv.unlink()
    return {
        "bundle_json": str(bundle_json),
        "candidates_md": str(candidates_md),
    }


def load_bundle(path: Path) -> Dict[str, object]:
    return read_json(path)


def write_confirmed_bundle(
    config: Dict[str, object], query: str, date_label: str, papers: List[PaperRecord]
) -> Dict[str, str]:
    confirmed_root = resolve_path(config, config["paths"]["confirmed_root"])
    confirmed_path = confirmed_root / f"{date_label}.json"
    payload = {
        "query": query,
        "date": date_label,
        "papers": [paper.to_dict() for paper in papers],
    }
    write_json(confirmed_path, payload)

    literature_root = resolve_path(config, config["paths"]["literature_root"]) / date_label
    for paper in papers:
        full_text, full_text_path = load_local_full_text(config, date_label, paper)
        note_sections: dict[str, str] | None = None
        if config.get("llm", {}).get("provider") == "openai":
            try:
                note_sections = generate_note_sections_with_openai(paper, query, full_text, config["openai"])
            except Exception:
                note_sections = None
        note_path = literature_root / note_filename(paper)
        write_text(
            note_path,
            render_note(
                paper,
                date_label,
                full_text=full_text,
                full_text_path=full_text_path,
                note_sections=note_sections,
            ),
        )
    return {
        "confirmed_json": str(confirmed_path),
    }


def write_daily_report(config: Dict[str, object], query: str, date_label: str, papers: List[PaperRecord]) -> str:
    report_root = resolve_path(config, config["paths"]["report_root"])
    report_path = report_root / f"{date_label}.md"
    content = render_daily_report(query, papers, date_label)
    write_text(report_path, content)
    return str(report_path)


def load_all_confirmed(config: Dict[str, object]) -> List[PaperRecord]:
    confirmed_root = resolve_path(config, config["paths"]["confirmed_root"])
    confirmed_root.mkdir(parents=True, exist_ok=True)
    papers: List[PaperRecord] = []
    for path in sorted(confirmed_root.glob("*.json")):
        payload = read_json(path)
        for record in payload.get("papers", []):
            papers.append(PaperRecord.from_dict(record))
    return papers


def today_label(explicit: str = "") -> str:
    return explicit or date.today().isoformat()
