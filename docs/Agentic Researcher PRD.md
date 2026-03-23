<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Agentic Researcher PRD

## 项目名称

Agentic Researcher：基于 Zotero–Obsidian–VSCode Claude/Codex 的半自动化科研文献阅读与研究协作系统[^1][^2][^3]

## 项目背景与目标

### 背景

信息系统（IS）和计算机科学（CS）领域 agentic AI 论文快速增长，覆盖 Information Systems Research、MIS Quarterly、Management Science 及 AAMAS、NeurIPS、ICML、AAAI、IJCAI 等顶会，从 survey 开始优先阅读，每天限 10 篇确认高分文献。[^4][^5][^6][^7][^8][^9]
传统工作流需多工具切换，Zotero 管理文献、Obsidian 笔记、VSCode 自动化，现优化为 Zotero 后端同步更新、Obsidian 前端显示已确认阅读文献。
目标：自动化发现、VSCode 内 Claude/Codex 插件评分标签生成及日报（含研究方向与商业应用想法），用户仅确认并阅读。[^2][^10]

### 目标

建立 Zotero–Obsidian–VSCode Claude/Codex 系统，每天推送 10 篇高相关 survey 等文献至 Obsidian，用户确认后 Zotero 同步标签/PDF，确保高效阅读与知识图谱构建。[^11][^12][^1]

## 项目角色与目标用户

### 主要用户

- PhD 学生（IS/CS，聚焦 agentic AI × 商业场景 × IS 理论，从 survey 开始，每天 10 篇确认阅读）。
- 导师（接收含研究方向及商业想法的日报/周报）。[^12]


### 其他利益相关方

HKU 图书馆（导出 RIS/CSV 至 Zotero）；Zotero/Obsidian 社区插件（Zotero Integration、BeterBibTeX）。[^13][^14]

## 核心原则与约束

### 设计原则

- Zotero 后端：存储 PDF/BibTeX/标签，同步用户确认的 10 篇/天高分文献（优先 survey，从指定期刊/会议）。
- Obsidian 前端：显示已同步阅读笔记、研究地图、日报（LLM 生成研究方向/商业想法）。
- VSCode + Claude Code/Codex 插件：自动化引擎，直接调用 LLM 评分/标签/日报生成，无需 Perplexity/Gemini。[^3][^10][^2]
- LLM 仅生成草稿（评分 0-10、标签如 \#survey \#agentic-ai \#banking，用户确认后 Zotero 更新）。


### 约束

仅 VSCode + Obsidian 切换；Python 脚本用 Claude/Codex 生成；Zotero 保留引用管理；每天 10 篇，从 survey 优先。[^15][^16]

## 业务价值

| 维度 | 传统痛点 | 本项目收益 |
| :-- | :-- | :-- |
| 文献发现 | 手动搜索遗漏 | 每天自动 10 篇指定源 survey 等，Zotero 同步确认项 [^6][^13] |
| 筛选 | 主观疲劳 | Claude/Codex 评分/标签，用户确认 10 篇 [^2][^17] |
| 笔记/地图 | 手动同步 | Obsidian 集中，自动更新地图 [^1][^12] |
| 汇报 | 临时撰写 | LLM 生成日报（含研究方向/商业想法） [^17][^18] |

## 系统架构

Zotero ↔ Python 脚本 (VSCode Claude/Codex 生成) ↔ Obsidian → 用户确认 → Zotero 更新。[^11][^2]

- **Zotero Backend**：PDF/元数据/标签（\#confirmed \#score-9 等），BetterBibTeX 生成 ID。[^1]
- **Obsidian Frontend**：插件 Zotero Integration/ZotLit/Templater/Dataview；目录：01_literature/（确认笔记）、02_reports/。[^12][^11]
- **VSCode Automation**：Claude Code/Codex 插件运行脚本，调用 LLM API 评分/生成日报。[^10][^2][^3]
- 无外部 LLM 服务，所有在 VSCode 内。[^15]


## 核心功能

### 每日文献发现

脚本 import_hku.py（Claude 生成）：HKU RIS/CSV → Zotero 导入 → 生成 Obsidian 候选列表（每天 10 篇 survey 优先，从 ISR/MISQ/Management Science/AAMAS 等）。[^14][^13]

### LLM 评分与标签

daily_score.py（Claude/Codex）：读候选摘要，LLM prompt 评分（相关性 0-10，优先 survey）、标签（\#agentic-ai \#commercial \#IS-theory），输出 JSON，用户确认 10 篇 → Zotero 同步标签/PDF → Obsidian 笔记。[^17]

### 阅读笔记自动化

Obsidian 插件同步 Zotero 高亮；用户在确认 10 篇笔记中微调；LLM prompt 生成初稿（用 Claude/Codex）。[^1][^12]

### 日报生成

daily_report.py：LLM prompt 生成“今日确认文献的 summary、研究方向建议、商业场景应用想法”，存 02_reports/daily/YYYY-MM-DD.md。[^18][^17]

## 数据流与每日流程

1. HKU 导出 RIS → Zotero 导入。
2. VSCode: python import_hku.py → 候选列表。
3. VSCode: python daily_score.py → 评分/标签 JSON，用户确认 10 篇 → Zotero 更新。
4. Obsidian: 阅读/微调笔记，插件同步。
5. VSCode: python daily_report.py → 日报（研究方向/商业想法）。

## 用户每日体验

### 早上 (VSCode)

```
python import_hku.py --input data/YYYY-MM-DD.ris
python daily_score.py --input candidates.md
```

确认 JSON，选 10 篇 → Zotero 同步。[^2]

### 白天 (Obsidian)

查看确认笔记，阅读/高亮同步，用 LLM 草稿微调日报（含想法）。[^12]

### 晚上 (VSCode + Obsidian)

```
python daily_report.py
```

发日报给导师。[^10]

## 项目里程碑

| 里程碑 | 时长 | 产出 |
| :-- | :-- | :-- |
| 1. 环境 | 1 周 | Zotero–Obsidian 同步 + VSCode Claude/Codex [^2][^3] |
| 2. 脚本 | 2 周 | 4 个 Python 脚本（Claude 生成） |
| 3. 测试日报/地图 | 1 周 | 首份含商业想法日报 + 地图 |
| 4. 迭代 | 2 周 | 稳定系统 + 周报反馈 |
| 5. 收尾 | 1 周 | 项目文档，作为设计科学基础 |

<span style="display:none">[^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29]</span>

<div align="center">⁂</div>

[^1]: https://github.com/mgmeyers/obsidian-zotero-integration

[^2]: https://marketplace.visualstudio.com/items?itemName=dliedke.ClaudeCodeExtension

[^3]: https://community.openai.com/t/vscode-extension-with-api-key/1355263

[^4]: https://www.tandfonline.com/doi/abs/10.1080/08874417.2025.2483832

[^5]: https://cto.aom.org/discussion/misqe-special-issue-on-ai-in-the-enterprise-full-paper-deadline-march-1st-2026

[^6]: https://www.aamas2024-conference.auckland.ac.nz/accepted/papers/

[^7]: https://www.linkedin.com/posts/andrewyng_neurips-received-21575-paper-submissions-activity-7401399616883380224-G0wo

[^8]: https://icml.cc/virtual/2025/poster/44029

[^9]: https://multiagents.org/2026/

[^10]: https://code.claude.com/docs/en/overview

[^11]: https://obsidian.md/plugins?search=zotero

[^12]: https://girlinbluemusic.com/how-to-connect-zotero-and-obsidian-for-the-ultimate-phd-workflow/

[^13]: https://forums.zotero.org/discussion/87944/export-library-in-csv-format

[^14]: https://www.wispaper.ai/en/faq/how-to-export-the-literature-in-zotero-as-ris-files

[^15]: https://www.reddit.com/r/ClaudeAI/comments/1i3l7rb/use_claude_to_make_bash_andor_python_scripts_they/

[^16]: https://www.youtube.com/watch?v=AuQMLfeHWe8

[^17]: https://www.linkedin.com/pulse/llm-prompt-research-paper-analysis-simplifying-academic-hani-simo-rp24f

[^18]: https://www.reddit.com/r/PromptEngineering/comments/1lnsu1q/a_universal_prompt_template_to_improve_llm/

[^19]: https://www.reddit.com/r/ObsidianMD/comments/186g1ak/whats_the_latest_optimal_workflow_from_zotero/

[^20]: https://forum.obsidian.md/t/zotero-better-notes-plugin-syncs-notes-with-obsidian/62272

[^21]: https://www.youtube.com/watch?v=hRCiuycpAIU

[^22]: https://pubmed.ncbi.nlm.nih.gov/27542184/

[^23]: https://forums.zotero.org/discussion/112942/zotero-7-obsidian-integration

[^24]: https://www.tiktok.com/@sabrina_ramonov/video/7516976272031894815

[^25]: https://www.linkedin.com/posts/devopschat_how-to-integrate-a-local-llm-into-vs-code-activity-7364537696259674112-lvH5

[^26]: https://dev.to/chand1012/the-best-way-to-do-agentic-development-in-2026-14mn

[^27]: https://www.reddit.com/r/codex/comments/1quaute/what_is_the_best_way_to_run_codex_in_vscode_what/

[^28]: https://www.youtube.com/watch?v=ScXGpZRZ7Ck

[^29]: https://www.youtube.com/watch?v=0lL94h1z72A
