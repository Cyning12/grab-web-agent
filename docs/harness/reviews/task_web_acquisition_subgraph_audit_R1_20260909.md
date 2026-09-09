# 审查文 · task_web_acquisition_subgraph R1（20-task-audit）

| 项 | 值 |
|----|-----|
| **审查对象** | `docs/tasks/active/task_web_acquisition_subgraph.md` |
| **task_slug** | `web_acquisition_subgraph` |
| **审查轮次** | R1 |
| **审查日期** | 2026-09-09 |
| **审查帽** | 20-task-audit（skill 已加载并遵守「只做/禁止」） |
| **对照真值** | `docs/spec/SPEC-web-research-agent_v1.md`（signed）+ `docs/spec/_source/PRD_web_research_agent_v2.md` |
| **结构真值** | `docs/harness/templates/TASK_TEMPLATE.md` |
| **前置闸** | HG-TASK-DRAFT = approved（人签 2026-09-09 会话）✅ |

---

## 结论摘要

- **内容审查：PASS** —— 范围/非范围/验收/failure_paths/思考轮全部零内容阻塞。
- **流程闸：HG-AUDIT-R1 = pending** —— 须维护者签 task 表后方可下发 30（见文末签闸清单）。
- **总结论：PASS（建议人签 HG-AUDIT-R1）**。

## 机械闸复核（实测）

| 命令 | 结果 | exit code |
|------|------|-----------|
| `npx --yes dsh-coding-kit@1.10.0 task lint --file docs/tasks/active/task_web_acquisition_subgraph.md` | `LINT: PASS` | **0** |
| `npx --yes dsh-coding-kit@1.10.0 gate-check --task docs/tasks/active/task_web_acquisition_subgraph.md` | HG-TASK-DRAFT=approved；HG-AUDIT-R1=pending → 拒 30 | **2**（预期：流程闸未签，非内容缺陷） |

## 核对项明细

### 1. SPEC 边界一致性 ✅
- 范围 8 项全部落在 SPEC 范围第 1 条（对外子图五项职责）+ 第 4 条（状态机 Fetching→Parsing 上报，对应 PRD §6.3）+ SPEC R3 安全建议（SSRF 白名单，SPEC 建议 task 阶段约束，本 task 已落实为强制入口检查并入验收）。
- 非范围与 SPEC 非范围 1/2/4/6 双向锁定；Top-K/结论生成/Tool Node 归对内（SPEC 范围第 2 条）、前端与 SSE 归控制台（SPEC 范围第 3 条），无越界、无灰色重叠。
- 铁律一边界（截图「落盘+展示+复核」∈范围 /「像素级分析」∈非范围）与 SPEC R1/A6 一致。

### 2. 验收可回溯 A1–A9 ✅（附 1 条非阻塞观察）
- task 验收 9 项均可勾选、可观测：契约测试（PRD §6.2）、切分断言（A3）、截图断言+铁律一审计（A6/A2 对外部分）、SSRF 用例（SPEC R3/R4-7）、失败注入三条（SPEC R4-5，承接 A9 对外部分）、状态迁移观测（SPEC 范围 4 / A1 对外部分）。
- R4 分工句明确「A2/A3/A6 对外部分本 task 承接；A1/A4/A5/A8 由控制台与对内 task 承接」，与三 task 拆分一致。
- **非阻塞观察 O1**：分工枚举未提 A7（2核4G 资源上限，逻辑上属对内 task）与 A9（本 task 失败注入已部分承接）；建议 00 在 internal_rag_subgraph 审查中确认 A7 归属闭环。

### 3. failure_paths 四列 ✅
- 6 行全部四列（触发→行为→可重试→用户可见）齐备。超时/反爬/解析为空三行与 SPEC failure_paths 逐行一致（含「解析为空不降级多模态」铁律一处置）；新增 SSRF 拒绝、Embedding 失败两行为对外职责自然延伸，与 SPEC 不矛盾；首行为模板默认流程闸行（拒开工）。

### 4. 思考轮 R0 + R1–R5 ✅
- 六轮全部填实无空槽；R2 方案对比（Playwright 渲染优先 vs 静态抓取+渲染回退）含推荐与弃选理由且与 PRD §4.1 锁定一致；控制表 early_stop=no、reason 合法（功能 Epic 不适用 bugfix 跳轮）、residual_risks 三条具体（Embedding 选型后置 / CDP Turbo 收益未量化 / 反爬无兜底）。

### 5. Harness 元信息 ✅（附 1 条非阻塞观察）
- 必填字段无占位；`graph_delta=none`、`wiki_delta=none` 均有 note 理由；`invoke_retention_profile=default` 已选定；`semi_auto=false`；`required_invoke_hats=10,30,40`（不含 20，本轮无需 invoke 快照落盘）。
- **非阻塞观察 O2**：`chain_prompt` 指向 `docs/harness/prompts/PROMPT_cursor_task_chain_serial_v1.md`，该文件本仓**尚不存在**；task 已注明「00 派发 30 前补齐或改用等效链 Prompt」。不阻塞本审查，但为 30 派发前置条件（00 职责）。

### 6. 依赖相对路径真实存在 ✅
- `./task_internal_rag_subgraph.md` ✅、`./task_web_console_mvp.md` ✅、SPEC ✅、PRD ✅ 均真实存在；`AGENTS.md`/`docs/meta/`/`docs/standards/` 当前缺失但 task 已标注「若存在」，豁免合理。

### 7. 双轨 Mock 解耦与 PRD §6.2 契约 ✅
- R0 声明「双轨策略（PRD §2.2）下本轨不依赖内部大模型，可独立开发测试」，与 PRD §2.2 一致；范围末项与契约测试验收锁定 PRD §6.2 四字段（`url`/`screenshot_path`/`extracted_meta`/`pre_chunks[]`）；pre_chunks 的 `title`/`text`/`embedding`/`xpath` + §4.3 的 `section_path` 均在范围与验收体现（对契约为增强，不冲突）。

### 行为变更类 checklist（K7）
- 本 task 为绿地新建（仓内无既有实现/旧测），非行为变更类，「旧测 grep 影响面」项不适用。

## 非阻塞观察汇总（不退回 · 供 00/维护者知悉）

| # | 观察 | 处置建议 |
|---|------|----------|
| O1 | R4 分工枚举未提 A7/A9 归属 | 00 在 internal task 审查确认 A7 承接 |
| O2 | chain_prompt 目标文件本仓不存在 | 00 派发 30 前补齐或改用等效链 Prompt |
| O3 | 失败注入验收断言「用户可见文案」在纯后端子图内的断言对象需明确（建议断言错误消息字段/状态载体而非前端渲染） | 30 实现期明确即可 |

## 阻塞项

无。

## 维护者签闸（20 后 · 30 前）

- [ ] 已读 R1 审查结论
- [ ] 在 task 人工闸表将 HG-AUDIT-R1 改为 approved（维护者 · 日期）
- [ ] commit task 文档或确认已签
- [ ] 再下发 Harness 30 Prompt（下发前先解决 O2：补齐 chain_prompt 或指定等效链 Prompt）

30 Agent 将以 task 表为准；pending 时必须拒开工（见 TEMPLATE_30_gate_stop.md）。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R1：内容 PASS（零阻塞 · 3 条非阻塞观察）；机械闸 lint exit 0 / gate-check exit 2（预期）；建议人签 HG-AUDIT-R1 |
