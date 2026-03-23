from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_doi(value: str) -> str:
    text = normalize_whitespace(value).lower()
    text = text.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return text.strip(" .")


def normalize_title(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return normalize_whitespace(text)


def slugify(value: str) -> str:
    return normalize_title(value).replace(" ", "-")


def stable_paper_id(title: str, doi: str = "", year: object = "") -> str:
    base = normalize_doi(doi) or normalize_title(title)
    if year:
        base = f"{base}:{year}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()
    return digest[:12]
