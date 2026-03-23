from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .models import DedupeIndex, HistoryRecord, PaperRecord
from .normalize import normalize_doi, normalize_title, stable_paper_id
from .ris import parse_ris


def _as_list(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if ";" in text:
        return [item.strip() for item in text.split(";") if item.strip()]
    if "|" in text:
        return [item.strip() for item in text.split("|") if item.strip()]
    return [text]


def _normalize_row_keys(row: Dict[str, object]) -> Dict[str, object]:
    return {str(key).strip().lower(): value for key, value in row.items()}


def _extract_title(row: Dict[str, object]) -> str:
    normalized = _normalize_row_keys(row)
    return str(
        normalized.get("title")
        or normalized.get("name")
        or normalized.get("ti")
        or normalized.get("t1")
        or ""
    ).strip()


def _extract_doi(row: Dict[str, object]) -> str:
    normalized = _normalize_row_keys(row)
    return normalize_doi(
        str(normalized.get("doi") or normalized.get("do") or normalized.get("doi url") or "")
    )


def _extract_venue(row: Dict[str, object]) -> str:
    normalized = _normalize_row_keys(row)
    return str(
        normalized.get("publication title")
        or normalized.get("journal")
        or normalized.get("venue")
        or normalized.get("jo")
        or normalized.get("t2")
        or ""
    ).strip()


def _extract_tags(row: Dict[str, object]) -> List[str]:
    normalized = _normalize_row_keys(row)
    return _as_list(normalized.get("tags") or normalized.get("tag"))


def _extract_collections(row: Dict[str, object]) -> List[str]:
    normalized = _normalize_row_keys(row)
    return _as_list(normalized.get("collections") or normalized.get("collection"))


def _is_confirmed(tags: Iterable[str], collections: Iterable[str], config: Dict[str, object]) -> bool:
    confirmed_tags = {tag.lower() for tag in config.get("confirmed_tags", [])}
    confirmed_collections = {value.lower() for value in config.get("confirmed_collections", [])}
    if not confirmed_tags and not confirmed_collections:
        return True
    tag_match = any(tag.lower() in confirmed_tags for tag in tags)
    collection_match = any(collection.lower() in confirmed_collections for collection in collections)
    return tag_match or collection_match


def read_zotero_export(path: Path, config: Dict[str, object]) -> List[HistoryRecord]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv_export(path, config)
    if suffix == ".json":
        return _read_json_export(path, config)
    if suffix == ".ris":
        return _read_ris_export(path)
    raise ValueError(f"Unsupported Zotero export format: {path}")


def _read_csv_export(path: Path, config: Dict[str, object]) -> List[HistoryRecord]:
    records: List[HistoryRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = _extract_title(row)
            if not title:
                continue
            tags = _extract_tags(row)
            collections = _extract_collections(row)
            if not _is_confirmed(tags, collections, config):
                continue
            doi = _extract_doi(row)
            normalized_title = normalize_title(title)
            records.append(
                HistoryRecord(
                    id=stable_paper_id(title, doi),
                    title=title,
                    normalized_title=normalized_title,
                    doi=doi,
                    venue=_extract_venue(row),
                    tags=tags,
                    collections=collections,
                )
            )
    return records


def _read_json_export(path: Path, config: Dict[str, object]) -> List[HistoryRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "items" in payload:
        items = payload["items"]
    else:
        items = payload
    records: List[HistoryRecord] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        title = _extract_title(row)
        if not title:
            continue
        tags = _extract_tags(row)
        collections = _extract_collections(row)
        if not _is_confirmed(tags, collections, config):
            continue
        doi = _extract_doi(row)
        records.append(
            HistoryRecord(
                id=stable_paper_id(title, doi),
                title=title,
                normalized_title=normalize_title(title),
                doi=doi,
                venue=_extract_venue(row),
                tags=tags,
                collections=collections,
            )
        )
    return records


def _read_ris_export(path: Path) -> List[HistoryRecord]:
    records: List[HistoryRecord] = []
    for row in parse_ris(path):
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        doi = normalize_doi(str(row.get("doi", "")))
        records.append(
            HistoryRecord(
                id=stable_paper_id(title, doi, row.get("year")),
                title=title,
                normalized_title=normalize_title(title),
                doi=doi,
                venue=str(row.get("venue", "")),
                tags=[],
                collections=[],
            )
        )
    return records


def build_history_snapshot(records: List[HistoryRecord]) -> Dict[str, object]:
    doi_index: Dict[str, Dict[str, str]] = {}
    title_index: Dict[str, Dict[str, str]] = {}
    for record in records:
        if record.doi:
            doi_index[record.doi] = {"id": record.id, "title": record.title, "venue": record.venue}
        if record.normalized_title:
            title_index[record.normalized_title] = {"id": record.id, "title": record.title, "venue": record.venue}
    return {
        "count": len(records),
        "doi_index": doi_index,
        "title_index": title_index,
    }


def load_history_snapshot(path: Path) -> DedupeIndex:
    if not path.exists():
        return DedupeIndex()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DedupeIndex(
        count=int(payload.get("count", 0)),
        doi_index=dict(payload.get("doi_index", {})),
        title_index=dict(payload.get("title_index", {})),
    )


def check_duplicate(paper: PaperRecord, history: DedupeIndex) -> Tuple[bool, str]:
    paper_doi = normalize_doi(paper.doi)
    paper_title = normalize_title(paper.title)
    if paper_doi and paper_doi in history.doi_index:
        target = history.doi_index[paper_doi]
        return True, f"Duplicate DOI matched Zotero record '{target.get('title', '')}'"
    if paper_title and paper_title in history.title_index:
        target = history.title_index[paper_title]
        return True, f"Duplicate title matched Zotero record '{target.get('title', '')}'"
    return False, ""
