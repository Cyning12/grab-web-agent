# Task：单页 Web 控制台 MVP —— 异步提交、SSE 进度与三步渐进式回填

> **状态**：`draft`  
> **关联图谱**：无（本仓尚无 `docs/_tech_graph/` flow 真值）  
> **落盘**：`docs/tasks/active/task_web_console_mvp.md`；验收后 `git mv` → `docs/tasks/done/`

---

## Harness 元信息

| 字段 | 值 |
|------|-----|
| **task_slug** | `web_console_mvp` |
| **test_strategy** | `recommended` |
| **test_strategy_note** | （非 not_applicable，无需填写） |
| **code_quality_bar** | `recommended` |
| **freeze_id** | none |
| **orchestration** | `Cursor Task 链` |
| **chain_prompt** | `docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md`（模板默认嵌入路径 · 本仓尚未嵌入，00 派发 30 前补齐或改用等效链 Prompt） |
| **semi_auto** | `false` |
| **audit_profile** | `full` |
| **invoke_retention_profile** | `default` |
| **required_invoke_hats** | `10,30,40` |
| **git_branch** | `task/web_console_mvp` |
| **worktree_root** | none（单仓工作目录；与双轨子图并行时是否开独立 worktree 由 00 派发时决定） |
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
| HG-TASK-DRAFT | pending | 22-R1, 30 | 初稿人扫 |
| HG-AUDIT-R1 | pending | 30 | 22 R1 落盘后人签 |

---

## 背景与目标

交付 PRD §3 + §8.2/8.3 的**单页 Web 控制台（MVP）**：一个 URL 输入框 + 一个「开始调研」按钮；`POST /api/task` 异步提交 + `GET /api/task/{id}/stream`（SSE）进度推送（10% / 50% / 100%）；同页三块区域渐进式回填（Step 1 预览区：整页截图缩略图 + 标题/Meta/状态码；Step 2 知识切片区：实时展示 `pre_chunks`；Step 3 结论回填区：结构化结论卡片 + 回填状态回执）；页面底部出现「已模拟写入内部系统（工单号：xxx）」成功提示完成闭环（PRD §8.3 一票否决项的页面侧）。

**进程拓扑（审计 R1 观察项② · 已钉死）**：**Flask 仅渲染页面模板，全部 API/SSE 端点由 FastAPI 进程提供**（SPEC R2 分叉一两种拓扑解读中选定前者）。Flask 不做任何数据接口，仅交付 HTML 骨架；页面内 vanilla JS（fetch / EventSource）直连 FastAPI。两进程同机部署（PRD §2.3 允许同机），FastAPI 需放行 Flask 页面来源的 CORS 或经同源反向代理。

---

## 范围

- [ ] Flask 进程：渲染单页模板（输入框 + 按钮 + 三块回填区骨架），不含任何业务 API 端点
- [ ] FastAPI 进程：`POST /api/task`（接收 URL，异步派发任务，立即返回任务 ID，不经 HTTP 长等待）+ `GET /api/task/{id}/stream` SSE 端点（推送进度 10% / 50% / 100% 与状态机迁移事件）
- [ ] 状态机 Pending → Fetching → Parsing → RAGing → Done 经 SSE 可观测（PRD §6.3 / SPEC 范围 4）
- [ ] Step 1 预览区：Fetching 完成后渲染整页截图缩略图（源自 Payload `screenshot_path`）+ 标题/Meta/HTTP 状态码
- [ ] Step 2 知识切片区：实时展示 `pre_chunks`（每条含标题/正文片段，附 `section_path`/`xpath`）
- [ ] Step 3 结论回填区：对内完成后渲染结构化结论卡片（竞品价格/风险等级/建议动作三字段）+ 回填状态回执
- [ ] 闭环验证提示：回填成功时页面底部显示「已模拟写入内部系统（工单号：xxx）」，工单号与对内 Tool Node 回调一致（SPEC A5）
- [ ] 界面层简易权限：URL 参数（如 `?role=admin`）最小实现——调研员视角仅见 Step 1+2；管理员视角可见 Step 3 且「重新生成」按钮可触发对内子图重跑并刷新结论区（SPEC A8）
- [ ] SSE 断线重连：前端按任务 ID 自动重连并补拉当前状态，重连超上限提示刷新（SPEC failure_paths 第五行）
- [ ] 失败可见性：任一失败路径触发时页面出现对应错误提示，任务状态不滞留中间态（SPEC A9）

## 非范围

- 多 URL 批量上传、任务历史列表、多页面（PRD §8.4/§9.2 · V2.0+）
- 账号认证体系 / 复杂权限管理（V1 仅界面层 URL 参数角色区分，无安全语义，SPEC 非范围 3）
- 前后端分离构建链 / 现代前端框架（PRD §7 MVP 选型：模板 + 少量 vanilla JS）
- 对外/对内子图业务逻辑实现（见 `./task_web_acquisition_subgraph.md` 与 `./task_internal_rag_subgraph.md`；本 task 仅消费其契约）
- Streamlit 方案（SPEC R2 分叉一已弃选）
- 像素级截图分析展示（铁律一；截图仅缩略图展示与人工复核入口）

---

## 依赖（跨 task 契约）

1. **依赖对外子图**：PRD §6.2 标准 Payload 契约（`screenshot_path`/`extracted_meta`/`pre_chunks[]`），见 `./task_web_acquisition_subgraph.md`。**可并行**：开发期以 Mock Payload 驱动三块回填区。
2. **依赖对内子图**：结论 JSON Schema（竞品价格/风险等级/建议动作）与回填回调（成功/失败/工单号），见 `./task_internal_rag_subgraph.md`。**可并行**：开发期以 Mock 结论 + Mock 工单号驱动 Step 3 与闭环提示。
3. **Supervisor 编排**：状态机迁移事件的产生依赖 LangGraph 主控图接线（由 00 决定归属：可在本 task 内交付 Supervisor 薄壳，或单独拆 task；本 task 默认承担 FastAPI 侧的 Supervisor 触发接线）。
4. SPEC：`docs/spec/SPEC-web-research-agent_v1.md`（A1/A2/A3/A4/A5/A8/A9 的页面侧判据）。

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| 22 未签 `HG-AUDIT-R1` 即 30 改码 | 执行 Agent **拒开工** | 是 | 须先 22 + 人签 |
| `POST /api/task` 入参非法（空/非 http/https/内网地址） | FastAPI 返回 4xx 与原因，不创建任务 | 是（用户改正后重新提交） | 输入框旁提示「请输入合法的目标 URL」 |
| SSE 连接中断（网络抖动/服务重启） | 前端按任务 ID 断线重连并补拉当前状态；后端任务状态不丢失（内存态可接受，须日志可查） | 是（前端自动重连，上限后提示刷新） | 进度条停滞超过阈值时提示「连接中断，正在重连」 |
| 上游子图失败（超时/反爬/解析为空/向量化失败） | SSE 推送终态 Error，页面渲染对应错误文案（文案与对外 task 失败路径表对齐） | 是（用户重新提交同一或新 URL） | 页面提示对应错误 + 状态 Error |
| 对内回填失败 | SSE 推送 Done(回填失败)，结论卡片照出，回执区标「写入失败」及原因 | 是（管理员「重新生成」） | 页面底部显示「模拟写入失败：原因」而非成功工单号 |
| Flask 渲染进程与 FastAPI 进程互不可达（部署错误） | 页面加载但 API 调用失败，前端捕获并提示 | 是（修复部署后刷新） | 页面提示「后端服务不可达」 |

---

## 验收标准

- [ ] 全量测试命令通过（本仓尚无 CI workflow；本 task `test_strategy=recommended`，30 至少落盘可执行的 E2E 演练脚本或手工验证清单并执行留痕）
- [ ] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过（wiki_delta 预检 · 与 PR CI sample `run:` 行逐字一致）
- [ ] **A1 异步提交与进度**：输入合法 URL 点击「开始调研」后前端不经 HTTP 超时即收到任务 ID；SSE 流中可依次观测 10% / 50% / 100% 进度事件与 Pending→Fetching→Parsing→RAGing→Done 状态迁移
- [ ] **A2 Step 1**：Fetching 完成后预览区渲染整页截图缩略图 + 标题/Meta/HTTP 状态码
- [ ] **A3 Step 2**：切片区实时展示 `pre_chunks`，每条含标题/正文片段且附 `section_path`/`xpath`
- [ ] **A4 Step 3**：对内完成后结论区渲染结构化 JSON 结论卡片（竞品价格/风险等级/建议动作三字段），非纯文本报告
- [ ] **A5 闭环（一票否决项）**：页面底部出现「已模拟写入内部系统（工单号：xxx）」，工单号非空且与对内 Tool Node 模拟回调返回值一致
- [ ] **A8 权限最小实现**：无参/调研员视角 Step 3 不可见；`?role=admin` 视角可见 Step 3 且「重新生成」触发对内子图重跑并刷新结论区
- [ ] **A9 失败可见性**：超时/反爬/回填失败三桩各演练一次，页面出现对应错误提示且任务落终态（Done(失败) 或 Error）
- [ ] **SSE 断线演练**：任务进行中断开 SSE，前端自动重连并补拉当前状态；重连超上限提示刷新
- [ ] **拓扑确认（审计观察项②）**：Flask 进程无任何 `/api/*` 路由；`POST /api/task` 与 SSE 端点仅存在于 FastAPI 进程（代码审查 + 路由清单断言）

---

## 给执行帽的必读列表

1. `AGENTS.md` · `docs/meta/PROJECT_CONFIG_*.md`（若存在）
2. 关联 SPEC：`docs/spec/SPEC-web-research-agent_v1.md`（已签收 · 范围第 3/4/5 条 / A1–A5/A8/A9 / R2 分叉一）
3. PRD 真值：`docs/spec/_source/PRD_web_research_agent_v2.md` §3、§6.1、§6.3、§8.2/8.3
4. 审计观察项：`docs/harness/reviews/spec_web-research-agent_audit_R1_20260909.md` 观察项 2（进程拓扑，已钉死为「Flask 仅渲染、API/SSE 全走 FastAPI」）
5. 并行轨 task：`./task_web_acquisition_subgraph.md`（Payload 契约）、`./task_internal_rag_subgraph.md`（结论 Schema 与工单号回调）
6. `docs/standards/CODING_*_L2`（若仓内存在则必读；当前缺失时按仓通用编码约定执行）

---

## 思考轮（10-task 预置 · 30/22 可续填）

### R0 · 读人聊 / 业务目标

PRD §3（新增核心章节）+ §8.2/8.3：控制台是用户唯一触点，完成态 = 单页三区块渐进回填 + 底部工单号闭环提示。A5 闭环是一票否决项；本 task 承接 SPEC A1–A5/A8/A9 的全部页面侧判据。

### R1 · 范围 / 非范围 / 角色与场景

范围锁定单页 + 双端点（POST + SSE）+ 三块回填区 + 状态机可观测 + 界面层角色开关。非范围排除批量/历史/认证体系/前端框架构建链，与 SPEC 非范围 1/3 及 PRD §8.4 双向锁定。角色：调研员（Step 1+2 复核）与管理员（Step 3 + 重新生成），以 URL 参数最小实现，无认证安全语义（SPEC residual_risks 已披露）。

### R2 · 方案对比（≥2 · 推荐 · 弃选）

**分叉一：前端框架 —— Flask + Jinja2 vs Streamlit**：SPEC R2 已裁定 Flask + Jinja2（SSE 契约与三块异步回填为 §3.1/3.2 硬需求，Streamlit rerun 模型结构性冲突），本 task 不重开。

**分叉二：Flask 与 FastAPI 进程拓扑（审计观察项② · 本 task 钉死）**

| 维度 | Flask 仅渲染 + API/SSE 全走 FastAPI（推荐 · 选定） | 同进程（FastAPI 内挂模板渲染） |
|------|------------------------------------------------------|--------------------------------|
| 与 SPEC R2 分叉一表述一致性 | 一致（「Flask 原生支持…与 FastAPI 后端契约一致」的直读） | 偏离（「或同进程」的另一解读） |
| 职责边界 | 渲染与 API 分离，Flask 无任何数据接口，边界最清晰 | 单进程简单但框架职责混杂 |
| PRD §2.3 部署形态 | 同机两进程，符合 | 同机单进程，亦符合 |
| V2 演进（批量/历史页） | 模板层独立演进，API 不动 | 演进时单进程内耦合面大 |

**推荐并钉死：Flask 仅渲染页面，API/SSE 全走 FastAPI。** 决定性理由：职责边界最清晰且与 SPEC R2 表格主表述一致；审计观察项②要求「明确其一」，本 task 选前者并写入范围与验收（拓扑确认行）。**弃选同进程方案**：两框架同进程职责混杂，V2 演进成本高。

### R3 · 边界 / 失败路径 / 安全与依赖

- **边界**：本 task 只消费契约（Payload / 结论 Schema / 状态机事件），不实现任何子图业务逻辑；Mock 数据驱动先行，双轨解耦（PRD §2.2）。
- **状态持久性**：任务状态内存态可接受（服务重启即丢，SPEC residual_risks 已披露），但必须日志可查，且 SSE 重连语义以任务 ID 补拉当前状态。
- **安全**：`POST /api/task` 入参复用对外轨 SSRF 白名单校验（http/https + 内网段拒绝）；LLM Key 等配置不落盘明文。
- **依赖**：FastAPI（SSE 流式）/ Flask + Jinja2 / vanilla JS（fetch + EventSource）；同机两进程部署（PRD §2.3），CORS 或同源反向代理为 30 实现细节。

### R4 · 验收标准 / 可测性 / test_strategy

`test_strategy: recommended`。理由：页面层以 E2E 演练与文档化手工验证为主（三块回填区渲染、SSE 事件序列、角色开关、断线重连均为可观测演示），但 A1+A5 必须以真实（或本地镜像目标页）E2E 闭环演练留痕（SPEC R4-4）；失败注入三桩（超时/反爬/回填失败）各演练一次（SPEC R4-5 的页面侧）。拓扑确认以路由清单断言机械化。

### R5 · 草稿就绪 · 移交判断

草稿就绪。范围/非范围/验收/failure_paths 全部可观测并可回溯 PRD §3/§6/§8 与 SPEC 条目；审计观察项②已钉死进程拓扑并落入范围与验收；跨 task 依赖与可并行性已明示（双轨 Mock 解耦）。移交路径：HG-TASK-DRAFT 人扫 → 20-task-audit R1 → HG-AUDIT-R1 人签 → 30 开工。

### 思考轮控制

| 项 | 值 |
|----|-----|
| early_stop | no |
| reason | 默认 R0–R5 全轮预置；功能 Epic 不适用 bugfix 跳轮 |
| residual_risks | 1) 内存态任务状态重启即丢（SPEC 已披露，V1 接受）；2) 界面层角色开关无认证，仅演示权限语义；3) Supervisor 薄壳归属本 task 为默认假设，00 如另拆 task 需同步调整依赖节 |

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| 30 实现 | ⏳ | |
| 40 自检 | ⏳ | |

---

## 测试策略（Harness）

**test_strategy**: `recommended`

- `recommended`：文档演练或抽样验证（E2E 闭环演练 + 失败注入三桩 + SSE 断线演练，留痕于自检结论）

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
| 2026-09-09 | 10-task bulk-split ×3 之三：Web 控制台 MVP 初稿（依据 SPEC v1 signed + PRD §3/§8.2/8.3；吸收审计 R1 观察项②：进程拓扑钉死为「Flask 仅渲染、API/SSE 全走 FastAPI」） |
