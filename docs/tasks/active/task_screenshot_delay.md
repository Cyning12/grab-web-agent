# Task：截图触发延迟加大与可配置（screenshot_delay）

> **状态**：`draft`  
> **关联图谱**：无  
> **落盘**：`docs/tasks/active/task_screenshot_delay.md`；验收后 `git mv` → `docs/tasks/done/`

---

## Harness 元信息

| 字段 | 值 |
|------|-----|
| **task_slug** | `screenshot_delay` |
| **test_strategy** | `required` |
| **test_strategy_note** | （非 not_applicable） |
| **code_quality_bar** | `recommended` |
| **freeze_id** | （无） |
| **orchestration** | `MANIFEST 仅` |
| **chain_prompt** | `docs/harness/prompts/30-execute-code.md` + `docs/harness/prompts/40-self-check.md`（等效链） |
| **semi_auto** | `false` |
| **audit_profile** | `full` |
| **invoke_retention_profile** | `default` |
| **required_invoke_hats** | `10,30,40` |
| **git_branch** | `task/screenshot_delay` |
| **worktree_root** | `.worktrees/shot`（00 建） |
| **graph_delta** | `none` |
| **graph_delta_note** | 节点内时序参数调整，无图结构变化 |
| **wiki_delta** | `none` |
| **wiki_delta_note** | 参数化小改，经验入 task 经验总结即可 |
| **wiki_promotion** | `none` |
| **related_pr** | （无 · D3） |
| **close_pr_policy** | `exempt` |
| **close_pr_exempt_note** | V1 仅本地运行、无 PR 流（人决 D3） |
| **experience_capture** | `recommended` |
| **experience_capture_note** | （非 not_applicable） |
| **kpi_rubric** | `KPI_RUBRIC_v1_2` |
| **kpi_aggregator** | `CLOSE` |

### 人工闸

| human_gate_id | status | blocks_hats | 说明 |
|---------------|--------|-------------|------|
| HG-TASK-DRAFT | approved | 22-R1, 30 | 00 代签 2026-09-09（授权在案） |
| HG-AUDIT-R1 | approved | 30 | 20-task-audit R1 PASS · 00 代签 2026-09-09（授权在案） |

---

## 背景与目标

用户真机复核（2026-09-09）：极速版页面截图仍含验证蒙层/内容未完全稳定。人决：**截图触发前加大延迟**（且可配置），让页面渲染与蒙层稳定期更充分。完成态 = 真机复跑 concept/sz000858，截图在延迟后触发，蒙层覆盖情况改善或至少稳定可判读，A5 闭环不受影响。

---

## 范围

- [ ] 截图节点（或 fetch 截图触发点）前增加**可配置延迟**：env `SCREENSHOT_DELAY_MS`（默认值建议 3000–5000ms，30 实测定推荐默认），读取方式与 `FETCH_RENDER_TIMEOUT_MS` 同口径（模块内 os.getenv + 默认值）
- [ ] 延迟插点须位于**渲染确认探针通过之后**（探针不过仍 ANTI_BOT，不空等）
- [ ] `.env.example` 补录 `SCREENSHOT_DELAY_MS` 行（注释说明语义与推荐值）
- [ ] 单测：mock 场景断言延迟被调用且时长取自 env；探针不过时**不发生**延迟空等
- [ ] 真机复跑留痕：concept/sz000858 全管道，截图路径 + 工单号 + SSE 流写入实现备忘；00 人工看图复核蒙层改善

## 非范围

- 蒙层自动关闭/绕过（V2 反爬，PRD §9.1）
- 渲染确认探针逻辑改动（复用既有门槛）
- 解析/切分/对内/控制台改动

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| 22 未签 `HG-AUDIT-R1` 即 30 改码 | 执行 Agent **拒开工** | 是 | 须先 22 + 签 |
| `SCREENSHOT_DELAY_MS` 非法值（非数字/负数） | 落默认值并记 warning 日志，不中断 | 是 | 无感知 |
| 延迟后蒙层仍在 | 按 D7 口径 warning 继续（既有逻辑），结论标注不变 | 是 | 横幅提示不变 |

---

## 验收标准

- [ ] 全量测试命令通过（`.venv/bin/python -m pytest tests -q` 全绿，基线 122 collected = 120 passed + 2 skipped 不回退）
- [ ] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过
- [ ] **延迟单测**：mock 断言截图前延迟被调用、时长取自 env；非法值落默认；探针不过时无延迟空等
- [ ] **env 断言**：`.env.example` 含 `SCREENSHOT_DELAY_MS` 且带注释
- [ ] **真机复跑**：concept/sz000858 跑通 Pending→…→Done，工单号非空；截图供 00 人工看图（蒙层改善或稳定可判读）

---

## 给执行帽的必读列表

1. `docs/tasks/done/task_fetch_render_wait_lite.md`（D7 口径与渲染确认实现）
2. `docs/spec/architecture/frontend_backend_breakdown_v1.md` §1.3（fetch 三行式）· §5 D7
3. 用户反馈（会话留痕）：截图仍含蒙层，加大延迟触发

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| 延迟插点与默认值的实测依据 | ⏳ | |
| 真机复跑结果 | ⏳ | |

---

## 测试策略（Harness）

**test_strategy**: `required` —— mock 延迟断言先行，真机复跑为人工可见验收。

---

### 自检结论（执行者）

（30/40 回填）

---

### KPI（00）

（`kpi_aggregator: CLOSE` · 关账回溯填写）

---

### 经验总结

（`experience_capture: recommended` · 关账时建议回填）

---

## 思考轮（00 起草预置）

### R0 · 读人聊
用户：截图仍含蒙层，加大延迟触发。

### R1 · 范围
仅截图触发时序参数化 + env 补录 + 真机复跑；其余不动。

### R2 · 方案对比
- 方案 A（推荐）：探针通过后固定可配延迟再截图 —— 简单可测。
- 方案 B（弃）：轮询蒙层消失再截图 —— 蒙层可能永不消失（东财对本机持续下发），轮询会拖死任务。
- 方案 C（弃）：降低默认延迟保持原样 —— 不解决用户反馈。

### R3 · 边界
延迟在探针通过后才发生（不过不空等）；延迟不改 D7 警告语义；非法 env 落默认不中断。

### R4 · 验收
mock 延迟断言 + env 断言 + 真机看图。

### R5 · 就绪
改动面极小（单插点 + env + 单测），一轮 30 闭环。

### 思考轮控制

| 项 | 值 |
|----|-----|
| early_stop | no |
| reason | 默认全轮执行（00 起草一轮填实） |
| residual_risks | ① 延迟只能改善不能根除蒙层（站点侧反爬）；② 延迟加大拉长单任务耗时（PRD §3.1 异步 SSE 模式可承受） |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 00 起草初版（用户真机反馈：截图蒙层 · 人决加大延迟触发） |
