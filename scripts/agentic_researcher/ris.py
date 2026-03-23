from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .normalize import normalize_whitespace


RIS_FIELD_MAP = {
    "TI": "title",
    "T1": "title",
    "AU": "authors",
    "PY": "year",
    "Y1": "year",
    "AB": "abstract",
    "DO": "doi",
    "JO": "venue",
    "T2": "venue",
    "UR": "url",
}


def parse_ris(path: Path) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    current: Dict[str, object] = {}
    authors: List[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue
            if line.startswith("ER  -"):
                if authors:
                    current["authors"] = authors
                records.append(current)
                current = {}
                authors = []
                continue
            if "  -" not in line:
                continue
            tag, value = line.split("  -", 1)
            tag = tag.strip()
            value = normalize_whitespace(value)
            mapped = RIS_FIELD_MAP.get(tag)
            if mapped == "authors":
                authors.append(value)
            elif mapped == "year":
                digits = "".join(char for char in value if char.isdigit())
                current["year"] = int(digits[:4]) if digits[:4] else None
            elif mapped:
                current[mapped] = value
        if current:
            if authors:
                current["authors"] = authors
            records.append(current)
    return records


def write_ris(records: List[Dict[str, object]], path: Path) -> None:
    lines: List[str] = []
    for record in records:
        lines.append("TY  - JOUR")
        for author in record.get("authors", []):
            lines.append(f"AU  - {author}")
        if record.get("title"):
            lines.append(f"TI  - {record['title']}")
        if record.get("year"):
            lines.append(f"PY  - {record['year']}")
        if record.get("abstract"):
            lines.append(f"AB  - {record['abstract']}")
        if record.get("doi"):
            lines.append(f"DO  - {record['doi']}")
        if record.get("venue"):
            lines.append(f"JO  - {record['venue']}")
        if record.get("url"):
            lines.append(f"UR  - {record['url']}")
        lines.append("ER  - ")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
