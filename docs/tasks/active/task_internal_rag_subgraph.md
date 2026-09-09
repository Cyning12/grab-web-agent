# Task：对内子图 —— Top-K 检索、结构化结论与模拟回填（Internal RAG）

> **状态**：`draft`  
> **关联图谱**：无（本仓尚无 `docs/_tech_graph/` flow 真值）  
> **落盘**：`docs/tasks/active/task_internal_rag_subgraph.md`；验收后 `git mv` → `docs/tasks/done/`

---

## Harness 元信息

| 字段 | 值 |
|------|-----|
| **task_slug** | `internal_rag_subgraph` |
| **test_strategy** | `required` |
| **test_strategy_note** | （非 not_applicable，无需填写） |
| **code_quality_bar** | `strict` |
| **freeze_id** | none |
| **orchestration** | `Cursor Task 链` |
| **chain_prompt** | `docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md`（模板默认嵌入路径 · 本仓尚未嵌入，00 派发 30 前补齐或改用等效链 Prompt） |
| **semi_auto** | `false` |
| **audit_profile** | `full` |
| **invoke_retention_profile** | `default` |
| **required_invoke_hats** | `10,30,40` |
| **git_branch** | `task/internal_rag_subgraph` |
| **worktree_root** | none（单仓工作目录；与对外子图双轨并行时是否开独立 worktree 由 00 派发时决定） |
| **graph_delta** | `none` |
| **graph_delta_note** | 本仓尚无 `docs/_tech_graph/` 目录与 flow 真值，本 task 不新增图谱文件；后续引入图谱时再补 |
| **wiki_delta** | `none` |
| **wiki_delta_note** | `docs/coding_wiki/` 当前为空，无既有 wiki 页需更新；执行期沉淀的可复用经验于关账经验总结再评估晋升 |
| **wiki_promotion** | `none` |
| **related_pr** | （缺省 · 由 `gh pr view` 关联当前分支） |
| **close_pr_policy** | `required` |
| **close_pr_exempt_note** | （非 exempt，无需填写） |
| **experience_capture** | `recommended` |
| **experience_capture_note** | （非 not_applicable，无需填写） |
| **kpi_rubric** | `KPI_RUBRIC_v1_2` |
| **kpi_aggregator** | `CLOSE` |

### 人工闸

| human_gate_id | status | blocks_hats | 说明 |
|---------------|--------|-------------|------|
| HG-TASK-DRAFT | approved | 22-R1, 30 | 初稿人扫 · 人签 2026-09-09 会话 |
| HG-AUDIT-R1 | pending | 30 | 22 R1 落盘后人签 |

---

## 背景与目标

交付 LangGraph 编排下的**对内子图（Internal RAG，「读取+回写」轨）**：接收对外子图产出的标准 Payload（PRD §6.2，开发期可 Mock）→ 结合内部知识库（FAISS）做 Top-K 混合检索（**禁用 Rerank**）→ `with_structured_output` 强制生成符合内部 API Schema 的结论 JSON（竞品价格 / 风险等级 / 建议动作）→ 末节点 Tool Node **模拟** POST 回填内部系统并捕获回调状态（成功/失败/工单号）。本轨落实铁律三（瘦内耗：2 核 4G 资源盒内运行，唯一降级手段为截断 Top-K）。

---

## 范围

- [ ] 接收并解析 PRD §6.2 标准 Payload（含 `pre_chunks[]` 及其 `embedding`）；**禁止对内重算 Embedding**（铁律二）
- [ ] 基于 FAISS 的内部知识库 Top-K 混合检索（向量 + 标量过滤拼接），**显式禁用 Rerank**（铁律三 / SPEC 非范围 7）
- [ ] `with_structured_output` 生成结构化结论 JSON，Schema 至少含三字段：竞品价格、风险等级、建议动作（对应 SPEC A4）
- [ ] 空 chunks 输入时产出「信息不足」结论 JSON（承接对外解析为空失败路径，不报错中断）
- [ ] Graph 末节点 Tool Node **模拟** POST 回填内部系统，捕获回调状态（成功/失败/工单号），回填失败时保留结论仅标回执失败（SPEC failure_paths 第四行）
- [ ] 2 核 4G 资源盒内运行；内存逼近上限时降级为截断 Top-K（减少检索条数）完成生成并记录降级日志（SPEC failure_paths 末行）
- [ ] 子图状态上报钩子：RAGing → Done 状态迁移事件供 Supervisor/SSE 消费
- [ ] 「重新生成」入口：支持以同一 Payload 重跑对内子图（供控制台管理员按钮触发，SPEC A8）

## 非范围

- 网页抓取、解析、切分、截图、Embedding 计算（对外子图职责，见 `./task_web_acquisition_subgraph.md`）
- 检索重排序（Rerank）（铁律三，显式禁用）
- 接入真实企业 OA/CRM/Jira 审批流（PRD §9.3 · V2.0+；V1 仅模拟回填）
- 私有化大模型部署（PRD §9.4 · POC 期走外部 API，Key 不落盘明文）
- 前端页面与 SSE 端点（控制台职责，见 `./task_web_console_mvp.md`）
- 引入常驻重服务（如独立 Qdrant 进程；铁律三约束，Qdrant 为 V2 迁移候选）

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| 22 未签 `HG-AUDIT-R1` 即 30 改码 | 执行 Agent **拒开工** | 是 | 须先 22 + 人签 |
| Payload 契约校验失败（字段缺失/类型不符） | 子图入口拒绝，任务转终态 Error，记录契约违例日志 | 是（修复上游后重新提交） | 页面提示「数据契约异常」+ 状态 Error |
| 输入为空 chunks（对外解析为空） | 正常流转，产出「信息不足」结论 JSON，不视为错误 | 是（用户换 URL 重试） | 结论区显示信息不足结论 |
| LLM 生成失败或结构化输出校验失败 | 有限重试（≤2 次，防重试风暴），仍失败则任务终态 Error | 是（管理员「重新生成」） | 页面提示「结论生成失败」+ 状态 Error |
| 对内回填 API（模拟 Tool Node）失败 | 捕获回调失败状态，结论区仍展示已生成结论 JSON，回执区标注「写入失败」及原因；任务终态 Done(回填失败) | 是（管理员点「重新生成」重跑对内子图） | 页面底部显示「模拟写入失败：原因」而非成功工单号 |
| 2核4G 资源超限（内存逼近阈值） | 降级为截断 Top-K（减少检索条数）完成生成；记录降级日志 | 否（任务继续完成，质量降级） | 无感知；日志可观测降级事件 |

---

## 验收标准

- [ ] 全量测试命令通过（本仓尚无 CI workflow；30 须随实现落盘 `pytest tests -q` 等效测试入口并使其通过，后续 CI 接入时与仓 workflow 对齐）
- [ ] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过（wiki_delta 预检 · 与 PR CI sample `run:` 行逐字一致）
- [ ] **对内子图单测**：Mock chunks+向量 Payload 输入 → 断言结构化结论 JSON 三字段齐全（竞品价格/风险等级/建议动作）且通过内部 API Schema 校验（SPEC R4-2 / A4）
- [ ] **Tool Node 闭环**：模拟回填返回工单号非空，且与回调返回值一致（SPEC A5 闭环一票否决项的对内侧）
- [ ] **禁 Rerank 审计**：检索路径代码与日志中无 Rerank 调用；对内进程无 Embedding 模型加载（铁律二/三）
- [ ] **空 chunks 用例**：空 `pre_chunks` 输入产出「信息不足」结论 JSON，任务不中断
- [ ] **回填失败用例**：模拟 Tool Node 500 桩 → 结论 JSON 仍产出，回执标注失败原因，终态 Done(回填失败)（SPEC R4-5）
- [ ] **A7 资源上限（审计 R1 观察项① · 已钉死）**：对内子图进程在 `docker run --cpus=2 --memory=4g`（或等效 cgroup 限额：CPU=2 核、内存=4096MB）环境下完成一次完整任务（Mock Payload → 结论 → 模拟回填），不 OOM、无重试风暴（LLM 调用重试 ≤2 次）；**测量方式**：任务运行期间每 1s 采样对内进程 RSS（读 `/proc/<pid>/status` 的 VmRSS 或 `docker stats`），取全程峰值；**阈值：内存峰值 ≤ 3072MB（3GB）**，采样原始数据随测试报告留档
- [ ] **降级用例**：资源逼近阈值时触发截断 Top-K 降级，任务完成且日志含降级事件记录
- [ ] **重跑用例**：同一 Payload 触发对内子图重跑，产出新结论且不回写旧结果（支撑 SPEC A8「重新生成」）
- [ ] 状态迁移事件 RAGing → Done 可被 Supervisor 层观测（供 SSE 进度 50%→100% 映射）

---

## 给执行帽的必读列表

1. `AGENTS.md` · `docs/meta/PROJECT_CONFIG_*.md`（若存在）
2. 关联 SPEC：`docs/spec/SPEC-web-research-agent_v1.md`（已签收 · 范围第 2 条 / A4/A5/A7 / failure_paths / R3 铁律三边界）
3. PRD 真值：`docs/spec/_source/PRD_web_research_agent_v2.md` §5、§6.2、§8.3
4. 审计观察项：`docs/harness/reviews/spec_web-research-agent_audit_R1_20260909.md` 观察项 1（A7 阈值钉死，已吸收进本 task 验收）
5. 并行轨 task：`./task_web_acquisition_subgraph.md`（Payload 契约产出方）、`./task_web_console_mvp.md`（结论 Schema 消费方）
6. `docs/standards/CODING_*_L2`（若仓内存在则必读；当前缺失时按仓通用编码约定执行）

---

## 思考轮（10-task 预置 · 30/22 可续填）

### R0 · 读人聊 / 业务目标

PRD §5 + SPEC 范围第 2 条：对内子图是「读取+回写」轨，职责极简轻量。完成态 = Payload 输入 → Top-K 检索 → 结构化结论 JSON → 模拟回填并捕获工单号。PRD §8.3 闭环验证（页面底部工单号提示）的对内侧由本 task 交付，是一票否决项的产出源头。

### R1 · 范围 / 非范围 / 角色与场景

范围锁定 PRD §5.1–5.3 三节点职责 + 空 chunks 流转 + 「重新生成」入口（SPEC A8）。非范围显式排除 Rerank、真实审批流、私有化部署、常驻重服务，与 SPEC 非范围 5/6/7 及 R3 铁律三边界双向锁定。双轨策略（PRD §2.2）下本轨可全 Mock Payload 独立闭环，不阻塞对外轨。

### R2 · 方案对比（≥2 · 推荐 · 弃选）

**分叉：向量库 —— FAISS vs Qdrant**（继承 SPEC R2 分叉二结论，task 层确认）

| 维度 | FAISS（推荐 · V1） | Qdrant（V2 生产候选） |
|------|--------------------|------------------------|
| 资源占用（铁律三 · 2核4G） | 进程内库，零额外服务 | 独立服务进程，与对内 Agent 争资源 |
| 运维复杂度 | pip 依赖，无部署项 | 需额外容器/服务编排 |
| V1 单任务检索需求 | 充足 | 能力溢出 |

**推荐 FAISS（V1）**，与 SPEC R2 一致；**弃选 Qdrant（仅 V1 阶段）**，保留为 V2 迁移候选。**接口层抽象约束**：检索接口须抽象（向量库可替换），30 实现时不得把 FAISS 调用散落于业务逻辑（SPEC R2 遗留建议，写入非功能约束）。

### R3 · 边界 / 失败路径 / 安全与依赖

- **铁律二边界**：对内禁止重算 Embedding，Payload 缺 `embedding` 字段属契约违例（走失败路径第一行业务行）。
- **铁律三边界**：2核4G 资源盒内唯一允许的降级手段 = 截断 Top-K；禁止引入常驻重服务；**审计观察项①已吸收**：A7 阈值钉死为「容器限额 CPU=2/内存=4096MB + 每 1s 采样 RSS 峰值 ≤3072MB」，见验收 A7 行。
- **防重试风暴**：LLM 调用重试上限 ≤2 次（SPEC A7「不触发重试风暴」的操作化）。
- **回填失败不丢结论**：结论区照出，仅回执标失败（SPEC failure_paths 关键设计）。
- **依赖**：LangGraph（`with_structured_output`）/ FAISS / 外部 LLM API（POC）；LLM Key 不落盘明文。

### R4 · 验收标准 / 可测性 / test_strategy

`test_strategy: required`。可测性设计：Mock Payload（PRD §6.2 契约）使本轨完全离线可测；Tool Node 以可注入桩实现（成功桩/500 桩），工单号断言与 SPEC A5 闭环对齐；资源测试以容器限额 + 峰值采样落地 A7（采样脚本随测试制品落盘）。SPEC A4/A5/A7 由本 task 验收承接；A8 的「重新生成触发重跑」语义由本 task 提供入口、控制台 task 提供按钮。

### R5 · 草稿就绪 · 移交判断

草稿就绪。范围/非范围/验收/failure_paths 全部可观测并可回溯 PRD §5/§6.2/§8.3 与 SPEC 条目；审计观察项①（A7 数值与测量方式）已钉死进验收；R2 向量库结论与 SPEC 自洽并补接口抽象约束。移交路径：HG-TASK-DRAFT 人扫 → 20-task-audit R1 → HG-AUDIT-R1 人签 → 30 开工。

### 思考轮控制

| 项 | 值 |
|----|-----|
| early_stop | no |
| reason | 默认 R0–R5 全轮预置；功能 Epic 不适用 bugfix 跳轮 |
| residual_risks | 1) 内部知识库初始语料来源未定义（V1 接受空库/小样本库，检索质量不兜底）；2) 模拟回填的回调语义为自定桩，与真实内部系统（PRD §9.3）可能存在语义差；3) RSS 峰值采样在 macOS 开发机无 /proc，需以 docker stats 或 ps 等效实现，采样脚本属 30 实现制品 |

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| 30 实现 | ⏳ | |
| 40 自检 | ⏳ | |

---

## 测试策略（Harness）

**test_strategy**: `required`

- `required`：先可失败自动化测试再改实现（Mock Payload 单测 + 回填桩用例 + 资源峰值测试先行）

---

### 自检结论（执行者）

（30/40 回填）

---

### KPI（00）

（`kpi_aggregator: CLOSE` · 关账回溯填写 · 至少一种可解析分数：`Task_KPI%: N` / D1–D5 表 / 四维 1–5）

---

### 经验总结

（`experience_capture: recommended` · 关账时建议回填 ≥80 字或 ≥3 条列表）

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 10-task bulk-split ×3 之二：对内子图初稿（依据 SPEC v1 signed + PRD §5/§6.2；吸收审计 R1 观察项①：A7 内存阈值与测量方式钉死入验收） |
