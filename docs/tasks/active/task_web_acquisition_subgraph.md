# Task：对外子图 —— 网页采集、解析切分与标准 Payload 产出（Web Acquisition）

> **状态**：`draft`  
> **关联图谱**：无（本仓尚无 `docs/_tech_graph/` flow 真值）  
> **落盘**：`docs/tasks/active/task_web_acquisition_subgraph.md`；验收后 `git mv` → `docs/tasks/done/`

---

## Harness 元信息

| 字段 | 值 |
|------|-----|
| **task_slug** | `web_acquisition_subgraph` |
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
| **git_branch** | `task/web_acquisition_subgraph` |
| **worktree_root** | none（单仓工作目录；与对内子图双轨并行时是否开独立 worktree 由 00 派发时决定） |
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
| HG-AUDIT-R1 | approved | 30 | 20-task-audit R1 PASS · 人签 2026-09-09 会话 |

---

## 背景与目标

交付 LangGraph 编排下的**对外子图（Web Acquisition，「写入」轨）**：给定单个目标 URL，完成 Playwright 渲染抓取（CDP Turbo 加速）→ BeautifulSoup + CSS 语义推断的代码级解析（正文/价格/Meta，绑定 BoundingRect/XPath）→ 按 H1/H2 语义切分为 512–1024 tokens 的 `pre_chunks`（附 `section_path`/`xpath` 可溯源）→ 整页/视口截图落盘 → 轻量 Embedding 向量化，最终产出符合 PRD §6.2 的标准 Payload 转交对内子图。本轨落实铁律一（代码解析优先，截图仅留痕）与铁律二（性能左移：解析/切分/向量化全部下沉本轨）。

---

## 范围

- [ ] Playwright 渲染抓取单 URL 页面（主路径），配合 CDP 协议 Turbo 加速；抓取超时阈值可配置
- [ ] BeautifulSoup + CSS 语义推断提取正文、价格、标题、Meta 等字段，并为提取节点绑定 BoundingRect 坐标与 XPath
- [ ] 按 H1/H2 标题层级语义切分清洗后文本为 `pre_chunks`，每块 512–1024 tokens，每块附 `section_path`（父级标题路径）与 `xpath`
- [ ] 整页/视口截图落盘存储（仅留痕与人工复核，**不做任何像素级分析**），路径写入 Payload `screenshot_path`
- [ ] 调用轻量 Embedding 模型为每个 chunk 生成文本向量，随 Payload 一并转交对内
- [ ] 产出并校验符合 PRD §6.2 契约的标准 Payload（`url` / `screenshot_path` / `extracted_meta` / `pre_chunks[]`）
- [ ] 目标 URL 协议白名单校验（仅 http/https；拒绝 file:// 与内网地址段，SSRF 防护）
- [ ] 子图状态上报钩子：Fetching → Parsing 状态迁移事件供 Supervisor/SSE 消费

## 非范围

- 多模态/视觉大模型调用（铁律一 · 违反即返工）；像素级截图内容分析
- 多 URL 批量采集、任务历史（PRD §8.4/§9.2 · V2.0+）
- 动态反爬策略与代理池（PRD §9.1 · V2.0+；反爬失败按失败路径处理）
- Top-K 检索、结论生成、Tool Node 回填（对内子图职责，见 `./task_internal_rag_subgraph.md`）
- 前端页面与 SSE 端点（控制台职责，见 `./task_web_console_mvp.md`）
- 私有化模型部署（POC 期走外部 API）

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| 22 未签 `HG-AUDIT-R1` 即 30 改码 | 执行 Agent **拒开工** | 是 | 须先 22 + 人签 |
| 目标页抓取超时（Playwright 超时阈值内未完成渲染） | 标记 Fetching 失败，任务转终态 Error；保留已落盘的部分截图（若有）供复核 | 是（用户重新提交同一 URL；V1 不自动重试） | 页面提示「目标页面抓取超时，请稍后重试」+ 状态 Error |
| 目标站反爬拦截（403/验证码/重定向到验证页） | 检测响应状态码与验证页特征，终止管道，状态 Error；截图留痕 | 是（重试语义同超时；代理池属非范围，不承诺成功率） | 页面提示「目标站点拒绝访问（反爬拦截）」+ 状态码 |
| 代码级解析为空（DOM/CSS 提取无有效正文） | **不降级**调用多模态模型（铁律一）；以空 chunks 的 Payload 继续流转，由对内子图产出「信息不足」结论 JSON | 是（用户可换 URL 重试） | 切片区显示「未提取到有效内容」 |
| 非法目标 URL（非 http/https、file://、内网地址段） | 子图入口拒绝执行，任务转终态 Error，记录 SSRF 拦截日志 | 是（用户改正 URL 重新提交） | 页面提示「目标 URL 不被允许」 |
| Embedding 服务调用失败（外部 API 异常） | 对外子图标记失败，任务终态 Error；已产出的解析/切分中间结果保留日志可查 | 是（用户重新提交） | 页面提示「向量化失败，请稍后重试」+ 状态 Error |

---

## 验收标准

- [ ] 全量测试命令通过（本仓尚无 CI workflow；30 须随实现落盘 `pytest tests -q` 等效测试入口并使其通过，后续 CI 接入时与仓 workflow 对齐）
- [ ] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过（wiki_delta 预检 · 与 PR CI sample `run:` 行逐字一致）
- [ ] **契约测试**：对本地静态测试页（含 H1/H2/价格 DOM）跑完整管道，产出的 Payload 通过 PRD §6.2 JSON Schema 校验（`url`/`screenshot_path`/`extracted_meta`/`pre_chunks[]` 字段齐全）
- [ ] **切分断言**：每条 `pre_chunks` 块长 ∈ [512, 1024] tokens，且 `section_path` 与 `xpath` 字段非空
- [ ] **截图断言**：`screenshot_path` 指向的截图文件真实落盘可读，且 Payload 中路径可追溯（SPEC A6）
- [ ] **铁律一审计**：全流程日志 grep 无任何多模态/视觉模型调用记录（SPEC A6）
- [ ] **SSRF 用例**：`file://`、内网 IP 段（如 10.x/172.16.x/192.168.x/127.x）URL 被拒绝并落日志（SPEC R4 安全用例）
- [ ] **失败注入**：超时（慢响应桩）、反爬（403 桩）、空解析（空 body 桩）三条失败路径各一用例，断言状态终态 Error 与用户可见文案（SPEC R4-5）
- [ ] 状态迁移事件 Fetching → Parsing 可被 Supervisor 层观测（供 SSE 进度 10%→50% 映射）

---

## 给执行帽的必读列表

1. `AGENTS.md` · `docs/meta/PROJECT_CONFIG_*.md`（若存在）
2. 关联 SPEC：`docs/spec/SPEC-web-research-agent_v1.md`（已签收 · 范围第 1 条 / A2/A3/A6 / failure_paths）
3. PRD 真值：`docs/spec/_source/PRD_web_research_agent_v2.md` §4、§6.2、§1.2
4. 并行轨 task：`./task_internal_rag_subgraph.md`（Payload 契约消费方）、`./task_web_console_mvp.md`（Payload 展示方）
5. 工程底座 task：`./task_project_scaffold.md`（**前置依赖**：本 task 的 30 在 scaffold 交付的目录槽位与 stub 节点内填实现，不再动工程骨架）
6. `docs/standards/CODING_*_L2`（若仓内存在则必读；当前缺失时按仓通用编码约定执行）

---

## 思考轮（10-task 预置 · 30/22 可续填）

### R0 · 读人聊 / 业务目标

PRD §4 + SPEC 范围第 1 条：对外子图是「写入」轨与性能重灾区，承担铁律二下沉的全部 CPU/内存密集职责。完成态 = 单 URL 输入 → 标准 Payload（含向量与截图路径）产出，全程无多模态调用。双轨策略（PRD §2.2）下本轨不依赖内部大模型，可独立开发测试。

### R1 · 范围 / 非范围 / 角色与场景

范围锁定 PRD §4.1–4.5 五项职责 + SPEC 补充的 SSRF 白名单（SPEC R3 安全约束）。非范围显式排除批量、视觉分析、代理池，与 SPEC 非范围 1/2/4 双向锁定。边界钉死：截图「落盘+展示+复核」属范围，「截图内容分析」属非范围（铁律一）。角色上本轨无界面交互，消费者为 Supervisor 与对内子图。

### R2 · 方案对比（≥2 · 推荐 · 弃选）

**分叉：抓取主路径 —— Playwright 全量渲染 vs 静态 HTTP 抓取 + 渲染回退**

| 维度 | Playwright 渲染优先（推荐 · PRD §4.1 锁定） | 静态抓取优先 + 渲染回退 |
|------|----------------------------------------------|--------------------------|
| PRD 符合度 | §4.1 明文锁定 Playwright 优先 + CDP Turbo | 与 PRD 锁定冲突 |
| SPA/JS 重页面覆盖 | 全覆盖 | 静态抓取对 SPA 失效，回退路径增加复杂度 |
| 资源占用 | 较高（浏览器进程），但在对外轨符合铁律二左移 | 低，但省下的资源在错误的一轨 |
| BoundingRect 绑定 | 渲染后 DOM 天然可取坐标 | 静态 HTML 无布局信息，坐标不可得 |

**推荐 Playwright 渲染优先**：PRD 选型已锁定且 BoundingRect 需求（§4.2）只有渲染后 DOM 可满足。**弃选静态优先**：与 PRD §4.1 明文冲突且无法满足坐标绑定。

Embedding 模型具体选型（维度/中文能力）按 SPEC residual_risks 留待 30 实现期确定，约束：轻量、可离线或小模型 API、维度写入 Payload 契约注释。

### R3 · 边界 / 失败路径 / 安全与依赖

- **铁律一边界**：任何「解析为空 → 调多模态」的降级提案均为越界，处置固定为空 chunks 流转 + 对内「信息不足」结论（SPEC failure_paths 第三行）。
- **铁律二边界**：对内子图禁止重算 Embedding；本轨必须保证 Payload 内 `embedding` 字段就位。
- **安全**：SSRF 白名单（http/https only + 内网段拒绝）为本轨入口强制检查，已列入验收。
- **依赖**：LangGraph / Playwright（+CDP）/ BeautifulSoup / 轻量 Embedding 模型；LLM Key 不落盘明文（SPEC R3 建议项）。

### R4 · 验收标准 / 可测性 / test_strategy

`test_strategy: required`。可测性设计：本地静态测试页（含 H1/H2/价格 DOM）作为集成测试夹具，使块长区间、section_path/xpath、截图落盘三条断言完全离线可跑；契约测试以 PRD §6.2 JSON Schema 双向校验（本轨产出端）。失败注入用慢响应桩/403 桩/空 body 桩覆盖三条主失败路径。SPEC A2/A3/A6 的对外轨部分由本 task 验收承接；A1/A4/A5/A8 由控制台与对内 task 承接。

### R5 · 草稿就绪 · 移交判断

草稿就绪。范围/非范围/验收/failure_paths 全部可观测并可回溯 PRD §4/§6.2 与 SPEC 条目；R2 抓取路径分叉已给推荐与弃选；SSRF 安全约束落入验收。移交路径：HG-TASK-DRAFT 人扫 → 20-task-audit R1 → HG-AUDIT-R1 人签 → 30 开工。

### 思考轮控制

| 项 | 值 |
|----|-----|
| early_stop | no |
| reason | 默认 R0–R5 全轮预置；功能 Epic 不适用 bugfix 跳轮 |
| residual_risks | 1) Embedding 模型选型后置（影响块长口径与检索质量）；2) CDP Turbo 加速收益未量化，V1 接受基线 Playwright 性能；3) 反爬成功率无代理池兜底，依赖目标站宽松度 |

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| 30 实现 | ⏳ | |
| 40 自检 | ⏳ | |

---

## 测试策略（Harness）

**test_strategy**: `required`

- `required`：先可失败自动化测试再改实现（契约测试 + 静态页集成测试 + 失败注入先行）

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
| 2026-09-09 | 10-task bulk-split ×3 之一：对外子图初稿（依据 SPEC v1 signed + PRD §4/§6.2 + 审计 R1 无阻塞结论） |
