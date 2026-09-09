# 审查文：task_internal_rag_subgraph · 20-task-audit R1

| 项 | 值 |
|----|-----|
| 审查 hat | 20-task-audit（R1 · 书面审） |
| 被审 task | `docs/tasks/active/task_internal_rag_subgraph.md`（slug: `internal_rag_subgraph`） |
| 对照真值 | `docs/spec/SPEC-web-research-agent_v1.md`（signed · HG-SPEC-SIGNOFF=approved）+ `docs/spec/_source/PRD_web_research_agent_v2.md` |
| 结构真值 | `docs/harness/templates/TASK_TEMPLATE.md` |
| 前置 | HG-TASK-DRAFT=approved ✅（task 人工闸表） |
| 审查日期 | 2026-09-09 |

---

## 结论摘要

| 维度 | 结论 |
|------|------|
| **内容审查** | **PASS · 零内容阻塞** |
| **流程闸 HG-AUDIT-R1** | **pending**（本审查不构成签收；须维护者签 task 表 → approved，blocks 30） |
| **总结论** | **PASS（建议人签 HG-AUDIT-R1）** |

---

## 机械闸复核

| 命令 | exit code | 结果 |
|------|-----------|------|
| `npx --yes dsh-coding-kit@1.10.0 task lint --file docs/tasks/active/task_internal_rag_subgraph.md` | **0** | LINT: PASS |
| `npx --yes dsh-coding-kit@1.10.0 gate-check --task docs/tasks/active/task_internal_rag_subgraph.md` | **2** | 预期结果：HG-AUDIT-R1=pending → 拒 30。属**流程闸**未人签，非内容缺陷 |

---

## 逐项核对（内容）

| 核对项 | 结果 | 证据 |
|--------|------|------|
| 范围落在 SPEC 边界内 | ✅ | 范围 8 条全部对应 SPEC 范围第 2 条（对内子图）+ A4/A5/A7/A8；无越界（抓取/Embedding/前端均显式排除） |
| 非范围与 SPEC 双向锁定 | ✅ | 非范围 6 条对应 SPEC 非范围 5/6/7 + PRD §9.3/§9.4 + 铁律三（常驻重服务）；与 SPEC R3 边界一致 |
| 验收可回溯 A1–A9 | ✅ | A4（结论三字段）、A5（工单号非空且与回调一致 · 一票否决项对内侧）、A7（2核4G · 峰值 ≤3072MB · 测量方式钉死）、A8（同一 Payload 重跑入口）均承接；状态事件行支撑 A1/A9。A8 按钮 UI 归控制台 task，本 task 仅提供重跑入口，分工已在验收/R4 写明 |
| failure_paths 四列齐备 | ✅ | 6 行全部四列填实；「回填失败不丢结论」「资源超限截断 Top-K 降级」两行与 SPEC failure_paths 第 4/末行语义一致不矛盾；新增契约校验失败/空 chunks/LLM 重试≤2 三行与 SPEC 不冲突；首行模板闸行保留 |
| R0 + R1–R5 无空槽 | ✅ | R0–R5 全部填实；R2 含 FAISS vs Qdrant 对比表（推荐/弃选理由齐），与 SPEC R2 分叉二自洽并补接口抽象约束 |
| 思考轮控制表 | ✅ | early_stop=no；reason 合法（功能 Epic 不适用 bugfix 跳轮）；residual_risks 3 条具体（语料来源/桩语义差/macOS 无 /proc 需等效采样） |
| 元信息无占位 | ✅ | test_strategy=required；semi_auto=false；audit_profile=full；invoke_retention_profile=default（已选定）；required_invoke_hats=10,30,40（不含 20，按 v2.12 无需 20 invoke 快照）；freeze_id=none；graph_delta/wiki_delta=none 且 note 理由均在（与仓实况一致：无 `_tech_graph/`、`coding_wiki/` 仅 .gitkeep）；wiki_promotion=none；close_pr_policy=required |
| 依赖相对路径真实存在 | ✅ | `./task_web_acquisition_subgraph.md`、`./task_web_console_mvp.md` 均存在于 `docs/tasks/active/`；必读列表引用的 SPEC、PRD、SPEC 审计文均真实存在 |
| 双轨 Mock 解耦与 PRD §6.2 契约一致 | ✅ | 范围首条锁定 `pre_chunks[]` 含 `embedding`（与 PRD §6.2 Payload 字段一致）；禁止对内重算 Embedding（铁律二）；Mock Payload 独立闭环声明与 PRD §2.2「对内可 Mock 外部数据」一致，不阻塞对外轨 |
| SPEC 审计观察项吸收 | ✅ | `docs/harness/reviews/spec_web-research-agent_audit_R1_20260909.md` 非阻塞观察项①（A7 软表述钉死）已吸收进验收 A7 行：容器限额 CPU=2/内存=4096MB + 每 1s 采样 RSS 峰值 ≤3072MB（≤ SPEC 建议 3GB），采样数据留档 |
| 行为变更类「旧测 grep 影响面」（K7 checklist） | n/a | 本 task 为新功能交付，非改默认值/校验/策略门/fallback 语义，该项不适用 |

---

## 非阻塞发现（不退回，建议 00/30 阶段闭环）

1. **chain_prompt 路径仓内不存在**：`docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md` 尚未嵌入本仓。task 元信息已自注「00 派发 30 前补齐或改用等效链 Prompt」，披露充分；请 00 在 30 派发前闭环。
2. **必读列表引用 `AGENTS.md` 不存在**：条目以「若存在」语义兜底，影响轻微；30 开工时按仓实况跳过即可。
3. **residual_risks 第 3 条（macOS 无 /proc）**：已声明以 docker stats/ps 等效实现，属 30 实现制品；建议 30 在采样脚本落盘时注明等效采样方式，40 自检时复核。

## 阻塞缺口

无。

---

## 维护者签闸（20 后 · 30 前）

- [ ] 已读 R1 审查结论
- [ ] 在 task 人工闸表将 HG-AUDIT-R1 改为 approved（维护者 · 日期）
- [ ] commit task 文档或确认已签
- [ ] 再下发 Harness 30 Prompt

30 Agent 将以 task 表为准；pending 时必须拒开工（见 TEMPLATE_30_gate_stop.md）。

> 本审查不构成签收；HG-AUDIT-R1 仅人类可签。本棒禁止改 task 实质内容；如需内容修订退回 10-task。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R1 落盘：内容 PASS · 零阻塞；机械闸 lint=0 / gate-check=2（流程闸 pending 属预期）；建议人签 HG-AUDIT-R1 |
