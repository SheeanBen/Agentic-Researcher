# Agentic Researcher

这个工作区现在已经具备一套可运行的、以当前工作区为核心的文献工作流。
当前这个副本已经整理成适合公开的模板版：不包含真实 PDF、全文缓存、个人 API 配置和实际阅读产物，只保留代码、配置、测试、fixtures 与目录骨架。
仓库现在已内置 GitHub Actions 自动测试。

## 这是什么

Agentic Researcher 是一套面向信息系统研究者的轻量文献工作流。
它的目标不是替代 Zotero 或 Obsidian，而是把“检索 -> 候选评分 -> 人工确认 -> PDF 同步 -> 中文深度笔记 -> 日报”这条链路自动串起来。

适合的使用方式是：

- 用 `VSCode` 运行脚本与查看数据
- 用 `Obsidian` 打开同一个工作区，阅读和沉淀笔记
- 用 `Zotero + Attanger` 管理文献与 PDF，并把 PDF 同步到 `data/zotero_pdf/`

## 环境要求

- `Python 3.9+`
- `Git`
- `Obsidian`
- `Zotero`
- `Attanger` Zotero 插件
- `pdftotext`

如果你在 macOS 上，安装 `pdftotext` 最简单的方式是：

```bash
brew install poppler
```

安装完成后，可用下面命令检查：

```bash
pdftotext -v
python3 --version
```

## 推荐的本地软件与插件

- `VSCode`：运行脚本、查看 `bundle.json`、调试流程
- `Obsidian`：阅读 `01_literature/` 下的中文笔记与日报
- `Zotero`：管理文献条目与附件
- `Attanger`：把 Zotero PDF 同步到 `data/zotero_pdf/`

目前这套工作流的关键约定是：

- PDF 附件目录在 `data/zotero_pdf/`
- 提取出的纯文本缓存在 `data/fulltext/YYYY-MM-DD/`
- 历史去重只依赖 `03_state/confirmed/`
- 候选确认页只保留 `candidates.md`

## 首次配置

1. 克隆仓库后，先准备环境变量：

```bash
cp .env.example .env.local
```

2. 在 `.env.local` 中填写你的接口配置，例如：

```bash
OPENAI_API_KEY=your_api_key
# 可选
# OPENAI_BASE_URL=https://api.openai.com/v1/responses
```

3. 如果你要使用真实 API 生成评分和深度笔记，使用：

```bash
config/agentic_researcher.openai.json
```

4. 如果你只想离线测试流程，默认配置 `config/agentic_researcher.json` 也可以跑通。

## 最短使用路径

下面是一条最顺手的日常使用路径：

1. 检索候选文献
2. 对候选文献评分
3. 人工确认要读的文献
4. 等 Zotero/Attanger 把 PDF 同步到 `data/zotero_pdf/`
5. 自动或手动刷新中文笔记
6. 查看 `01_literature/` 与 `02_reports/daily/`

## 工作流

1. 用关键词发现文献。第一版支持 `fixture / RIS / CSV / Crossref` 四种来源：

```bash
python3 scripts/discover_papers.py --query "你的关键词" --source fixture
```

默认会优先在 IS 领域高优先级 venue 中检索，包括：
`ISR / MISQ / JMIS / JAIS / ISJ / EJIS / JIT / I&M / DSS / JSIS / ICIS / AMCIS / ECIS / PACIS / HICSS`，
并保留 `AAMAS / NeurIPS / ICML / AAAI / IJCAI` 作为补充。
系统会自动把你的原始关键词扩展成更适合 IS 研究的查询模板，并把这些模板写进候选页，便于你直接复查检索策略。例如会自动补入
`information systems / digital transformation / decision support systems / enterprise systems / IT governance / service operations`
等 IS 场景词，并在合适时重写成 `agentic AI / AI agents / autonomous agents / multi-agent systems`。
系统会自动扫描 `03_state/confirmed/*.json` 中历史已经确认过的文献，按 `DOI 优先 + 标题标准化回退` 去重，所以你不需要再从 Zotero 导出去重数据。

2. 对非重复文献做评分，并生成候选确认页。这个阶段每篇文献只保留公开元信息与一句简短中文推荐理由，便于快速确认：
   标题、作者、期刊/会议、年份、DOI、被引次数、评分、推荐理由。

```bash
python3 scripts/daily_score.py --input data/discovery/2026-03-22/bundle.json --query "你的关键词"
```

3. 确认最终阅读列表，并为每篇确认文献生成单独的中文 Obsidian 笔记。笔记会按 5 步法组织：
   研究问题与动机、模型或实验方法、实验过程、核心结论与贡献、扩展方向与批判性评价，
   并额外附上研究建议、商业应用想法。笔记默认全部使用中文，不再保留 LaTeX 公式提示。
   如果你已经把 Zotero 中的 PDF 同步到 `data/zotero_pdf/`，系统会在确认后自动尝试匹配 PDF、提取全文并缓存到 `data/fulltext/YYYY-MM-DD/`，然后用全文重写出更细的中文笔记。
   如果 PDF 是稍后才同步完成的，可以再执行一次：

```bash
python3 scripts/refresh_notes.py --date 2026-03-22
```

如果你希望 Zotero PDF 一进来就自动刷新当天笔记，可以常驻运行：

```bash
python3 scripts/watch_zotero_pdf.py --date 2026-03-22 --config config/agentic_researcher.openai.json
```

```bash
python3 scripts/confirm_candidates.py --input data/discovery/2026-03-22/bundle.json --top 10
```

4. 生成日报：

```bash
python3 scripts/daily_report.py --input 03_state/confirmed/2026-03-22.json
```

5. 如果你想一条命令跑完整链路，可以直接使用：

```bash
python3 scripts/run_daily_workflow.py --query "你的关键词" --source fixture --top 10
```

## 关键产物

- `data/discovery/YYYY-MM-DD/candidates.md`：人工确认页，只展示候选元信息、评分和推荐理由，并展示本轮 IS 检索模板
- `data/discovery/YYYY-MM-DD/bundle.json`：内部流程使用的轻量 bundle，仅供脚本串联，不建议人工维护
- `01_literature/YYYY-MM-DD/`：每天确认后的中文 Markdown 笔记目录，单篇命名规则为“发表日期_作者_标题”
- `02_reports/daily/`：每日报告
- `03_state/confirmed/`：每天确认后的文献清单 JSON
- `data/zotero_pdf/`：Attanger 同步出来的 Zotero PDF 目录
- `data/fulltext/YYYY-MM-DD/`：从 PDF 自动提取并缓存的全文文本目录，用于增强笔记细节

模板仓库默认会忽略以下运行产物，因此公开仓库会保持简洁：

- `01_literature/` 下的正式阅读笔记
- `02_reports/daily/` 下的日报
- `03_state/confirmed/` 下的确认历史
- `data/discovery/` 下的当天检索结果
- `data/fulltext/` 下的全文缓存
- `data/zotero_pdf/` 下的 PDF 附件

## 关于工作区去重

- 当前实现不会依赖 Zotero 去重，而是只扫描 `03_state/confirmed/` 中历史已经确认过的文献。
- 去重依据仍然是：
  - 规范化 DOI -> 文献标题
  - 规范化标题 -> 文献标题
- 这意味着只有你真正确认进入阅读流程的文献才会参与去重，候选但未确认的文献不会阻塞之后的检索。
- 如果后续历史规模继续增长，更好的下一步是把这层工作区历史索引落到 SQLite，而不是每次扫描 JSON。

## Codex / OpenAI 接入

- 默认 `llm.provider` 是 `heuristic`，所以离线也能跑通。
- 如果你要让候选评分和全文笔记都走真实 API，建议直接使用 `config/agentic_researcher.openai.json`：

```bash
python3 scripts/refresh_notes.py --date 2026-03-22 --config config/agentic_researcher.openai.json
```

- 当前 OpenAI 配置文件已切到 `gpt-5.4`，通过 `Responses API` 调用。
- 运行前需要在环境里提供 `OPENAI_API_KEY`；如果你走自定义中转，还需要提供 `OPENAI_BASE_URL`。

## 建议你下一步再补的内容

- 一份英文版简短 README，方便 GitHub 外部读者快速理解
- 一张工作流示意图，展示“检索 -> 候选 -> 确认 -> PDF -> 笔记”
- 一个 `demo` 目录，只保留最小示例，不放真实研究数据
