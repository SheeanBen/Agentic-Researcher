from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PaperRecord:
    id: str
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    doi: str = ""
    venue: str = ""
    venue_type: str = ""
    venue_domain: str = ""
    venue_priority: int = 0
    source_type: str = ""
    url: str = ""
    citation_count: int = 0
    is_survey_candidate: bool = False
    duplicate_status: str = "unknown"
    duplicate_reason: str = ""
    score: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    recommendation_reason: str = ""
    rationale: str = ""
    summary_zh: str = ""
    research_suggestion_zh: str = ""
    business_application_zh: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PaperRecord":
        return cls(
            id=str(payload.get("id", "")),
            title=str(payload.get("title", "")),
            authors=list(payload.get("authors", [])),
            year=payload.get("year"),
            abstract=str(payload.get("abstract", "")),
            doi=str(payload.get("doi", "")),
            venue=str(payload.get("venue", "")),
            venue_type=str(payload.get("venue_type", "")),
            venue_domain=str(payload.get("venue_domain", "")),
            venue_priority=int(payload.get("venue_priority", 0) or 0),
            source_type=str(payload.get("source_type", "")),
            url=str(payload.get("url", "")),
            citation_count=int(payload.get("citation_count", 0) or 0),
            is_survey_candidate=bool(payload.get("is_survey_candidate", False)),
            duplicate_status=str(payload.get("duplicate_status", "unknown")),
            duplicate_reason=str(payload.get("duplicate_reason", "")),
            score=payload.get("score"),
            tags=list(payload.get("tags", [])),
            recommendation_reason=str(payload.get("recommendation_reason", "")),
            rationale=str(payload.get("rationale", "")),
            summary_zh=str(payload.get("summary_zh", "")),
            research_suggestion_zh=str(payload.get("research_suggestion_zh", "")),
            business_application_zh=str(payload.get("business_application_zh", "")),
        )


@dataclass
class HistoryRecord:
    id: str
    title: str
    normalized_title: str
    doi: str = ""
    venue: str = ""
    tags: List[str] = field(default_factory=list)
    collections: List[str] = field(default_factory=list)
    status: str = "confirmed"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DedupeIndex:
    count: int = 0
    doi_index: Dict[str, Dict[str, str]] = field(default_factory=dict)
    title_index: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
