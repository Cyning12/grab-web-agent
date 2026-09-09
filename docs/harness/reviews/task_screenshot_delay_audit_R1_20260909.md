# 审查文：task_screenshot_delay · 20-task-audit R1

## 元信息

| 项 | 值 |
|----|-----|
| 审查对象 | `docs/tasks/active/task_screenshot_delay.md`（截图触发延迟加大与可配置） |
| 审查帽 | 20-task-audit · R1 |
| 审查日期 | 2026-09-09 |
| 对照真值 | `docs/tasks/done/task_fetch_render_wait_lite.md`（D7 口径）· `docs/spec/architecture/frontend_backend_breakdown_v1.md` §1.3/§5 D7 · `docs/harness/templates/TASK_TEMPLATE.md` · `app/services/acquisition/browser.py`（既有实现） |
| 机械闸 | `task lint --file` exit **0**（LINT: PASS）· `gate-check --task` exit **2**（HG-AUDIT-R1 pending → 拒 30，符合预期：本帽不签闸） |

## 结论摘要

- **内容审查：PASS**（零内容阻塞）。范围极小化成立、与 fetch 节点既有实现兼容、失败路径三行合理、验收可命令化且基线实测吻合、R0–R5 无空槽。
- **流程闸：HG-AUDIT-R1 = pending**（blocks 30）。本审查不构成签闸；须维护者在 task 人工闸表签 approved 后 30 方可开工。

## 逐要点核对

### 1. 范围极小化与非范围

- 范围四条均为**同一插点**的极小改动面：env `SCREENSHOT_DELAY_MS` 参数化（读取口径钉死与 `FETCH_RENDER_TIMEOUT_MS` 相同）+ `.env.example` 补录 + 单测 + 真机复跑。无第二改动点。✅
- 非范围明确排除：蒙层自动关闭/绕过（引 PRD §9.1）、渲染确认探针逻辑改动（复用既有门槛）、解析/切分/对内/控制台。与 D7 task 非范围口径一致，无溢出。✅

### 2. 与 fetch 节点既有实现兼容性（亲验 browser.py）

- 现行 `fetch()` 时序：`_wait_for_render`（L139 渲染确认）→ `_detect_slider_overlay` + `_content_probe_passed`（L145–158 探针裁决）→ `_save_screenshot`（L159）。**截图触发点本就在渲染探针之后**，故「延迟插点在探针通过之后」与既有实现天然兼容，单插点可达。✅
- 检出拆三（`_detect_hard_anti_bot` / `_detect_slider_overlay` / `_content_probe_passed`）三段均不受延迟插点影响。✅
- 失败路径三行核对：①闸拒开工行与 TEMPLATE 逐字口径一致；②非法 env 落默认 + warning 不中断——优于现行 `int(os.getenv(...))` 直接 ValueError 的行为，属明确定义的可测改进；③蒙层仍在走 D7 warning 继续——与架构 §5 D7「警告但继续」逐字对齐。✅

### 3. 验收可命令化与基线实测复核（本帽亲跑）

| 验收项 | 可命令化 | 本帽实测 |
|--------|----------|----------|
| `.venv/bin/python -m pytest tests -q` 全绿不回退 | ✅ | exit 0 · **120 passed, 2 skipped**（3.21s） |
| 基线 122 collected | ✅ | `pytest --collect-only -q` = **122 tests collected** —— 与 task 文「122 collected = 120 passed + 2 skipped」**逐数吻合** |
| `task lint-wiki-delta --target .` | ✅ | （验收行在案；R1 未代跑，30/40 闭环保留） |
| 延迟单测 / env 断言 / 真机复跑 | ✅ 均为可执行断言形态 | — |

### 4. 思考轮与元信息

- R0–R5 全部填实无空槽；思考轮控制表 `early_stop=no` + reason + residual_risks 两条（①延迟只能改善不能根除蒙层——与 D7 task 残余风险①实锤呼应；②耗时拉长由 PRD §3.1 异步 SSE 承受）闭合。✅
- 元信息无占位：`test_strategy_note` / `freeze_id` / `related_pr` 的「（非 not_applicable）/（无）」写法与 done 的 D7 task 同口径，非占位符。✅
- `close_pr_policy=exempt` + exempt_note 引「V1 仅本地运行、无 PR 流（人决 D3）」——与架构 §5 D3 决策记录一致，exempt 成立。✅
- `required_invoke_hats=10,30,40` 不含 20 → 本帽无需落 invoke 快照（仅 reviews 落盘，符合 K 澄清）。✅
- `chain_prompt` 引用 `30-execute-code.md` / `40-self-check.md` 两文件均存在；HG-TASK-DRAFT 代签授权文件 `docs/harness/AUTHORIZATION_00_signoff_20260909.md` 在案。✅

## 非阻塞观察项（交 30 注意，不退回）

1. **延迟须条件化施加**：现行 `_save_screenshot` 在 `anti_bot=True` 路径（探针不过 / 硬反爬 403·title 特征）同样会执行（SPEC FP-2 反爬截图留痕）。task 失败路径「探针不过仍 ANTI_BOT，不空等」要求延迟只在非 anti_bot 分支生效；30 实现时延迟应为条件式（如 `if not anti_bot`），而非无条件插在 `_save_screenshot` 之前。硬反爬路径是否延迟 task 未显式钉，按「不过不空等」精神应同样跳过——验收单测「探针不过时无延迟空等」已可机械卡住此语义。
2. **K7 旧测 grep 影响面（checklist 提醒 · 非机械闸）**：本 task 为新增时序参数而非改默认值/校验/策略门/fallback 语义，且本帽实测 `tests/` 中 `wait_for_timeout` 仅出现于 FakePage mock 定义（test_acquisition_browser.py L100–101），**零断言依赖其调用次数/序列**，影响面实测为零，故未强制要求补列 grep 影响面验收项。提醒 30：新增延迟断言时勿引入对 `calls` 完整序列的脆弱相等断言。

## 回填清单

无（零阻塞）。

## 维护者签闸（20 后 · 30 前）

- [ ] 已读 R1 审查结论
- [ ] 在 task 人工闸表将 HG-AUDIT-R1 改为 approved（维护者 · 日期）
- [ ] commit task 文档或确认已签
- [ ] 再下发 Harness 30 Prompt

30 Agent 将以 task 表为准；pending 时必须拒开工（见 TEMPLATE_30_gate_stop.md）。

---

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R1：内容 PASS · HG-AUDIT-R1 仍 pending · 机械闸 lint exit 0 / gate-check exit 2（pending 拒 30，符合预期）· 基线 122=120+2 亲测吻合 · 非阻塞观察项 2 条 |
