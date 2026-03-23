from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .config import resolve_path
from .models import DedupeIndex, HistoryRecord, PaperRecord
from .normalize import normalize_doi, normalize_title, stable_paper_id


def history_record_from_paper(paper: PaperRecord, status: str = "seen") -> HistoryRecord:
    return HistoryRecord(
        id=paper.id or stable_paper_id(paper.title, paper.doi, paper.year),
        title=paper.title,
        normalized_title=normalize_title(paper.title),
        doi=normalize_doi(paper.doi),
        venue=paper.venue,
        tags=list(paper.tags),
        collections=[],
        status=status,
    )


def build_history_snapshot(records: List[HistoryRecord]) -> DedupeIndex:
    doi_index: Dict[str, Dict[str, str]] = {}
    title_index: Dict[str, Dict[str, str]] = {}
    for record in records:
        if record.doi:
            doi_index[record.doi] = {
                "id": record.id,
                "title": record.title,
                "venue": record.venue,
                "status": record.status,
            }
        if record.normalized_title:
            title_index[record.normalized_title] = {
                "id": record.id,
                "title": record.title,
                "venue": record.venue,
                "status": record.status,
            }
    return DedupeIndex(count=len(records), doi_index=doi_index, title_index=title_index)


def check_duplicate(paper: PaperRecord, history: DedupeIndex) -> Tuple[bool, str]:
    paper_doi = normalize_doi(paper.doi)
    paper_title = normalize_title(paper.title)
    if paper_doi and paper_doi in history.doi_index:
        target = history.doi_index[paper_doi]
        return True, f"Duplicate DOI matched workspace record '{target.get('title', '')}'"
    if paper_title and paper_title in history.title_index:
        target = history.title_index[paper_title]
        return True, f"Duplicate title matched workspace record '{target.get('title', '')}'"
    return False, ""


def load_workspace_history(config: Dict[str, object], exclude_paths: Iterable[Path] | None = None) -> DedupeIndex:
    records: List[HistoryRecord] = []
    excluded = {path.resolve() for path in (exclude_paths or [])}

    confirmed_root = resolve_path(config, config["paths"]["confirmed_root"])

    if confirmed_root.exists():
        for path in sorted(confirmed_root.glob("*.json")):
            if path.resolve() in excluded:
                continue
            records.extend(_records_from_bundle(path, status="confirmed"))

    return build_history_snapshot(records)


def _records_from_bundle(path: Path, status: str) -> List[HistoryRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: List[HistoryRecord] = []
    for item in payload.get("papers", []):
        paper = PaperRecord.from_dict(item)
        if not paper.title:
            continue
        records.append(history_record_from_paper(paper, status=status))
    return records
