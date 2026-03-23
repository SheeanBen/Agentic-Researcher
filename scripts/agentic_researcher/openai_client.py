from __future__ import annotations

import json
import os
import re
from typing import Dict, Iterable, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import PaperRecord


SCORE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "papers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "score": {"type": "number"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "recommendation_reason": {"type": "string"},
                    "summary_zh": {"type": "string"},
                    "research_suggestion_zh": {"type": "string"},
                    "business_application_zh": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "id",
                    "score",
                    "tags",
                    "recommendation_reason",
                    "summary_zh",
                    "research_suggestion_zh",
                    "business_application_zh",
                    "rationale",
                ],
            },
        }
    },
    "required": ["papers"],
}

NOTE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overview": {"type": "string"},
        "problem_motivation": {"type": "string"},
        "method_design": {"type": "string"},
        "research_process": {"type": "string"},
        "findings_contributions": {"type": "string"},
        "extensions_critique": {"type": "string"},
    },
    "required": [
        "overview",
        "problem_motivation",
        "method_design",
        "research_process",
        "findings_contributions",
        "extensions_critique",
    ],
}


def _extract_output_json(payload: Dict[str, object]) -> Dict[str, object]:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return json.loads(output_text)

    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text", "")
                if text:
                    return json.loads(text)
    raise ValueError("OpenAI response did not contain parseable JSON output.")


def _responses_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if not base_url.endswith("/responses"):
        base_url = f"{base_url}/responses"
    return base_url


def _chat_completions_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/responses"):
        base_url = base_url[: -len("/responses")]
    if not base_url.endswith("/chat/completions"):
        base_url = f"{base_url}/chat/completions"
    return base_url


def _post_json(url: str, body: Dict[str, object], api_key: str, timeout_seconds: int) -> Dict[str, object]:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Codex-AgenticResearcher/0.1",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec
        return json.loads(response.read().decode("utf-8"))


def _respond_with_responses(
    system_prompt: str,
    prompt_payload: Dict[str, object],
    schema_name: str,
    schema: Dict[str, object],
    api_key: str,
    config: Dict[str, object],
) -> Dict[str, object]:
    body = {
        "model": config["model"],
        "reasoning": {"effort": config.get("reasoning_effort", "medium")},
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(prompt_payload, ensure_ascii=False),
                    }
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
    }
    base_url = os.environ.get("OPENAI_BASE_URL", config["base_url"])
    return _post_json(_responses_url(base_url), body, api_key, int(config.get("timeout_seconds", 120)))


def _respond_with_chat_completions(
    system_prompt: str,
    prompt_payload: Dict[str, object],
    schema: Dict[str, object],
    api_key: str,
    config: Dict[str, object],
) -> Dict[str, object]:
    schema_text = json.dumps(schema, ensure_ascii=False)
    body = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    f"{system_prompt}"
                    "只返回一个 JSON 对象，必须满足这个 JSON Schema："
                    f"{schema_text}"
                ),
            },
            {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
        ],
        "temperature": 0.2,
    }
    base_url = os.environ.get("OPENAI_BASE_URL", config["base_url"])
    payload = _post_json(_chat_completions_url(base_url), body, api_key, int(config.get("timeout_seconds", 120)))
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


def _call_openai_json(
    system_prompt: str,
    prompt_payload: Dict[str, object],
    schema_name: str,
    schema: Dict[str, object],
    config: Dict[str, object],
) -> Dict[str, object]:
    api_key = os.environ.get(config["api_key_env"], "")
    if not api_key:
        raise RuntimeError(f"{config['api_key_env']} is not set.")

    wire_api = str(config.get("wire_api", "responses"))
    try:
        if wire_api == "chat_completions":
            return _respond_with_chat_completions(system_prompt, prompt_payload, schema, api_key, config)
        payload = _respond_with_responses(system_prompt, prompt_payload, schema_name, schema, api_key, config)
        return _extract_output_json(payload)
    except HTTPError as exc:  # pragma: no cover - network/integration path
        detail = exc.read().decode("utf-8", errors="ignore")
        if wire_api == "responses" and exc.code in {400, 403, 404, 405}:
            try:
                return _respond_with_chat_completions(system_prompt, prompt_payload, schema, api_key, config)
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"OpenAI Responses API failed with HTTP {exc.code}: {detail}; "
                    f"chat.completions fallback also failed: {fallback_exc}"
                ) from fallback_exc
        raise RuntimeError(f"OpenAI API HTTPError {exc.code}: {detail}") from exc
    except URLError as exc:  # pragma: no cover - network/integration path
        raise RuntimeError(f"OpenAI API connection failed: {exc}") from exc


def _condense_full_text(full_text: str, max_chars: int = 32000) -> str:
    text = re.sub(r"\s+", " ", full_text or "").strip()
    if len(text) <= max_chars:
        return text

    segments: list[str] = [text[:9000]]
    headings = [
        "abstract",
        "introduction",
        "background",
        "theory",
        "method",
        "methods",
        "research design",
        "experiment",
        "results",
        "discussion",
        "implications",
        "conclusion",
    ]
    seen = set()
    for heading in headings:
        match = re.search(rf"\b{re.escape(heading)}\b", text, re.IGNORECASE)
        if not match:
            continue
        start = max(0, match.start() - 1500)
        end = min(len(text), match.start() + 4500)
        segment = text[start:end].strip()
        if not segment:
            continue
        key = segment[:200]
        if key in seen:
            continue
        seen.add(key)
        segments.append(segment)
    segments.append(text[-7000:])

    joined = "\n\n[...]\n\n".join(segments)
    return joined[:max_chars]


def score_papers_with_openai(papers: Iterable[PaperRecord], query: str, config: Dict[str, object]) -> List[PaperRecord]:
    paper_list = list(papers)
    if not paper_list:
        return paper_list

    prompt_payload = {
        "query": query,
        "papers": [
            {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "abstract": paper.abstract,
                "doi": paper.doi,
                "venue": paper.venue,
                "venue_type": paper.venue_type,
                "is_survey_candidate": paper.is_survey_candidate,
            }
            for paper in paper_list
        ],
    }
    system_prompt = (
        "你是一名严谨的科研助理。请根据给定论文元数据，用中文为每篇论文返回："
        "0-10 相关性评分、3-6 个英文短标签、一句中文推荐理由、中文摘要总结、中文研究建议、"
        "中文商业应用想法，以及简短中文评分依据。输出必须严格遵守 JSON Schema。"
    )

    response_payload = _call_openai_json(
        system_prompt=system_prompt,
        prompt_payload=prompt_payload,
        schema_name="agentic_researcher_scores",
        schema=SCORE_SCHEMA,
        config=config,
    )
    by_id = {item["id"]: item for item in response_payload.get("papers", [])}
    for paper in paper_list:
        scored = by_id.get(paper.id)
        if not scored:
            continue
        paper.score = float(scored.get("score", 0))
        paper.tags = list(scored.get("tags", []))
        paper.recommendation_reason = str(scored.get("recommendation_reason", ""))
        paper.summary_zh = str(scored.get("summary_zh", ""))
        paper.research_suggestion_zh = str(scored.get("research_suggestion_zh", ""))
        paper.business_application_zh = str(scored.get("business_application_zh", ""))
        paper.rationale = str(scored.get("rationale", ""))

    paper_list.sort(key=lambda item: (item.score or 0.0), reverse=True)
    return paper_list


def generate_note_sections_with_openai(
    paper: PaperRecord,
    query: str,
    full_text: str,
    config: Dict[str, object],
) -> Dict[str, str]:
    prompt_payload = {
        "query": query,
        "paper": {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "venue": paper.venue,
            "venue_type": paper.venue_type,
            "doi": paper.doi,
            "citation_count": paper.citation_count,
            "abstract": paper.abstract,
            "recommendation_reason": paper.recommendation_reason,
            "summary_zh": paper.summary_zh,
        },
        "full_text_available": bool(full_text.strip()),
        "full_text_excerpt": _condense_full_text(full_text),
    }
    system_prompt = (
        "你是一名服务于信息系统领域研究者的资深科研助理。"
        "请基于论文元信息与全文片段，输出一份适合写入 Obsidian 的中文深度笔记。"
        "要求："
        "1. 全部使用中文；"
        "2. 不要使用 LaTeX、公式或英文小标题；"
        "3. 不要空泛复述摘要，要给出研究判断、理论位置、方法边界、可扩展方向与批判性评价；"
        "4. 若全文信息不足，可以明确写“基于摘要与有限正文判断”，但不要编造实验细节；"
        "5. 每个字段写成可直接放进 Markdown 正文的自然中文段落。"
    )
    payload = _call_openai_json(
        system_prompt=system_prompt,
        prompt_payload=prompt_payload,
        schema_name="agentic_researcher_note",
        schema=NOTE_SCHEMA,
        config=config,
    )
    return {key: str(value or "") for key, value in payload.items()}
