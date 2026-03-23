from __future__ import annotations

import json
import subprocess
from typing import Dict, Iterable, List, Tuple

from .models import PaperRecord
from .openai_client import score_papers_with_openai


TOPIC_TAGS = {
    "agentic": "agentic-ai",
    "agent": "agentic-ai",
    "multi-agent": "agentic-ai",
    "bank": "banking",
    "banking": "banking",
    "finance": "finance",
    "commercial": "commercial",
    "business": "commercial",
    "enterprise": "commercial",
    "information systems": "IS-theory",
    "is theory": "IS-theory",
    "review": "survey",
    "survey": "survey",
    "framework": "framework",
}


def heuristic_score_papers(papers: Iterable[PaperRecord], query: str) -> List[PaperRecord]:
    query_terms = [term.lower() for term in query.split() if term.strip()]
    scored: List[PaperRecord] = []
    for paper in papers:
        (
            paper.score,
            paper.tags,
            paper.recommendation_reason,
            paper.rationale,
            paper.summary_zh,
            paper.research_suggestion_zh,
            paper.business_application_zh,
        ) = score_paper(paper, query_terms)
        scored.append(paper)
    scored.sort(key=lambda item: (item.score or 0.0), reverse=True)
    return scored


def _short_topic(paper: PaperRecord, matched_terms: List[str]) -> str:
    if matched_terms:
        mapping = {
            "agentic": "agentic AI",
            "ai": "智能体/AI 系统",
            "banking": "银行业务场景",
            "finance": "金融业务场景",
            "enterprise": "企业流程场景",
        }
        return mapping.get(matched_terms[0], matched_terms[0])
    title = paper.title.lower()
    if "bank" in title or "finance" in title:
        return "金融/银行场景"
    if paper.is_survey_candidate:
        return "综述脉络"
    if "information systems" in title:
        return "信息系统理论"
    return "agentic AI 研究主题"


def _focus_phrase(paper: PaperRecord) -> str:
    text = f"{paper.title} {paper.abstract}".lower()
    phrases = []
    if "bank" in text or "finance" in text:
        phrases.append("金融服务与银行业务")
    if "governance" in text or "control" in text:
        phrases.append("治理与控制机制")
    if "workflow" in text or "service" in text or "operations" in text:
        phrases.append("工作流与服务流程")
    if "planning" in text:
        phrases.append("任务规划与流程编排")
    if "memory" in text:
        phrases.append("智能体记忆架构")
    if "agent" in text and not phrases:
        phrases.append("多智能体系统")
    return "、".join(dict.fromkeys(phrases)) or "agentic AI 相关问题"


def _summary_zh(paper: PaperRecord, topic: str) -> str:
    paper_type = "综述/框架性梳理" if paper.is_survey_candidate else "方法或实证讨论"
    return f"这篇文献发表于 {paper.venue}，主要围绕 {topic} 与 {_focus_phrase(paper)} 展开，整体更偏向 {paper_type}。"


def _research_suggestion_zh(paper: PaperRecord, topic: str) -> str:
    if paper.is_survey_candidate:
        return f"建议先把它作为 {topic} 的综述入口，用来梳理核心变量、研究空白与后续必读参考文献。"
    if "IS-theory" in paper.tags or "framework" in paper.tags:
        return "建议把文中的框架与 IS 理论变量对应起来，进一步抽象为可检验的研究模型或命题。"
    return "建议关注其方法设计与评估指标，思考如何迁移到企业场景并与 IS/商业问题结合。"


def _business_idea_zh(paper: PaperRecord) -> str:
    text = f"{paper.title} {paper.abstract}".lower()
    if "bank" in text or "finance" in text:
        return "可优先延伸到银行客服、合规审查或投顾辅助等高价值金融场景，验证 agentic AI 的流程提效价值。"
    if "enterprise" in text or "service" in text or "business" in text:
        return "可尝试映射到企业运营协同、客服编排或知识工作流自动化，评估多智能体协作带来的 ROI。"
    return "可探索其在复杂业务流程自动化中的落地方式，尤其关注可观测性、治理与人机协同设计。"


def score_paper(paper: PaperRecord, query_terms: List[str]) -> Tuple[float, List[str], str, str, str, str, str]:
    text = f"{paper.title} {paper.abstract} {paper.venue}".lower()
    score = 4.0
    matched_terms = [term for term in query_terms if term in text]
    score += min(3.0, len(matched_terms) * 0.8)
    if paper.is_survey_candidate:
        score += 1.5
    if paper.venue_domain == "is":
        score += 1.3
    elif paper.venue_domain == "business":
        score += 0.7
    if paper.venue_type == "journal":
        score += 0.5
    if paper.citation_count >= 100:
        score += 0.7
    elif paper.citation_count >= 20:
        score += 0.3
    score += min(0.8, paper.venue_priority / 200)
    if len(paper.abstract.split()) > 80:
        score += 0.5
    score = round(min(score, 10.0), 1)

    tags = []
    for token, tag in TOPIC_TAGS.items():
        if token in text and tag not in tags:
            tags.append(tag)
    if paper.venue_type and paper.venue_type not in tags:
        tags.append(paper.venue_type)
    if not tags:
        tags.append("candidate")

    topic = _short_topic(paper, matched_terms)
    reason_tail = "且带有综述/框架入口价值" if paper.is_survey_candidate else "且可作为今日候选中的高价值补充"
    reason = f"这篇文献与 {topic} 高度相关，来源于 {paper.venue}，{reason_tail}。"
    rationale = (
        f"命中查询词 {len(matched_terms)} 个；来源={paper.venue}；"
        f"综述候选={paper.is_survey_candidate}；被引次数={paper.citation_count}；摘要词数={len(paper.abstract.split())}。"
    )
    return (
        score,
        tags,
        reason,
        rationale,
        _summary_zh(paper, topic),
        _research_suggestion_zh(paper, topic),
        _business_idea_zh(paper),
    )


def command_score_papers(
    papers: Iterable[PaperRecord], query: str, command: str, fallback_to_heuristic: bool = True
) -> List[PaperRecord]:
    paper_list = list(papers)
    payload = {
        "query": query,
        "papers": [paper.to_dict() for paper in paper_list],
    }
    completed = subprocess.run(
        command,
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        shell=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        if fallback_to_heuristic:
            return heuristic_score_papers(paper_list, query)
        raise RuntimeError(completed.stderr.decode("utf-8", errors="ignore"))

    response = json.loads(completed.stdout.decode("utf-8"))
    by_id = {item["id"]: item for item in response.get("papers", [])}
    for paper in paper_list:
        scored = by_id.get(paper.id, {})
        paper.score = float(scored.get("score", paper.score or 0))
        paper.tags = list(scored.get("tags", paper.tags))
        paper.recommendation_reason = str(scored.get("recommendation_reason", paper.recommendation_reason))
        paper.rationale = str(scored.get("rationale", paper.rationale))
        paper.summary_zh = str(scored.get("summary_zh", paper.summary_zh))
        paper.research_suggestion_zh = str(scored.get("research_suggestion_zh", paper.research_suggestion_zh))
        paper.business_application_zh = str(scored.get("business_application_zh", paper.business_application_zh))
    paper_list.sort(key=lambda item: (item.score or 0.0), reverse=True)
    return paper_list


def openai_score_papers(papers: Iterable[PaperRecord], query: str, openai_config: Dict[str, object]) -> List[PaperRecord]:
    return score_papers_with_openai(papers, query, openai_config)
