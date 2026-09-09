# Task：抓取渲染确认与极速版目标页切换（fetch_render_wait_lite）

> **状态**：`draft`  
> **关联图谱**：无（本仓尚无 `docs/_tech_graph/` flow 真值）  
> **落盘**：`docs/tasks/active/task_fetch_render_wait_lite.md`；验收后 `git mv` → `docs/tasks/done/`

---

## Harness 元信息

| 字段 | 值 |
|------|-----|
| **task_slug** | `fetch_render_wait_lite` |
| **test_strategy** | `required` |
| **test_strategy_note** | （非 not_applicable，无需填写） |
| **code_quality_bar** | `recommended` |
| **freeze_id** | （无） |
| **orchestration** | `MANIFEST 仅` |
| **chain_prompt** | `docs/harness/prompts/30-execute-code.md` + `docs/harness/prompts/40-self-check.md`（等效链 · 与既有 task 同口径） |
| **semi_auto** | `false` |
| **audit_profile** | `full` |
| **invoke_retention_profile** | `default` |
| **required_invoke_hats** | `10,30,40` |
| **git_branch** | `task/fetch_render_wait_lite` |
| **worktree_root** | `.worktrees/fetch`（单轨改进 · 由 00 建） |
| **graph_delta** | `none` |
| **graph_delta_note** | 本仓未建 tech graph 真值；改动为节点内行为增强，无图结构变化 |
| **wiki_delta** | `none` |
| **wiki_delta_note** | 改进属既有铁律一/失败路径的落地强化，无新知识沉淀必要（经验总结仍回填 task） |
| **wiki_promotion** | `none` |
| **related_pr** | （无 · V1 仅本地运行，人决 D3） |
| **close_pr_policy** | `exempt` |
| **close_pr_exempt_note** | V1 仅本地运行、无 PR 流（人决 D3 · 2026-09-09） |
| **experience_capture** | `recommended` |
| **experience_capture_note** | （非 not_applicable，无需填写） |
| **kpi_rubric** | `KPI_RUBRIC_v1_2` |
| **kpi_aggregator** | `CLOSE` |

### 人工闸

| human_gate_id | status | blocks_hats | 说明 |
|---------------|--------|-------------|------|
| HG-TASK-DRAFT | approved | 22-R1, 30 | 00 代签 2026-09-09（授权：AUTHORIZATION_00_signoff_20260909.md） |
| HG-AUDIT-R1 | approved | 30 | 20-task-audit **R4（D7 口径）** PASS · 00 代签 2026-09-09（授权在案 · 闸效力自 R2 延续至 R4 确认） |

---

## 背景与目标

真机验收（2026-09-09 用户截图留证）发现：东财标准个股页 `quote.eastmoney.com/sz000858.html` 触发**滑块验证覆盖层**（「拖动下方滑块完成拼图」软反爬），且大量字段（价格/盘口/K线）为 JS 异步渲染，**页面未渲染完成即进入解析**，导致截图留痕含验证覆盖层、文本字段多为「-」占位。人决：①默认目标切换为**极速版**链接 `https://quote.eastmoney.com/concept/sz000858.html`（干扰少）；②fetch 节点必须**确认页面真实渲染完成**后再放行解析。完成态 = 真机跑 concept 版 URL，截图无滑块覆盖、切片含真实行情文本、A5 闭环工单号依旧产出。

---

## 范围

- [ ] fetch_page 节点增加**渲染完成确认**：`wait_for_load_state`（networkidle 优先，domcontentloaded 兜底）+ 关键内容选择器/非占位文本等待（超时阈值 env 可配，如 `FETCH_RENDER_TIMEOUT_MS`），确认通过才交 parse_dom
- [ ] **滑块/验证码覆盖层检测**：识别「拖动下方滑块完成拼图」等东财验证特征 → 走 ANTI_BOT 失败路径（终态 Error + 用户文案），**禁止继续解析半成品页面**
- [ ] 默认目标 URL 更新：`.env.example` `TASK_TARGET_URLS` 更新为 concept 极速版两条（sz000858 / sz300810）；README 演示步骤**新增/更新为** concept 极速版两条（README 现无东财 URL，仅 localhost 演示行，实为新增）；架构文档决策记录补 D4 修订注
- [ ] 真机验收留痕：concept/sz000858 全管道复跑，SSE 事件流 + 截图路径 + 结论 JSON + 工单号写入实现备忘

## 非范围

- 自动过滑块 / 打码平台 / 代理池 / UA 轮换等动态反爬（PRD §9.1 · V2.0+）
- parse_dom / chunker / embedder 的解析逻辑改动（仅 fetch 节点行为增强）
- 对内子图改动；控制台结构性改动（**例外放行**：D7 warning 事件的前端横幅提示属 D7 人决原文「页面提示」的最小落点，允许 30 在 app/web 模板 JS 增 warning 渲染分支一处，R3 审查观察项纳入）

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| 22 未签 `HG-AUDIT-R1` 即 30 改码 | 执行 Agent **拒开工** | 是 | 须先 22 + 签 |
| 渲染等待超时（选择器/非占位文本未出现） | fetch 失败，终态 Error；已落盘部分截图保留 | 是（重交同 URL） | 页面提示「目标页面抓取超时，请稍后重试」 |
| 检测到滑块/验证码覆盖层（人决 D7 放宽） | **渲染确认探针通过**（内容非占位）→ 降级为警告继续解析：SSE 发 `warning` 事件，结论 JSON 标注「页面含验证覆盖层」；**探针不通过** → 才走 ANTI_BOT 终态 Error | 是（稍后重试；不主动绕过验证） | 警告时页面提示「目标页含验证覆盖层，结果已人工可复核」；拦截时提示「目标站点拒绝访问（反爬拦截）」 |
| concept 极速版同样未渲染出行情字段 | 不降级硬猜（铁律一）；按空解析路径流转，对内产出「信息不足」结论 | 是 | 切片区「未提取到有效内容」+ 信息不足结论 |

---

## 验收标准

- [ ] 全量测试命令通过（`.venv/bin/python -m pytest tests -q` 全绿不回退；实测基线口径：`pytest --collect-only` = **106 collected** = **104 passed + 2 skipped**（2026-09-09 10-task 实测），改动后 104 passed 不减少、skipped 不新增失败）
- [ ] **旧测 grep 影响面**（K7 · 2026-09-09 10-task 实测 `grep -rn "sz000858|sz300810|eastmoney" tests/` = **10 文件 26 处**，逐文件处置如下）：
  - `tests/test_web_console_sse.py`（1 处 · TARGET_URL 常量）→ **改为 concept 版 URL**（与 .env.example 默认对齐）
  - `tests/test_acquisition_pipeline.py`（9 处 · mock fetcher 失败注入 + live 冒烟）→ mock 失败注入用例**保留作 SSRF/失败注入语义**（mock 不联网，URL 仅参数）；`test_live_eastmoney` live 冒烟**参数化为 concept 版**（或维持 skipped 标注）
  - `tests/test_acquisition_url.py`（2 处 · URL 白名单用例）→ **保留**（concept URL 同域 quote.eastmoney.com，白名单语义不受影响）
  - `tests/test_web_console_api.py`（2 处 · API 入参 URL）→ **参数化/改为 concept 版**（与默认 URL 对齐）
  - `tests/internal_rag_fakes.py`（2 处）· `tests/test_internal_rag_contract.py`（1 处）· `tests/test_internal_rag_graph.py`（1 处）· `tests/test_internal_rag_live.py`（2 处）→ **保留不受影响**（对内子图 fixture/契约，URL 仅透传参数，本 task 不碰对内链路）
  - `tests/test_acquisition_parser.py`（5 处 · HTML fixture 内 sz000858 文本）→ **保留不受影响**（解析 fixture 文本与目标 URL 无关）
  - `tests/test_acquisition_chunker.py`（1 处 · estimate_tokens("sz000858") 纯字符串）→ **保留不受影响**
  - 显式断言：新增渲染等待/滑块检测**不破坏既有 mock fetcher 失败注入用例**（ANTI_BOT / FETCH_TIMEOUT 现行断言口径不变）；改动后 104 passed 基线全量不回退仍成立
- [ ] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过
- [ ] **渲染等待单测**：mock page 对象断言 fetch 节点在内容就绪前不放行（wait 逻辑被调用、超时走 FETCH_TIMEOUT）
- [ ] **滑块检测单测（人决 D7 口径）**：含「拖动下方滑块」特征 fixture + 探针通过 → **继续解析 + `warning` 事件 + 结论标注「页面含验证覆盖层」**；fixture + 探针不通过 → ANTI_BOT 终态 Error；正常 fixture 不误报
- [ ] **默认 URL 断言**：`.env.example` 与 README 中目标 URL 为 `quote.eastmoney.com/concept/sz000858.html` 与 `concept/sz300810.html`
- [ ] **真机 A5 复跑（人决 D7 口径）**：concept/sz000858 跑通 Pending→…→Done；截图允许含覆盖层（00 人工看图复核留痕即可），但结论 JSON 须带「验证覆盖层」警告标注、工单号非空

---

## 给执行帽的必读列表

1. `docs/spec/SPEC-web-research-agent_v1.md`（铁律一 / failure_paths FP-1/FP-2）
2. `docs/spec/architecture/frontend_backend_breakdown_v1.md` §1.3（fetch_page 三行式）与 §5 决策 D4
3. `docs/tasks/done/task_web_acquisition_subgraph.md`（对外子图既有实现与验收）
4. `docs/harness/reviews/task_web_acquisition_subgraph_audit_R1_20260909.md`
5. 用户截图证据（会话留痕）：滑块覆盖层 + 字段未渲染

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| 渲染确认策略 | ✅ | goto(domcontentloaded) 后 `wait_for_load_state`：networkidle 优先（超时降级 domcontentloaded 兜底，不视为失败）+ 非占位文本等待（`wait_for_function`：body innerText 剔除空白与 `-—–_` 占位符后 ≥30 字符）；阈值 `FETCH_RENDER_TIMEOUT_MS`（默认 10000，browser.py 模块内 os.getenv 读取 · app/config.py 冻结未动）；非占位等待超时 → FetchTimeout 终态，确认通过前不放行 content() |
| 滑块特征清单 | ✅ | ① 文案：拖动下方滑块完成拼图 / 拖动左边滑块 / 滑块验证 / 请完成安全验证等；② DOM 组件签名：nc-container / nc_wrapper / geetest / slide-verify；③ **子框架 URL**：websitecaptcha / slidervalid —— 真机实证东财滑块挂独立 iframe（`i.eastmoney.com/websitecaptcha/slidervalid`），主框架 innerText/content 均扫不到，首轮实现漏检（截图含滑块却放行），补扫 `page.frames[1:]` 后修复；命中即 anti_bot_flag → ANTI_BOT 终态 + 截图留痕，禁止解析半成品 |
| 真机复跑结果 | ⏳ D7 前口径实证 · 待 30 续施工回填 |（D7 前实证，D7 口径复跑由 30 续施工执行） NO_PROXY 净化后 uvicorn:8011 全管道实跑 5 次 + sz300810 探针 1 次（2026-09-09 19:25–19:52）：① **19:25 跑（渲染确认已生效 / iframe 检出修复前）**：Pending→Fetching(10%)→Parsing(50%)→RAGing→Done(100%)，12 切片含真实行情文本（分时成交/股吧时间戳 19:21 即渲染当时内容，渲染确认实证有效），结论 JSON 非空（price 仍「-」占位 → insufficient_info=true 如实输出，铁律一），**工单号 MOCK-18F5C515**，截图 `app/static/shot_8b1b8439f2_1788953109798.png` —— 但截图顶部含滑块覆盖层（iframe 盲区，主框架扫不到）；② **修复后 19:28/19:30/19:36/19:52 四跑 + sz300810 探针**：全部正确检出滑块 → ANTI_BOT 终态 Error + SSE error 事件（user_message「目标站点拒绝访问（反爬拦截）」）+ 截图留痕（`shot_8b1b8439f2_1788953319141.png` 等 4 张，滑块清晰可见供 00 人工看图），无半成品解析；③ 东财对本机 IP 持续下发滑块（6 连命中，含 15 分钟冷却后），「Done + 无滑块截图」本轮未达成 —— 残余风险①实锤，交 00 人决（换网络/时段重试或签收 ANTI_BOT 实证口径） |

---

## 测试策略（Harness）

**test_strategy**: `required` —— 先落 mock/fixture 失败用例再改 fetch 实现；真机复跑为人工可见验收。

---

### 自检结论（执行者）

30/40 同上下文闭环（2026-09-09 · worktree `.worktrees/fetch` · 分支 `task/fetch_render_wait_lite`）：

| 验收项 | 结论 | 证据 |
|--------|------|------|
| 全量测试不回退 | ✅ pass | `pytest tests -q` exit 0：**114 passed, 2 skipped**；`--collect-only` = **116 collected**（基线 106=104+2，新增 10 全绿，零回退、skipped 无新增失败） |
| 旧测 grep 影响面（10 文件 26 处逐条处置） | ✅ pass | 改 3 文件 4 处（sse TARGET_URL / api ×2 / pipeline live 冒烟 → concept 版，live 维持默认 skipped 不参数化以钉死 collected 口径）；保留 7 文件 22 处（mock 失败注入 SSRF 语义 / 白名单 / 对内 fixture / parser fixture / chunker 纯字符串）；显式断言成立：既有 ANTI_BOT/FETCH_TIMEOUT mock 注入用例断言口径不变且全绿 |
| lint-wiki-delta | ✅ pass | `task lint-wiki-delta --target .` exit 0（LINT-WIKI-DELTA: PASS） |
| 渲染等待单测 | ✅ pass | `tests/test_acquisition_browser.py::TestRenderWait` ×4：networkidle 优先 / 兜底链 / 超时 FetchTimeout 且不放行 content() / env 覆盖（全 mock，零浏览器） |
| 滑块检测单测 | ⏳ D7 前口径实证 · 待 30 续施工回填 |（D7 前实证，验收以 D7 口径行为准） `TestSliderDetection` ×6：滑块 fixture → 图级 ANTI_BOT 终态（无 payload/blocks）；iframe URL / iframe 正文双检出；正常 fixture + 广告 iframe 不误报 |
| 默认 URL 断言 | ✅ pass | `.env.example` L8 与 README L64-65 均为 concept/sz000858 + concept/sz300810（grep 实证） |
| 真机 A5 复跑 | ⚠️ 部分 | 见实现备忘「真机复跑结果」行：A5 闭环（Done + 工单号 MOCK-18F5C515 + 结论非空）19:25 跑达成；「截图无滑块覆盖层」未达成 —— 东财持续下发滑块（6 连命中），修复后检出语义四跑实证（ANTI_BOT 终态 + 截图留痕）。**此项留 00 人决** |

已知未测项：① 干净会话（无滑块）下 concept 页端到端截图（站点侧阻断，非代码缺陷）；② `FETCH_RENDER_TIMEOUT_MS` 真机调参未做（单测覆盖 env 读取）。

命令块（workdir=.worktrees/fetch）：
- `npx --yes dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_fetch_render_wait_lite.md` → exit 0 VERIFY: PASS（首跑 BLOCKED·缺 hat-10 invoke，主仓同步后 PASS）
- `.venv/bin/python -m pytest tests -q`（仓根执行）→ exit 0（114 passed, 2 skipped）
- `npx --yes dsh-coding-kit@1.10.0 task lint-wiki-delta --target .` → exit 0
- 真机：`NO_PROXY=localhost,127.0.0.1,::1 uvicorn app.api.main:app --port 8011` + POST /api/task + SSE 流（事件留档 /tmp/fetch_realrun_events.json，截图 app/static/）

---

### KPI（00）

（`kpi_aggregator: CLOSE` · 关账回溯填写）

---

### 经验总结

（`experience_capture: recommended` · 关账时建议回填）

---

## 思考轮（00 起草预置 · 30/22 可续填）

### R0 · 读人聊
用户真机验收截图：标准页触发滑块验证 + 字段未渲染即解析。人决：切极速版 concept 链接 + 确认真实渲染后再解析。

### R1 · 范围
仅 fetch_page 行为增强 + 默认 URL/文档更新 + 真机复跑；不碰解析/切分/对内/控制台。

### R2 · 方案对比
- 方案 A（推荐）：networkidle + 关键内容选择器等待 —— 确定性高、零新依赖。
- 方案 B（弃）：固定 sleep 延时 —— 不稳定且拖慢全管道。
- 方案 C（弃，V2）：打码/过滑块 —— 属反爬加固，PRD §9.1。

### R3 · 边界
滑块检出即走 ANTI_BOT，不尝试绕过；渲染确认失败不降级多模态（铁律一）。**续填（人决 D7 · 2026-09-09）**：滑块为悬浮覆盖层且背景 DOM 已完整渲染时，检出降级为警告继续（探针通过为前提），结论标注「页面含验证覆盖层」；SSE 事件枚举增 `warning` 第六类（架构 §1.1 注记）；探针不通过仍 ANTI_BOT 终态，不主动绕过验证。

### R4 · 验收
单测 mock wait 逻辑 + 滑块 fixture；真机 concept 版 A5 复跑为一票否决级人工可见验收。

### R5 · 就绪
改动面小（单节点 + 文档默认值），一轮 30 可闭环；交 20 审后人签（00 代签授权在案）。

**R5 续填（30 施工实证）**：① 东财滑块挂**独立 iframe**（websitecaptcha/slidervalid），主框架 innerText/content 均扫不到 —— 首版检出漏报（截图含滑块却放行），补扫 `page.frames[1:]` 修复；此坑值得关账时沉淀 wiki。② 残余风险①实锤：2026-09-09 19:25–19:52 东财对本机 IP 持续滑块（6 连命中），concept 版不免疫；检出→ANTI_BOT 终态语义实机验证通过，「干净 Done + 无滑块截图」需换时段/网络重试。③ pre-30 invoke 须随 task 同仓（hat-10 留档漏同步 worktree 会挡 verify，已补）。

### 思考轮控制

| 项 | 值 |
|----|-----|
| early_stop | no |
| reason | 默认全轮执行（00 起草时一轮填实，改动面小） |
| residual_risks | ① concept 极速版亦可能触发反爬（不承诺成功率）；② 选择器锚点依赖东财页面结构，未来改版需跟进 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 00 起草初版（真机验收发现 · 人决切极速版 + 渲染确认） |
| 2026-09-09 | 10-task 按 R1 退回意见修订 R2 送审：① 验收新增「旧测 grep 影响面」项（实测 10 文件 26 处逐文件处置标注）；② 基线数更正为实测口径 106 collected = 104 passed + 2 skipped；③ 范围第 3 条措辞「改为」→「新增/更新为」（README 现无东财 URL） |
| 2026-09-09 | 人决 D7：滑块检出放宽为「警告但继续」（探针通过前提）；失败路径/验收行/R3 续填同步修订，送 20 R3 复核 |
