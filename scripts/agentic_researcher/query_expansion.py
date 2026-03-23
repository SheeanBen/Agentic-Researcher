from __future__ import annotations

from typing import Dict, List


IS_SUFFIXES = [
    "information systems",
    "digital transformation",
    "decision support systems",
    "enterprise systems",
    "IT governance",
    "service operations",
]

AGENTIC_REWRITES = [
    "agentic AI",
    "AI agents",
    "autonomous agents",
    "multi-agent systems",
]


def expand_query_for_is(query: str) -> List[str]:
    base = " ".join(query.split()).strip()
    if not base:
        return []

    variants: List[str] = [base]
    lowered = base.lower()

    for suffix in IS_SUFFIXES:
        if suffix.lower() not in lowered:
            variants.append(f"{base} {suffix}")

    if "agent" in lowered or "ai" in lowered:
        variants.extend(
            [
                f"{base} organizational impact",
                f"{base} business value",
            ]
        )
    else:
        for rewrite in AGENTIC_REWRITES[:2]:
            variants.append(f"{base} {rewrite}")

    if "agentic" in lowered or "agent" in lowered:
        for rewrite in AGENTIC_REWRITES:
            if rewrite.lower() not in lowered:
                variants.append(f"{rewrite} {base} information systems")

    deduped: List[str] = []
    seen = set()
    for item in variants:
        normalized = " ".join(item.split()).strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped[:8]


def describe_query_strategy(query: str, variants: List[str]) -> Dict[str, object]:
    themes = []
    lowered = query.lower()
    if "agent" in lowered or "ai" in lowered:
        themes.append("agentic-ai")
    if "bank" in lowered or "finance" in lowered:
        themes.append("finance")
    if "service" in lowered:
        themes.append("service-operations")
    themes.append("information-systems")
    return {
        "original_query": query,
        "expanded_queries": variants,
        "strategy": "IS-prioritized query expansion",
        "themes": themes,
    }
