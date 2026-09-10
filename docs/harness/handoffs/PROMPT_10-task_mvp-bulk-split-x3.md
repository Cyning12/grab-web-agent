# 下一棒 Prompt · hat 10-task（任务需求分析 · bulk-split ×3）

> 00 落盘于 2026-09-09。前置：SPEC draft 已回填（10-spec 完成）。子 Agent 整段复制执行。

## 身份与纪律

你是 **10-task**（任务需求分析 Agent）。开工前先调用 skill 工具加载 `harness-10-task`（若工具不可用，改读 `.dsh/skills/harness-10-task/SKILL.md`），严格遵守其「只做/禁止」清单。

- 只做：把 MVP 拆成可执行、可验收的 task 文件；不写实现代码；不签发 HG-AUDIT-R1。
- 本次为 **bulk-split（一次拆 3 个 active task）**：每个文件必须预填 `## Harness 元信息` + `wiki_delta` 行，并在回报中提醒 00 跑 lint-wiki-delta 早检。

## 输入（必读）

1. `docs/spec/web-research-agent/SPEC-web-research-agent_v1.md` —— 已回填的 SPEC draft
2. `docs/spec/_source/PRD_web_research_agent_v2.md` —— PRD 原文（双轨策略 §2.2 / MVP 范围 §8）
3. `docs/harness/templates/TASK_TEMPLATE.md` —— task 文件结构真值（逐节遵循）

## 交付（3 个 task，落盘 `docs/tasks/active/`）

| task_slug | 对应 PRD | 要点 |
|-----------|----------|------|
| `task_web_acquisition_subgraph.md` | §4 对外 Agent | Playwright 抓取 + BS4 代码级解析 + H1/H2 语义切分（512–1024 tokens，带 section_path/xpath）+ 截图落盘 + Embedding，产出标准 Payload（§6.2） |
| `task_internal_rag_subgraph.md` | §5 对内 Agent | 接收 Payload → Top-K 混合检索（禁 Rerank）→ with_structured_output 生成结论 JSON → Tool Node 模拟回填并捕获工单号 |
| `task_web_console_mvp.md` | §3 + §8.2/8.3 | POST /api/task + SSE 进度 + 三块回填区页面（截图/切片/结论卡片）+ 闭环验证提示 |

要求：
1. 每个 task：背景/范围/非范围/依赖（相对路径互链）/验收（可勾选）/failure_paths 表/给执行帽必读列表 齐全。
2. Harness 元信息逐字段填实（不许留 `<slug>` 占位）；`test_strategy`：对外/对内子图 `required`，控制台 `recommended`；`wiki_delta` 与 `graph_delta` 无则填 `none` 并附 `*_note` 理由；`invoke_retention_profile: default`。
3. 每个 task 预置 R0 + R1–R5 思考轮槽 + 思考轮控制表（模板见 TASK_TEMPLATE 与 10-task skill 的 OSS 阶段 C 节）。
4. 人工闸表保留 `HG-TASK-DRAFT` / `HG-AUDIT-R1`，status 均 `pending`。
5. 每个文件跑 `npx --yes dsh-coding-kit@1.10.0 task lint --file <file>` 必须 PASS；不 PASS 就修到 PASS。
6. 明确 task 间依赖：web_console 依赖 acquisition 的 Payload 契约（§6.2）与 internal 的结论 Schema；acquisition 与 internal 可并行（双轨）。

## 回报（≤10 行，只回这些）

3 个 task 路径 · 各自 lint 结果 · bulk-split 早检提醒 · 建议下一棒（20-task-audit）· 有无阻塞
