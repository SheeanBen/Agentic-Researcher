from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .env import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "config" / "agentic_researcher.json"


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_config() -> Dict[str, Any]:
    return {
        "workspace_root": ".",
        "daily_target": 10,
        "candidate_pool_size": 25,
        "discovery": {
            "provider": "fixture",
            "fixture_path": "data/fixtures/discovery_seed.json",
            "venue_whitelist": [
                "Information Systems Research",
                "MIS Quarterly",
                "Journal of Management Information Systems",
                "Journal of the Association for Information Systems",
                "Information Systems Journal",
                "European Journal of Information Systems",
                "Journal of Information Technology",
                "Information & Management",
                "Decision Support Systems",
                "Journal of Strategic Information Systems",
                "Management Science",
                "Organization Science",
                "INFORMS Journal on Computing",
                "International Conference on Information Systems",
                "Americas Conference on Information Systems",
                "European Conference on Information Systems",
                "Pacific Asia Conference on Information Systems",
                "Hawaii International Conference on System Sciences",
                "AAMAS",
                "NeurIPS",
                "ICML",
                "AAAI",
                "IJCAI",
            ],
        },
        "llm": {
            "provider": "heuristic",
            "command": "",
        },
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-5.2-codex",
            "base_url": "https://api.openai.com/v1/responses",
            "wire_api": "responses",
            "reasoning_effort": "medium",
            "timeout_seconds": 120,
        },
        "paths": {
            "discovery_root": "data/discovery",
            "fulltext_root": "data/fulltext",
            "zotero_pdf_root": "data/zotero_pdf",
            "literature_root": "01_literature",
            "report_root": "02_reports/daily",
            "confirmed_root": "03_state/confirmed",
        },
    }


def load_config(config_path: str = "") -> Dict[str, Any]:
    config = default_config()
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        config = deep_merge(config, data)
    config["__config_path__"] = str(path)
    return config


def resolve_path(config: Dict[str, Any], relative_path: str) -> Path:
    root = ROOT / config.get("workspace_root", ".")
    return (root / relative_path).resolve()
