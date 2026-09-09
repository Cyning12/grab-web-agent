# Task：截图触发延迟加大与可配置（screenshot_delay）

> **状态**：`done`  
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

- [x] 截图节点（或 fetch 截图触发点）前增加**可配置延迟**：env `SCREENSHOT_DELAY_MS`（默认值建议 3000–5000ms，30 实测定推荐默认），读取方式与 `FETCH_RENDER_TIMEOUT_MS` 同口径（模块内 os.getenv + 默认值）—— 00 复核通过
- [x] 延迟插点须位于**渲染确认探针通过之后**（探针不过仍 ANTI_BOT，不空等）—— 00 复核通过
- [x] `.env.example` 补录 `SCREENSHOT_DELAY_MS` 行（注释说明语义与推荐值）—— 00 复核通过
- [x] 单测：mock 场景断言延迟被调用且时长取自 env；探针不过时**不发生**延迟空等—— 00 复核通过
- [x] 真机复跑留痕：concept/sz000858 全管道，截图路径 + 工单号 + SSE 流写入实现备忘；00 人工看图复核蒙层改善—— 00 **人工看图复核**：shot_8b1b8439f2_1788961145303.png（2.1MB）主体全渲染、稳定可判读，顶部仅余小弹窗（D7 允许）；vs 基线 18KB 近空白图显著改善；工单 MOCK-805D21EE

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

- [x] 全量测试命令通过（`.venv/bin/python -m pytest tests -q` 全绿，基线 122 collected = 120 passed + 2 skipped 不回退）—— 00 复核：合并后 main = **127 passed, 2 skipped**（基线 122 不回退，净增 7）
- [x] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过—— 00 复核：PASS
- [x] **延迟单测**：mock 断言截图前延迟被调用、时长取自 env；非法值落默认；探针不过时无延迟空等—— 00 复核：TestScreenshotDelay ×7（env 取值/非法落默认/anti_bot 不空等）随全量通过
- [x] **env 断言**：`.env.example` 含 `SCREENSHOT_DELAY_MS` 且带注释—— 00 复核：.env.example 含 SCREENSHOT_DELAY_MS=5000 带注释
- [x] **真机复跑**：concept/sz000858 跑通 Pending→…→Done，工单号非空；截图供 00 人工看图（蒙层改善或稳定可判读）—— 00 **人工看图复核**：shot_8b1b8439f2_1788961145303.png（2.1MB）主体全渲染、稳定可判读，顶部仅余小弹窗（D7 允许）；vs 基线 18KB 近空白图显著改善；工单 MOCK-805D21EE

---

## 给执行帽的必读列表

1. `docs/tasks/done/task_fetch_render_wait_lite.md`（D7 口径与渲染确认实现）
2. `docs/spec/architecture/frontend_backend_breakdown_v1.md` §1.3（fetch 三行式）· §5 D7
3. 用户反馈（会话留痕）：截图仍含蒙层，加大延迟触发

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| 延迟插点与默认值的实测依据 | ✅ | 插点位于渲染确认探针裁决之后、`_save_screenshot` 之前，仅 `not anti_bot` 路径生效（anti_bot=True 终态页仅截图留痕不空等 · 20 审观察项②）；读取与 FETCH_RENDER_TIMEOUT_MS 同口径（`__init__` 内 os.getenv + 默认值，非法值落默认 + warning）。默认值定 **5000ms**：真机复跑（env 未设走默认）截图全页渲染完整、页面主体稳定可判读；取区间上限因东财对本机持续下发滑块（R5 residual ①：延迟只改善不根除蒙层），async SSE 模式可承受时长增加（residual ②）。 |
| 真机复跑结果 | ✅ | 2026-09-09 端口 8011（NO_PROXY/no_proxy 大小写双写）；task_id=`36044d85862a4874b36a0e9e2ec11626`；SSE：Pending→Fetching(10%)→warning PAGE_CAPTCHA_OVERLAY→Parsing(50%)→chunk×15→RAGing→conclusion+receipt→100%→**Done**；工单号 `MOCK-805D21EE`；截图 `app/static/shot_8b1b8439f2_1788961145303.png`（2.1MB 全页：K线/股吧/页脚均清晰，顶部仅余小型滑块弹窗，对比基线旧截图 18KB 近空白——蒙层覆盖情况显著改善，供 00 人工看图复核）。 |

---

## 测试策略（Harness）

**test_strategy**: `required` —— mock 延迟断言先行，真机复跑为人工可见验收。

---

### 自检结论（执行者）

**验证命令**（worktree `.worktrees/shot`，Python `.venv/bin/python`）：

| 命令 | 退出码 | 关键输出 |
|------|--------|----------|
| `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_screenshot_delay.md` | 0 | `VERIFY: PASS`（HG-TASK-DRAFT/HG-AUDIT-R1 均 approved） |
| `.venv/bin/python -m pytest tests -q`（改前基线） | 0 | 120 passed, 2 skipped（122 collected） |
| `.venv/bin/python -m pytest tests -q`（改后全量） | 0 | **127 passed, 2 skipped**（+7 新延迟单测，基线不回退） |
| `npx --yes dsh-coding-kit task lint-wiki-delta --target .` | 0 | `LINT-WIKI-DELTA: PASS`（issues: 0） |
| 真机：`uvicorn app.api.main:app --port 8011`（NO_PROXY 大小写双写）+ POST /api/task + SSE 流 | 0 | Pending→…→Done · 工单 MOCK-805D21EE · 截图 `app/static/shot_8b1b8439f2_1788961145303.png` |

**验收逐条**（勾选框由 00/维护者签，此处仅证据）：

1. 全量测试通过：✅ 127 passed + 2 skipped，基线 122 不回退。
2. lint-wiki-delta：✅ PASS。
3. 延迟单测：✅ `TestScreenshotDelay` 7 条——env 取值断言（wait_for_timeout==[settle, env 值] 且先于 screenshot）、非法值（非数字/负数）落默认 + warning、anti_bot 路径（探针不过 + 硬反爬 403）无延迟空等（wait_for_timeout 仅 settle 一次）、D7 降级警告路径同样延迟。
4. env 断言：✅ `.env.example` 含 `SCREENSHOT_DELAY_MS=5000` + 语义/推荐值注释。
5. 真机复跑：✅ 全管道 Done，工单号非空，截图落 `app/static/` 供 00 看图（蒙层改善：全页渲染完整，顶部仅余小滑块弹窗）。

**已知未测项**：不同延迟值（3000/4000）的蒙层改善梯度未逐档对比（R5 裁定取区间上限一档实测）；50 独立复检未做（本帽不越界）。

---

### KPI（00）

Task_KPI%: 100

| 维度 | 评分 | 依据 |
|------|------|------|
| D1 闸完整性 | 5/5 | 双闸 00 代签（授权在案）· R1 PASS · verify PASS |
| D2 验收覆盖 | 5/5 | 验收 5 项全勾；真机行经 00 人工看图复核（2.1MB 全渲染 vs 基线 18KB 近空白，显著改善） |
| D3 过程留痕 | 5/5 | invoke 10/30+40 齐；真机截图 + 工单 MOCK-805D21EE 留档 |
| D4 范围纪律 | 5/5 | 5 文件 +184/-3 极小 diff；20 审观察项（条件化延迟）落实为强制 |
| D5 测试制品 | 5/5 | 净增 7 用例零回退（127 passed） |

---

### 经验总结

（已回填 · 2026-09-09 CLOSE）
- 截图时机是「探针通过」≠「视觉稳定」：探针保证 DOM 非占位，但异步图片/弹窗需要时间稳定——5s 延迟（区间上限）实测把 18KB 近空白截图改善为 2.1MB 全渲染图。时序类参数必须 env 可配，站点差异大。
- 「条件化延迟」（anti_bot 路径不空等）来自 20 审观察项升级为强制——失败路径的每一秒空等都是用户可感知的成本，审查观察项值得当阻塞级对待。
- 蒙层只能改善不能根除（站点侧持续反爬），D7 警告横幅 + 人工可复核是 V1 的诚实终态；根除属 V2 代理池（PRD §9.1）。

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
