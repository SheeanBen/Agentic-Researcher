from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple


VENUE_ALIASES: Dict[str, Dict[str, object]] = {
    "Information Systems Research": {
        "type": "journal",
        "aliases": ["information systems research", "isr"],
        "domain": "is",
        "priority": 100,
    },
    "MIS Quarterly": {
        "type": "journal",
        "aliases": ["mis quarterly", "misq"],
        "domain": "is",
        "priority": 100,
    },
    "Journal of Management Information Systems": {
        "type": "journal",
        "aliases": ["journal of management information systems", "jmis", "jims"],
        "domain": "is",
        "priority": 96,
    },
    "Journal of the Association for Information Systems": {
        "type": "journal",
        "aliases": ["journal of the association for information systems", "jais"],
        "domain": "is",
        "priority": 95,
    },
    "Information Systems Journal": {
        "type": "journal",
        "aliases": ["information systems journal", "isj"],
        "domain": "is",
        "priority": 93,
    },
    "European Journal of Information Systems": {
        "type": "journal",
        "aliases": ["european journal of information systems", "ejis"],
        "domain": "is",
        "priority": 92,
    },
    "Journal of Information Technology": {
        "type": "journal",
        "aliases": ["journal of information technology", "jit"],
        "domain": "is",
        "priority": 92,
    },
    "Information & Management": {
        "type": "journal",
        "aliases": ["information & management", "information and management", "i&m"],
        "domain": "is",
        "priority": 90,
    },
    "Decision Support Systems": {
        "type": "journal",
        "aliases": ["decision support systems", "dss"],
        "domain": "is",
        "priority": 89,
    },
    "Journal of Strategic Information Systems": {
        "type": "journal",
        "aliases": ["journal of strategic information systems", "jsis"],
        "domain": "is",
        "priority": 88,
    },
    "Management Science": {
        "type": "journal",
        "aliases": ["management science"],
        "domain": "business",
        "priority": 91,
    },
    "Organization Science": {
        "type": "journal",
        "aliases": ["organization science"],
        "domain": "business",
        "priority": 84,
    },
    "INFORMS Journal on Computing": {
        "type": "journal",
        "aliases": ["informs journal on computing", "journal on computing"],
        "domain": "business",
        "priority": 82,
    },
    "International Conference on Information Systems": {
        "type": "conference",
        "aliases": ["international conference on information systems", "icis"],
        "domain": "is",
        "priority": 99,
    },
    "Americas Conference on Information Systems": {
        "type": "conference",
        "aliases": ["americas conference on information systems", "amcis"],
        "domain": "is",
        "priority": 90,
    },
    "European Conference on Information Systems": {
        "type": "conference",
        "aliases": ["european conference on information systems", "ecis"],
        "domain": "is",
        "priority": 89,
    },
    "Pacific Asia Conference on Information Systems": {
        "type": "conference",
        "aliases": ["pacific asia conference on information systems", "pacis"],
        "domain": "is",
        "priority": 86,
    },
    "Hawaii International Conference on System Sciences": {
        "type": "conference",
        "aliases": ["hawaii international conference on system sciences", "hicss"],
        "domain": "is",
        "priority": 85,
    },
    "AAMAS": {
        "type": "conference",
        "aliases": [
            "aamas",
            "international conference on autonomous agents and multiagent systems",
        ],
        "domain": "ai",
        "priority": 78,
    },
    "NeurIPS": {
        "type": "conference",
        "aliases": [
            "neurips",
            "neural information processing systems",
            "advances in neural information processing systems",
        ],
        "domain": "ai",
        "priority": 75,
    },
    "ICML": {
        "type": "conference",
        "aliases": ["icml", "international conference on machine learning"],
        "domain": "ai",
        "priority": 75,
    },
    "AAAI": {
        "type": "conference",
        "aliases": [
            "aaai",
            "aaai conference on artificial intelligence",
            "proceedings of the aaai conference on artificial intelligence",
        ],
        "domain": "ai",
        "priority": 74,
    },
    "IJCAI": {
        "type": "conference",
        "aliases": [
            "ijcai",
            "international joint conference on artificial intelligence",
            "proceedings of the international joint conference on artificial intelligence",
        ],
        "domain": "ai",
        "priority": 74,
    },
}


def match_venue(raw_name: str, whitelist: Iterable[str]) -> Tuple[Optional[str], Optional[str]]:
    lowered = (raw_name or "").strip().lower()
    allowed = set(whitelist)
    for canonical, config in VENUE_ALIASES.items():
        if canonical not in allowed:
            continue
        aliases = config.get("aliases", [])
        venue_type = str(config.get("type", ""))
        if lowered == canonical.lower() or lowered in aliases:
            return canonical, str(config.get("type", ""))
        if venue_type == "conference" and lowered and any(alias in lowered for alias in aliases):
            return canonical, str(config.get("type", ""))
    return None, None


def get_venue_metadata(canonical: str) -> Dict[str, object]:
    return dict(VENUE_ALIASES.get(canonical, {}))


def get_venue_priority(canonical: str) -> int:
    return int(VENUE_ALIASES.get(canonical, {}).get("priority", 0))


def get_venue_domain(canonical: str) -> str:
    return str(VENUE_ALIASES.get(canonical, {}).get("domain", ""))


def prioritized_whitelist(whitelist: Iterable[str]) -> List[str]:
    return sorted(whitelist, key=lambda venue: get_venue_priority(venue), reverse=True)
