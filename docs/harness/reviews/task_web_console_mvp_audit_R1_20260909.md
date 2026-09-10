# 审查文：task_web_console_mvp · 20-task-audit R1

> **审查帽**：20-task-audit（task 书面审查 · 不实现代码 · 不改 task 实质内容）
> **被审 task**：`docs/tasks/active/task_web_console_mvp.md`（task_slug：`web_console_mvp`）
> **对照真值**：`docs/spec/web-research-agent/SPEC-web-research-agent_v1.md`（signed · HG-SPEC-SIGNOFF=approved）+ `docs/spec/_source/PRD_web_research_agent_v2.md`
> **结构真值**：`docs/harness/templates/TASK_TEMPLATE.md`
> **审查日期**：2026-09-09 · 轮次：R1

---

## 结论摘要

| 维度 | 结论 |
|------|------|
| **内容** | **PASS · 零内容阻塞** —— 范围/非范围/验收/failure_paths/思考轮全部可观测、可回溯 SPEC/PRD，无占位、无空槽 |
| **流程闸** | HG-TASK-DRAFT=approved ✅；**HG-AUDIT-R1=pending**（本审查不建议绕过，须维护者人签） |

**总体结论：PASS —— 建议维护者人签 HG-AUDIT-R1（见文末签闸清单）。**

---

## 机械闸复核（实测）

| 闸 | 命令 | exit code | 结果 |
|----|------|-----------|------|
| task lint | `npx --yes dsh-coding-kit@1.10.0 task lint --file docs/tasks/active/task_web_console_mvp.md` | **0** | LINT: PASS |
| gate-check | `npx --yes dsh-coding-kit@1.10.0 gate-check --task docs/tasks/active/task_web_console_mvp.md` | **2** | 符合预期：HG-AUDIT-R1=pending → 拒 30（人签前的正确状态，非内容缺陷） |

> gate-check exit=2 是「流程闸未签」的真实反映：维护者签 HG-AUDIT-R1=approved 后应复跑确认放行。

---

## 审查核对项（逐条）

### 1. SPEC 边界一致性 ✅

- 范围 10 条全部落在 SPEC 范围第 3 条（前端单页控制台）、第 4 条（状态机 SSE 可观测）、第 5 条（界面层简易权限）之内，无越界实现子图业务逻辑（非范围第 4 条显式排除，仅消费契约）。
- 非范围与 SPEC 非范围 1/2/3 及 PRD §8.4/§9.2 双向锁定（批量/历史、像素级分析、认证体系）；Streamlit 弃选与 SPEC R2 分叉一裁定一致。
- 进程拓扑（Flask 仅渲染、API/SSE 全走 FastAPI）系 SPEC 审计 R1 观察项②的钉死结论，与 SPEC R2 分叉一「Flask 原生支持…与 FastAPI 后端契约一致」主表述一致，且已落入范围、验收（拓扑确认行）与 R2 分叉二，闭环完整。

### 2. 验收可回溯 A1–A9 ✅

- 本 task 承接 A1/A2/A3/A4/A5/A8/A9 的**页面侧**判据，逐条可勾选、可观测；A5 闭环（一票否决项）表述与 PRD §8.3 / SPEC A5 逐字对齐（工单号非空 + 与 Tool Node 回调一致）。
- A6（铁律一审计）由 `task_web_acquisition_subgraph.md` 验收行承接（日志 grep + screenshot_path 可追溯）；A7（2核4G 资源上限）由 `task_internal_rag_subgraph.md` 承接（容器限额 + RSS 峰值钉死）；SPEC A3 的块长 512–1024 tokens 断言在对外 task（切分产出端），控制台侧仅渲染，职责切分合理。**三 task 合起来 A1–A9 无漏项。**
- 额外验收行（全量测试命令、lint-wiki-delta、SSE 断线演练、拓扑确认路由断言）均为模板默认或审计观察项落地，无不可判项。

### 3. failure_paths 四列 ✅

- 6 行全部四列齐备（触发→行为→可重试→用户可见），首行为模板要求的流程闸拒开工行。
- 与 SPEC failure_paths 不矛盾：SSE 中断行与 SPEC 第五行语义一致（任务 ID 重连 + 补拉 + 内存态须日志可查）；对内回填失败行与 SPEC 第四行一致（结论照出、回执标失败、终态 Done(回填失败)）；上游失败行声明文案与对外 task 失败路径表对齐，跨 task 一致性好。

### 4. 思考轮 R0/R1–R5 + 控制表 ✅

- R0–R5 六槽全部填实无空槽；R2 含两个分叉（框架选型引用 SPEC 裁定不重开 + 进程拓扑 ≥2 方案对比表，推荐/弃选理由俱全）。
- 思考轮控制表填实：`early_stop=no`，reason 合法（功能 Epic 不适用跳轮），residual_risks 3 条真实（内存态丢失、角色开关无认证、Supervisor 薄壳归属默认假设）。

### 5. Harness 元信息 ✅

- 必填字段无占位：graph_delta=none 与 wiki_delta=none 均附 note 理由（本仓无 `docs/_tech_graph/`；`docs/coding_wiki/` 为空——已实测属实）；`invoke_retention_profile=default` 已选定；`semi_auto=false`；`required_invoke_hats=10,30,40`（default 集合，不含 20，故本帽无需 invoke 快照落盘）。
- 人工闸表两行与模板一致，HG-TASK-DRAFT=approved（人签 2026-09-09）与 gate-check 实测一致。

### 6. 依赖与双轨 Mock 解耦 ✅

- 跨 task 依赖为相对路径且实测存在：`./task_web_acquisition_subgraph.md`、`./task_internal_rag_subgraph.md`、`docs/spec/web-research-agent/SPEC-web-research-agent_v1.md`、`docs/harness/reviews/spec_web-research-agent_audit_R1_20260909.md` 全部真实落盘。
- Mock 解耦声明与 PRD §6.2 契约一致：Mock Payload 字段（`screenshot_path`/`extracted_meta`/`pre_chunks[]`）与 PRD §6.2 JSON 逐字段吻合；`section_path`/`xpath` 溯源字段回溯 PRD §4.3；Mock 结论三字段（竞品价格/风险等级/建议动作）与 PRD §3.2 Step 3 / §5.2 一致。acquisition 与 internal 可并行声明符合 PRD §2.2 双轨策略。
- 必读列表中 `AGENTS.md`/`docs/meta/`/`docs/standards/` 已注明「若存在」「当前缺失时按仓通用约定执行」（实测确缺失），无悬空硬依赖。

### 7. checklist 提醒（K7 · 非机械闸）

- 本 task 为新建功能（greenfield 页面 + 端点），非「改默认值/校验/策略门/fallback 语义」的行为变更类 task，「旧测 grep 影响面」项不适用，无需补列。

---

## 非阻塞观察项（不阻 PASS · 供维护者与 00 知悉）

1. **chain_prompt 路径未落盘**：元信息 `chain_prompt=docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md` 在本仓尚不存在；task 已自注「00 派发 30 前补齐或改用等效链 Prompt」。属 00 派发期动作，非 task 内容缺陷。
2. **Supervisor 薄壳归属为默认假设**：依赖第 3 条默认本 task 承担 FastAPI 侧 Supervisor 触发接线，00 若另拆 task 需同步调整依赖节（已在 residual_risks 第 3 条披露）。
3. **CORS / 同源反向代理**为 30 实现细节（R3 已注明），两进程同机部署符合 PRD §2.3，无需 task 层再钉。

## 阻塞项

无。

## 回填清单（退回 10-task 项）

无 —— 不退回。

---

## 维护者签闸（20 后 · 30 前）

- [ ] 已读 R1 审查结论（本文 · PASS）
- [ ] 在 task 人工闸表将 HG-AUDIT-R1 改为 approved（维护者 · 日期）
- [ ] commit task 文档或确认已签
- [ ] 复跑 `npx --yes dsh-coding-kit@1.10.0 gate-check --task docs/tasks/active/task_web_console_mvp.md` 确认 exit=0
- [ ] 再下发 Harness 30 Prompt（下发前补齐或替换 chain_prompt，见观察项 1）

30 Agent 将以 task 表为准；pending 时必须拒开工（见 `docs/harness/prompts/TEMPLATE_30_gate_stop.md`）。

> 本审查文不构成 HG-AUDIT-R1 代签；人签仅维护者可为。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R1：lint PASS(exit 0) / gate-check exit 2（HG-AUDIT-R1 pending · 符合预期）；内容零阻塞，结论 PASS，建议人签 HG-AUDIT-R1 |
