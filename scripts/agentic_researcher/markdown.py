from __future__ import annotations

import re
from typing import Iterable, List

from .models import PaperRecord
from .normalize import slugify


def _obsidian_tag(tag: str) -> str:
    return "#" + tag.strip().replace(" ", "-").replace("/", "-")


def _first_author_token(paper: PaperRecord) -> str:
    if not paper.authors:
        return "unknown-author"
    first_author = paper.authors[0].strip()
    if not first_author:
        return "unknown-author"
    parts = [part for part in first_author.replace(",", " ").split() if part]
    return slugify(parts[-1] if parts else first_author) or "unknown-author"


def _publication_date_token(paper: PaperRecord) -> str:
    if paper.year:
        return str(paper.year)
    return "unknown-date"


def _analysis_text(paper: PaperRecord, full_text: str = "") -> str:
    return " ".join((full_text or paper.abstract or "").split())


def _analysis_basis(full_text_path: str) -> str:
    if full_text_path:
        return f"本地全文：`{full_text_path}`"
    return "仅基于元信息与摘要"


def _extract_sentences(text: str, keywords: list[str], limit: int = 2) -> list[str]:
    if not text:
        return []
    sentences = [item.strip() for item in re.split(r"(?<=[。！？.!?])\s+|\n+", text) if item.strip()]
    picked: list[str] = []
    seen = set()
    for sentence in sentences:
        lowered = sentence.lower()
        if keywords and not any(keyword in lowered for keyword in keywords):
            continue
        normalized = " ".join(sentence.split())
        if len(normalized) < 24 or normalized in seen:
            continue
        seen.add(normalized)
        picked.append(normalized)
        if len(picked) >= limit:
            break
    if picked:
        return picked
    fallback: list[str] = []
    for sentence in sentences:
        normalized = " ".join(sentence.split())
        if len(normalized) < 24 or normalized in seen:
            continue
        fallback.append(normalized)
        if len(fallback) >= limit:
            break
    return fallback


def _topic_phrase(paper: PaperRecord, analysis_text: str = "") -> str:
    text = f"{paper.title} {analysis_text or paper.abstract}".lower()
    if "bank" in text or "finance" in text:
        return "银行与金融服务中的 agentic AI 应用"
    if "governance" in text or "control" in text or "trust" in text:
        return "agentic AI 的治理、控制与信任机制"
    if "service" in text or "workflow" in text or "operations" in text:
        return "企业服务流程与工作流中的智能体协作"
    if "review" in text or "survey" in text:
        return "agentic AI 相关研究脉络"
    return "agentic AI 与信息系统场景"


def _research_problem_zh(paper: PaperRecord, analysis_text: str) -> str:
    topic = _topic_phrase(paper, analysis_text)
    evidence = _extract_sentences(analysis_text, ["motivat", "problem", "challenge", "goal", "question", "agent", "system"], 2)
    base = f"这篇论文主要围绕 {topic} 展开，核心动机大概率是解释或改善该问题在组织与信息系统场景中的可行性、治理方式或业务价值。"
    if evidence:
        return base + " 从可读取文本中，尤其值得关注的线索包括：" + "；".join(evidence) + "。"
    return base + " 当前没有更多可直接提炼的全文证据，因此这部分仍以摘要级判断为主。"


def _method_zh(paper: PaperRecord, analysis_text: str) -> str:
    text = f"{paper.title} {analysis_text}".lower()
    if paper.is_survey_candidate:
        return "从文本信号看，这篇论文更像综述或框架型工作，方法上大概率采用文献梳理、主题分类、概念框架整合或研究议程构建。"
    if "experiment" in text or "benchmark" in text or "simulation" in text:
        detail = _extract_sentences(analysis_text, ["experiment", "benchmark", "simulation", "evaluate", "compare"], 2)
        lead = "从文本看，论文方法更偏实验或 benchmark 评估，通常会设定任务环境、比较基线模型，并用多项指标检验效果差异。"
        return lead + (" 方法细节线索：" + "；".join(detail) + "。" if detail else "")
    if "case study" in text or "field" in text or "survey data" in text:
        detail = _extract_sentences(analysis_text, ["case", "field", "survey", "dataset", "sample"], 2)
        lead = "从文本看，这篇论文可能采用案例研究、现场研究或问卷/档案数据分析，以验证智能体相关变量在组织情境中的作用。"
        return lead + (" 方法细节线索：" + "；".join(detail) + "。" if detail else "")
    if "framework" in text or "model" in text:
        detail = _extract_sentences(analysis_text, ["framework", "model", "design", "architecture"], 2)
        lead = "从文本看，论文可能先提出概念模型或分析框架，再通过案例、实验或示例任务来展示框架的解释力。"
        return lead + (" 方法细节线索：" + "；".join(detail) + "。" if detail else "")
    detail = _extract_sentences(analysis_text, ["method", "approach", "design", "evaluate"], 2)
    lead = "仅根据当前可用文本判断，这篇论文的方法更像“问题建模 + 方法设计/评估”的组合。"
    return lead + (" 可继续验证的线索：" + "；".join(detail) + "。" if detail else " 建议阅读全文后进一步确认其识别策略与评估方式。")


def _experiment_process_zh(paper: PaperRecord, analysis_text: str) -> str:
    text = f"{paper.title} {analysis_text}".lower()
    if paper.is_survey_candidate:
        detail = _extract_sentences(analysis_text, ["review", "literature", "classification", "framework"], 2)
        lead = "如果按综述型论文阅读，可重点追踪样本来源、纳入排除标准、分类维度与比较框架，并检查作者如何组织已有研究的主线。"
        return lead + (" 现有文本线索：" + "；".join(detail) + "。" if detail else "")
    if "benchmark" in text or "simulation" in text:
        detail = _extract_sentences(analysis_text, ["task", "dataset", "baseline", "metric", "simulation", "benchmark"], 3)
        lead = "实验过程大概率包括任务设定、数据或环境准备、基线模型选择、关键参数设置、性能指标评估以及稳健性比较。"
        return lead + (" 从文本中能看到的过程线索有：" + "；".join(detail) + "。" if detail else " 全文阅读时建议重点核对实验环境与评价指标是否充分。")
    if "case" in text or "field" in text:
        detail = _extract_sentences(analysis_text, ["sample", "data", "case", "field", "collect", "measure"], 3)
        lead = "实验或实证过程可能围绕研究场景选择、变量构造、数据收集、模型估计与结果解释展开。"
        return lead + (" 从文本中能看到的过程线索有：" + "；".join(detail) + "。" if detail else " 全文阅读时应特别关注样本边界与识别策略。")
    detail = _extract_sentences(analysis_text, ["data", "task", "evaluate", "result", "metric"], 3)
    lead = "当前无法完整还原实验流程，但阅读全文时建议优先提取研究对象、数据来源、变量或任务设定、比较基线、评价指标和稳健性处理。"
    return lead + (" 现有文本线索：" + "；".join(detail) + "。" if detail else "")


def _core_contribution_zh(paper: PaperRecord, analysis_text: str) -> str:
    evidence = _extract_sentences(analysis_text, ["conclusion", "result", "finding", "contribute", "impact", "improve"], 3)
    if paper.summary_zh:
        base = f"{paper.summary_zh} 结合候选评分结果看，它的核心价值在于为你当前主题提供一个可直接进入精读的切入口。"
    else:
        base = f"从题目、文本与来源看，这篇论文的主要贡献很可能在于把 {_topic_phrase(paper, analysis_text)} 的某个关键问题讲清楚，并提供可迁移到 IS 研究中的理论或方法抓手。"
    if evidence:
        return base + " 当前可提炼的结论线索包括：" + "；".join(evidence) + "。"
    return base


def _extension_critique_zh(paper: PaperRecord, analysis_text: str) -> str:
    if paper.is_survey_candidate:
        return "可扩展方向在于把综述中涉及的变量、任务类型和治理机制进一步结构化，转化成可检验的命题。批判性地看，需要留意其覆盖范围是否偏窄、分类是否足够稳定，以及是否忽略了具体业务场景差异。"
    evidence = _extract_sentences(analysis_text, ["limitation", "future", "boundary", "generaliz", "bias"], 2)
    lead = "后续可以从外部效度、场景边界、人机协同机制和治理约束四个方向继续扩展。批判性阅读时，建议重点检查样本代表性、指标设计、基线选择以及结果能否真正迁移到企业或 IS 场景。"
    return lead + (" 已暴露的局限或边界线索：" + "；".join(evidence) + "。" if evidence else "")


def render_candidates_markdown(query: str, papers: Iterable[PaperRecord], date_label: str, query_variants: List[str] | None = None) -> str:
    lines = [
        f"# 候选文献清单 - {date_label}",
        "",
        f"- 检索关键词: `{query}`",
        f"- 输出定位: `candidates.md` 用于人工确认，`bundle.json` 仅供脚本串联",
        "",
    ]
    if query_variants:
        lines.append("## IS 检索模板")
        lines.append("")
        for variant in query_variants:
            lines.append(f"- `{variant}`")
        lines.append("")
    for index, paper in enumerate(papers, start=1):
        lines.extend(
            [
                f"## {index}. {paper.title}",
                "",
                f"- 编号: `{paper.id}`",
                f"- 作者: {', '.join(paper.authors) if paper.authors else 'Unknown'}",
                f"- 来源: {paper.venue} ({paper.venue_type})",
                f"- 年份: {paper.year or 'Unknown'}",
                f"- DOI: {paper.doi or 'N/A'}",
                f"- 被引次数: {paper.citation_count}",
            ]
        )
        if paper.score is not None:
            lines.append(f"- 相关性评分: {paper.score}")
        if paper.recommendation_reason:
            lines.append(f"- 推荐理由: {paper.recommendation_reason}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_note(
    paper: PaperRecord,
    date_label: str,
    full_text: str = "",
    full_text_path: str = "",
    note_sections: dict[str, str] | None = None,
) -> str:
    authors = ", ".join(paper.authors) if paper.authors else "Unknown"
    yaml_tags = [f'"{tag}"' for tag in paper.tags]
    inline_tags = [_obsidian_tag(tag) for tag in paper.tags]
    analysis_text = _analysis_text(paper, full_text)
    sections = note_sections or {}
    overview = sections.get("overview") or paper.summary_zh or paper.recommendation_reason or "这篇文献值得进入精读阶段。"
    problem_motivation = sections.get("problem_motivation") or _research_problem_zh(paper, analysis_text)
    method_design = sections.get("method_design") or _method_zh(paper, analysis_text)
    research_process = sections.get("research_process") or _experiment_process_zh(paper, analysis_text)
    findings_contributions = sections.get("findings_contributions") or _core_contribution_zh(paper, analysis_text)
    extensions_critique = sections.get("extensions_critique") or _extension_critique_zh(paper, analysis_text)
    lines = [
        "---",
        f'title: "{paper.title.replace(chr(34), chr(39))}"',
        f"date_confirmed: {date_label}",
        f"paper_id: {paper.id}",
        f"venue: {paper.venue}",
        f"venue_type: {paper.venue_type}",
        f"year: {paper.year or ''}",
        f'doi: "{paper.doi}"',
        f"score: {paper.score or ''}",
        "status: confirmed",
        f"tags: [{', '.join(yaml_tags)}]",
        "---",
        "",
        f"# {paper.title}",
        "",
        f"- 作者: {authors}",
        f"- 来源: {paper.venue}",
        f"- 年份: {paper.year or 'Unknown'}",
        f"- DOI: {paper.doi or 'N/A'}",
        f"- 被引次数: {paper.citation_count}",
        f"- 推荐理由: {paper.recommendation_reason}",
        f"- 笔记依据: {_analysis_basis(full_text_path)}",
        f"- 标签: {' '.join(inline_tags) if inline_tags else '#candidate'}",
        "",
        "## 一句话定位",
        "",
        overview,
        "",
        "## 1. 研究问题与动机",
        "",
        problem_motivation,
        "",
        "## 2. 模型或实验方法",
        "",
        method_design,
        "",
        "## 3. 实验过程",
        "",
        research_process,
        "",
        "## 4. 核心结论与贡献",
        "",
        findings_contributions,
        "",
        "## 5. 扩展方向与批判性评价",
        "",
        extensions_critique,
        "",
        "",
    ]
    return "\n".join(lines)


def note_filename(paper: PaperRecord) -> str:
    date_token = _publication_date_token(paper)
    author_token = _first_author_token(paper)
    title_token = slugify(paper.title)[:80] or paper.id
    return f"{date_token}_{author_token}_{title_token}.md"


def note_link(date_label: str, paper: PaperRecord) -> str:
    return f"{date_label}/{note_filename(paper).removesuffix('.md')}"


def render_daily_report(query: str, papers: List[PaperRecord], date_label: str) -> str:
    lines = [
        f"# 每日文献报告 - {date_label}",
        "",
        f"- 检索关键词: `{query}`",
        f"- 已确认文献数: {len(papers)}",
        "",
        "## 今日确认文献",
        "",
    ]
    for index, paper in enumerate(papers, start=1):
        lines.extend(
            [
                f"### {index}. {paper.title}",
                "",
                f"- 笔记链接: [[{note_link(date_label, paper)}]]",
                f"- 来源: {paper.venue}",
                f"- 相关性评分: {paper.score or 'N/A'}",
                f"- 被引次数: {paper.citation_count}",
                f"- 推荐理由: {paper.recommendation_reason}",
                f"- 中文总结: {paper.summary_zh}",
                f"- 研究建议: {paper.research_suggestion_zh}",
                f"- 商业应用想法: {paper.business_application_zh}",
                f"- 标签: {' '.join(_obsidian_tag(tag) for tag in paper.tags) or '#candidate'}",
                "",
            ]
        )

    lines.extend(
        [
            "## 当日观察",
            "",
            "- 今天的文献组合依旧偏向综述与框架型切入，适合先构建知识地图，再补实证与方法论文。",
            "- 来自 ISR、MISQ、Management Science 的论文更适合沉淀理论抓手；顶会论文更适合补方法与系统能力。",
            "- 建议优先把每篇文献中的变量、场景、评估指标摘出来，逐步形成可复用的研究设计库。",
            "",
        ]
    )
    return "\n".join(lines)
