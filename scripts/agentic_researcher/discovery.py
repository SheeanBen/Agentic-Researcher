from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import PaperRecord
from .normalize import normalize_doi, stable_paper_id
from .query_expansion import expand_query_for_is
from .ris import parse_ris
from .venues import get_venue_domain, get_venue_priority, match_venue, prioritized_whitelist


def load_fixture_candidates(path: Path, whitelist: Iterable[str]) -> List[PaperRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _papers_from_payload(payload, whitelist, source_type="fixture")


def load_candidates_from_ris(path: Path, whitelist: Iterable[str]) -> List[PaperRecord]:
    payload = parse_ris(path)
    return _papers_from_payload(payload, whitelist, source_type="ris")


def load_candidates_from_csv(path: Path, whitelist: Iterable[str]) -> List[PaperRecord]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return _papers_from_payload(rows, whitelist, source_type="csv")


def search_crossref(query: str, whitelist: Iterable[str], rows: int = 50) -> List[PaperRecord]:
    seen_ids = set()
    normalized_items: List[Dict[str, object]] = []
    prioritized_venues = prioritized_whitelist(whitelist)
    query_variants = expand_query_for_is(query) or [query]
    target_rows = max(rows, 20)
    targeted_venues = prioritized_venues[: min(len(prioritized_venues), 6)]
    primary_variants = query_variants[: min(len(query_variants), 3)]
    per_request_rows = min(6, max(3, target_rows // max(len(targeted_venues) * max(len(primary_variants), 1), 1)))

    for venue in targeted_venues:
        for variant in primary_variants:
            items = _crossref_request(
                {
                    "query": variant,
                    "query.container-title": venue,
                    "rows": per_request_rows,
                    "sort": "relevance",
                    "select": "DOI,title,author,issued,container-title,abstract,URL,is-referenced-by-count",
                }
            )
            for item in _normalize_crossref_items(items):
                paper_id = stable_paper_id(str(item.get("title", "")), str(item.get("doi", "")), item.get("year"))
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)
                normalized_items.append(item)
            if len(normalized_items) >= target_rows:
                break
        if len(normalized_items) >= target_rows:
            break

    if len(normalized_items) < target_rows:
        for variant in query_variants[: min(len(query_variants), 4)]:
            items = _crossref_request(
                {
                    "query": variant,
                    "rows": target_rows,
                    "sort": "relevance",
                    "select": "DOI,title,author,issued,container-title,abstract,URL,is-referenced-by-count",
                }
            )
            for item in _normalize_crossref_items(items):
                paper_id = stable_paper_id(str(item.get("title", "")), str(item.get("doi", "")), item.get("year"))
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)
                normalized_items.append(item)
            if len(normalized_items) >= target_rows:
                break

    papers = _papers_from_payload(normalized_items, whitelist, source_type="crossref")
    papers.sort(
        key=lambda paper: (
            1 if paper.venue_domain == "is" else 0,
            paper.venue_priority,
            paper.citation_count,
            paper.year or 0,
        ),
        reverse=True,
    )
    return papers[:target_rows]


def _crossref_request(params: Dict[str, object]) -> List[Dict[str, object]]:
    url = f"https://api.crossref.org/works?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "AgenticResearcher/0.1 (mailto:research@example.com)"})
    with urlopen(request, timeout=25) as response:  # nosec - user-configured research request
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("message", {}).get("items", [])


def _normalize_crossref_items(items: List[Dict[str, object]]) -> List[Dict[str, object]]:
    normalized_items: List[Dict[str, object]] = []
    for item in items:
        authors = []
        for author in item.get("author", []):
            name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
            if name:
                authors.append(name)
        container_titles = item.get("container-title") or [""]
        year = None
        date_parts = (((item.get("issued") or {}).get("date-parts") or [[None]])[0] or [None])
        if date_parts and date_parts[0]:
            year = int(date_parts[0])
        normalized_items.append(
            {
                "title": (item.get("title") or [""])[0],
                "authors": authors,
                "year": year,
                "abstract": item.get("abstract", ""),
                "doi": item.get("DOI", ""),
                "venue": container_titles[0],
                "url": item.get("URL", ""),
                "citation_count": int(item.get("is-referenced-by-count", 0) or 0),
            }
        )
    return normalized_items


def _papers_from_payload(payload: List[Dict[str, object]], whitelist: Iterable[str], source_type: str) -> List[PaperRecord]:
    papers: List[PaperRecord] = []
    for item in payload:
        title = str(item.get("title", "")).strip()
        venue, venue_type = match_venue(str(item.get("venue", "")), whitelist)
        if not title or not venue:
            continue
        authors = item.get("authors") or []
        if isinstance(authors, str):
            authors = [author.strip() for author in authors.split(";") if author.strip()]
        abstract = str(item.get("abstract", "") or "").replace("<jats:p>", "").replace("</jats:p>", "")
        doi = normalize_doi(str(item.get("doi", "")))
        year = item.get("year")
        is_survey_candidate = any(token in f"{title} {abstract}".lower() for token in ["survey", "review", "framework"])
        papers.append(
            PaperRecord(
                id=stable_paper_id(title, doi, year),
                title=title,
                authors=list(authors),
                year=year if isinstance(year, int) else None,
                abstract=abstract,
                doi=doi,
                venue=venue,
                venue_type=venue_type or "",
                venue_domain=get_venue_domain(venue),
                venue_priority=get_venue_priority(venue),
                source_type=source_type,
                url=str(item.get("url", "")),
                citation_count=int(item.get("citation_count", 0) or 0),
                is_survey_candidate=is_survey_candidate,
            )
        )
    return papers
