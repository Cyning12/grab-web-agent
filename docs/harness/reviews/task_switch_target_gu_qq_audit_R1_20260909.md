# 审查文：task_switch_target_gu_qq · R1（20-task-audit）

> **审查帽**：20-task-audit（HG-AUDIT-R1 人签前的书面审）
> **对象**：`docs/tasks/active/task_switch_target_gu_qq.md`（draft · 00 起草 2026-09-09）
> **审查日期**：2026-09-09
> **对照真值**：`docs/spec/web-research-agent/SPEC-web-research-agent_v1.md`（signed）· `docs/spec/architecture/frontend_backend_breakdown_v1.md` §1.3/§5 · `docs/tasks/done/task_fetch_render_wait_lite.md` · `docs/harness/templates/TASK_TEMPLATE.md`

---

## 结论摘要

| 维度 | 结论 |
|------|------|
| **内容**（范围/非范围/验收/failure_paths/思考轮） | **PASS · 零内容阻塞** |
| **流程闸** HG-AUDIT-R1 | **pending**（须维护者签 task 表后方可 30 开工） |

**总体结论：PASS（R1 书面审通过）。** 内容面六项审查要点全部成立；流程闸 HG-AUDIT-R1 仍为 pending，30 不得开工，待维护者签闸。

---

## 逐项核对

### 1. 范围边界 ✅

- 范围五行：默认 URL 切换（.env.example/README + 架构 §5 增 D8 决策行）· 腾讯页全管道实测与最小解析适配 · HTML fixture + 解析/切分用例 · 双股票真机验收 · 旧测影响面（K7）。
- 非范围三行显式排除：东财兼容维护、**任何反爬绕过手段**、对内子图/控制台改动；价格字段不硬猜（铁律一）。与派发口径「不碰对内/控制台/反爬绕过」一致。
- **观察项（非阻塞）**：范围第 2 行适配边界写「限 parser.py 选择器/语义规则增补；**chunker 仅在切分明显不合法时动**」，略宽于派发口径「限 parser.py」。task 自设边界清晰、且 chunker 属对外子图不违 SPEC；建议 30 若确需动 chunker，须在实现备忘与用例中留痕说明「明显不合法」的判定实例。

### 2. 验收可命令化 + 基线口径（20 亲测复核）✅

- 验收六行全部可命令化/可观测：pytest 全量 · lint-wiki-delta · fixture 断言 · grep 处置 · 双股票真机闭环（一票否决级）· 默认 URL 断言。
- **基线实测复核（本审查亲跑，仓根）**：
  - `.venv/bin/python -m pytest tests --collect-only -q` → exit 0 · **129 tests collected**
  - `.venv/bin/python -m pytest tests -q` → exit 0 · **127 passed, 2 skipped**
  - task 验收行口径「129 collected = 127 passed + 2 skipped」**与实测完全吻合**，基线可信。

### 3. K7 旧测影响面行实质性 ✅

- 范围第 5 行与验收第 4 行均含旧测 grep 影响面项（行为变更类 task 必备，K7 checklist 满足）。
- **grep 实测复核（本审查亲跑）**：`grep -rn "eastmoney" tests/` = **9 文件 26 处**命中；其中 `quote.eastmoney.com` URL 字面量 **20 处**（test_acquisition_pipeline 7 · test_acquisition_browser 3 · test_web_console_api 2 · test_web_console_sse 1 · test_acquisition_url 2 · internal_rag_fakes 1 · test_internal_rag_contract 1 · test_internal_rag_graph 1 · test_internal_rag_live 1；另 6 处为注释/字符串语义引用）。
- **非阻塞建议**：task 未像前作 task_fetch_render_wait_lite 那样预填实测命中数基线；建议 30 开工第一条命令即跑 grep 并逐条标注处置（保留作失败注入/白名单/fixture 语义的保留，作默认目标的改腾讯），可参照本审查实测数 9 文件 26 处核对。

### 4. 与 D7 / 铁律一不冲突 ✅

- 非范围第 3 行：「腾讯页若同样异步渲染致占位，如实 insufficient_info，不硬猜——铁律一」；失败路径第 2 行：「解析为空 → 空 chunks 流转，对内产出信息不足结论（铁律一不降级）」——与 SPEC FP-3 及架构 §4 铁律一执行位置（n3 出口/m3 入口）逐字对齐。
- 失败路径第 3 行「腾讯后续上线反爬 → 按既有 ANTI_BOT/超时路径落终态」与 SPEC FP-1/FP-2 及架构 §1.3 n2 一致；未引入 D7 警告语义之外的新放宽，未承诺绕过。
- 完成态要求「截图无蒙层」属验收标准（达不到走既有失败路径），不构成对 D7 语义的改写。无冲突。

### 5. R0–R5 与控制表 / 元信息 / 机械闸 ✅

- **R0–R5 无空槽**：R0 用户原话在案 · R1 范围 · R2 三方案对比（A 推荐 / B 弃代理池 V2 范畴 / C 弃双站并行，弃选理由成立）· R3 边界（铁律一 + 反爬既有路径 + 适配限选择器层）· R4 验收 · R5 就绪。
- **思考轮控制表**：early_stop=no · reason 填实 · residual_risks 三条（适配工作量未知 / 腾讯未来反爬 / 价格异步占位）均实质。无裁量跳轮，符合模板。
- **元信息无占位**：全字段有值；freeze_id（无）/ related_pr（无 · D3）/ close_pr_policy=exempt 附 D3 理由，合规。graph_delta/wiki_delta=none 均附理由。人工闸表双行齐全（HG-TASK-DRAFT=approved 00 代签在案 · HG-AUDIT-R1=pending）。
- **机械闸（本审查亲跑）**：
  - `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.11.0 task lint --file docs/tasks/active/task_switch_target_gu_qq.md` → **exit 0 · LINT: PASS**
  - `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.11.0 gate-check --task docs/tasks/active/task_switch_target_gu_qq.md` → **exit 2（BLOCKED）**：HG-AUDIT-R1 pending 拒 30 —— 属审前预期的 failClosed 正确行为，非 task 缺陷。
- invoke 快照：required_invoke_hats=`10,30,40` 不含 20，按 V2 规则 20 invoke 快照非强制（reviews 硬闸分工），不落。

### 6. 审查纪律自守 ✅

- 本轮未改 task 任何实质内容；未代签任何人工闸；30 开工授权不由本审查签发。

---

## 阻塞项

**内容阻塞：零。**
**流程阻塞：HG-AUDIT-R1 = pending**（须维护者在 task 人工闸表签 approved）。

## 非阻塞建议（2 条，不挡签闸）

1. 30 开工首条命令跑 `grep -rn "eastmoney" tests/` 逐条标注处置（本审查实测 9 文件 26 处可参照）。
2. 若实测确需动 chunker，实现备忘须留「切分明显不合法」的判定实例。

---

## 维护者签闸（20 后 · 30 前）

```text
- [ ] 已读 R1 审查结论（PASS · 零内容阻塞 · 2 条非阻塞建议）
- [ ] 在 task 人工闸表将 HG-AUDIT-R1 改为 approved（维护者 · 日期）
- [ ] commit task 文档或确认已签
- [ ] 再下发 Harness 30 Prompt

30 Agent 将以 task 表为准；pending 时必须拒开工（见 TEMPLATE_30_gate_stop.md）。
```

（HG-AUDIT-R1 approved 后方可附 30 Prompt；本审查不签发。）

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R1：内容 PASS 零阻塞；pytest 基线 129=127+2 实测吻合；grep 实测 9 文件 26 处；lint exit 0 / gate-check exit 2（预期）；HG-AUDIT-R1 待维护者签 |
