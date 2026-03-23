from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Iterable, Tuple

from .config import resolve_path
from .io_utils import ensure_parent, write_text
from .models import PaperRecord
from .normalize import normalize_doi, normalize_title, slugify


def load_local_full_text(config: Dict[str, object], date_label: str, paper: PaperRecord) -> Tuple[str, str]:
    fulltext_root = resolve_path(config, config["paths"]["fulltext_root"])
    search_roots = [fulltext_root / date_label, fulltext_root]
    stems = _candidate_stems(paper)
    for root in search_roots:
        if not root.exists():
            continue
        for stem in stems:
            for suffix in (".md", ".txt"):
                path = root / f"{stem}{suffix}"
                if path.exists():
                    return path.read_text(encoding="utf-8"), str(path)

    pdf_root = resolve_path(config, config["paths"]["zotero_pdf_root"])
    pdf_path = find_matching_pdf(pdf_root, date_label, paper)
    if pdf_path:
        cache_path = fulltext_root / date_label / f"{paper.id}.txt"
        extracted = extract_pdf_text(pdf_path, cache_path)
        if extracted:
            return extracted, str(pdf_path)
    return "", ""


def _candidate_stems(paper: PaperRecord) -> list[str]:
    stems = [paper.id]
    normalized_doi = normalize_doi(paper.doi).replace("/", "_")
    if normalized_doi:
        stems.append(normalized_doi)
    title_slug = slugify(paper.title)[:120]
    if title_slug:
        stems.append(title_slug)
    deduped: list[str] = []
    seen = set()
    for stem in stems:
        if stem and stem not in seen:
            seen.add(stem)
            deduped.append(stem)
    return deduped


def find_matching_pdf(pdf_root: Path, date_label: str, paper: PaperRecord) -> Path | None:
    if not pdf_root.exists():
        return None

    pdf_paths = _preferred_pdf_paths(pdf_root, date_label)
    if not pdf_paths:
        return None

    best_path: Path | None = None
    best_score = -1
    for path in pdf_paths:
        score = _pdf_match_score(path, paper)
        if score > best_score:
            best_path = path
            best_score = score
    return best_path if best_score >= 6 else None


def extract_pdf_text(pdf_path: Path, cache_path: Path) -> str:
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    text = _run_pdftotext(pdf_path)
    if not text.strip():
        return ""
    ensure_parent(cache_path)
    write_text(cache_path, text)
    return text


def _preferred_pdf_paths(pdf_root: Path, date_label: str) -> list[Path]:
    preferred_dirs = [path for path in _date_specific_dirs(pdf_root, date_label) if path.exists()]
    seen = set()
    ordered: list[Path] = []
    for directory in preferred_dirs:
        for path in sorted(directory.rglob("*.pdf")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            ordered.append(path)
    if ordered:
        return ordered
    return sorted(pdf_root.rglob("*.pdf"))


def _date_specific_dirs(pdf_root: Path, date_label: str) -> list[Path]:
    variants = {date_label}
    parts = date_label.split("-")
    if len(parts) == 3:
        variants.add(f"{parts[0]}-{int(parts[1])}-{int(parts[2])}")
    matches: list[Path] = []
    for variant in variants:
        for path in pdf_root.rglob(variant):
            if path.is_dir():
                matches.append(path)
    return matches


def _pdf_match_score(path: Path, paper: PaperRecord) -> int:
    name_text = normalize_title(path.stem)
    score = 0

    title_text = normalize_title(paper.title)
    if title_text and title_text in name_text:
        score += 12

    title_tokens = [token for token in title_text.split() if len(token) > 2]
    overlap = sum(1 for token in title_tokens if token in name_text)
    score += min(8, overlap)

    if paper.year and str(paper.year) in path.stem:
        score += 3

    for author in _author_tokens(paper.authors):
        if author and author in name_text:
            score += 3

    if paper.doi:
        preview_text = _pdf_preview_text(path)
        doi = normalize_doi(paper.doi)
        if doi and doi in preview_text:
            score += 20
        preview_overlap = sum(1 for token in title_tokens if token in preview_text)
        score += min(10, preview_overlap)

    return score


def _author_tokens(authors: Iterable[str]) -> list[str]:
    tokens: list[str] = []
    for author in authors:
        parts = normalize_title(author).split()
        if parts:
            tokens.append(parts[-1])
    return tokens[:3]


def _pdf_preview_text(path: Path) -> str:
    try:
        completed = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "2", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return normalize_title(completed.stdout)


def _run_pdftotext(pdf_path: Path) -> str:
    try:
        completed = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout
