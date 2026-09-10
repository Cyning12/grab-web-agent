# Task：抓取目标切换腾讯 gu.qq.com 与双股票真机验收（switch_target_gu_qq）

> **状态**：`done`  
> **关联图谱**：无  
> **落盘**：`docs/tasks/active/task_switch_target_gu_qq.md`；验收后 `git mv` → `docs/tasks/done/`

---

## Harness 元信息

| 字段 | 值 |
|------|-----|
| **task_slug** | `switch_target_gu_qq` |
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
| **git_branch** | `task/switch_target_gu_qq` |
| **worktree_root** | `.worktrees/gu`（00 建） |
| **graph_delta** | `none` |
| **graph_delta_note** | 目标站点切换 + 解析适配，无图结构变化 |
| **wiki_delta** | `none` |
| **wiki_delta_note** | 站点切换属配置层决策，经验入 task 经验总结 |
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

人决 D8（2026-09-09 用户会话）：东财对本机 IP 持续下发滑块验证（残余风险实锤），切换抓取目标为**腾讯自选股** `https://gu.qq.com/sz000858/gp`——用户实测**暂无反爬**。完成态 = 默认目标双链切腾讯版，sz000858（五粮液）/ sz300810（中科海讯）各跑通 Pending→…→Done 全闭环，截图无蒙层、切片为真实行情文本、结论 JSON 非空、工单号产出；若腾讯页结构与既有解析器不适配，做**最小解析适配**。

---

## 范围

- [x] 默认目标 URL 切换：`.env.example` `TASK_TARGET_URLS` 与 README 更新为 `https://gu.qq.com/sz000858/gp`、`https://gu.qq.com/sz300810/gp`；架构文档 §5 增 D8 决策行—— 00 复核：双链切换 + 架构 §5 D8 行落盘
- [x] **腾讯页全管道实测与最小解析适配**：30 真机跑通腾讯页；若 parse_dom/chunker 对其结构提取为空或过碎，允许最小适配（限 `app/services/acquisition/parser.py` 选择器/语义规则增补；chunker 仅在切分明显不合法时动）—— 00 复核：parser 最小增补 ×2（纯标签跳过 + title 兜底），chunker 零改动（判定实例留痕）
- [x] **腾讯页 HTML fixture**：真机落一份页面快照为 fixture，新增解析/切分用例（切片非空、section_path/xpath 非空、无「-」全占位正文）—— 00 复核：tests/fixtures/gu_qq_sz000858.html 真机快照落盘
- [x] **双股票真机验收**：sz000858 与 sz300810 各一次全管道（SSE 流 + 截图 + 结论 + 工单号写入实现备忘；截图留 app/static/ 供 00 看图）—— 00 复核：双 SSE 流 + 截图 + 结论 + 工单号写入实现备忘
- [x] **旧测影响面（K7）**：grep tests/ 旧东财 URL 引用，按语义逐条处置（保留作反爬/失败注入语义的保留，作默认目标的改腾讯）—— 00 复核：26 处处置=改腾讯 8 / 保留东财 18，处置后复跑与标注逐条一致

## 非范围

- 东财链接的兼容维护（切默认目标；旧链仍可手动输入但不保证成功率）
- 任何反爬绕过手段；对内子图/控制台改动
- 价格字段强保证（腾讯页若同样异步渲染致占位，如实 insufficient_info，不硬猜——铁律一）

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| 22 未签 `HG-AUDIT-R1` 即 30 改码 | 执行 Agent **拒开工** | 是 | 须先 22 + 签 |
| 腾讯页结构变更致解析为空 | 空 chunks 流转，对内产出「信息不足」结论（铁律一不降级） | 是（换 URL/待适配） | 切片区「未提取到有效内容」 |
| 腾讯后续上线反爬 | 按既有 ANTI_BOT/超时路径落终态 | 是 | 对应错误文案 |

---

## 验收标准

- [x] 全量测试命令通过（`.venv/bin/python -m pytest tests -q` 全绿；基线 129 collected = 127 passed + 2 skipped 不回退——20 审实测复核）—— 00 复核：合并后 main = **131 passed, 2 skipped**（collect 133 · 基线 129 零回退）
- [x] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过—— 00 复核：PASS
- [x] **fixture 解析断言**：腾讯页 fixture → 切片 ≥1 且 section_path/xpath 非空、正文非全占位—— 00 复核：test_acquisition_parser_gu_qq.py + 真机快照 fixture 随全量通过（price 真值提取断言含）
- [x] **旧测影响面处置完毕**：grep 命中逐条标注且与处置一致—— 00 复核：26 处处置=改腾讯 8 / 保留东财 18，处置后复跑与标注逐条一致
- [x] **双股票真机闭环（一票否决级）**：两个 URL 各自 Pending→…→Done + 工单号非空；截图 00 人工看图（无蒙层、内容真实）—— 00 **人工看图 ×2**：sz000858（71.16 已收盘 · 无蒙层 · 工单 MOCK-19A83A73）与 sz300810（27.73 +11.59% · 无蒙层 · 工单 MOCK-CE85445C）双 Done 闭环
- [x] **默认 URL 断言**：.env.example/README 双链为 gu.qq.com—— 00 复核：.env.example/README 双链已切 gu.qq.com

---

## 给执行帽的必读列表

1. `docs/tasks/done/task_fetch_render_wait_lite.md` · `docs/tasks/done/task_screenshot_delay.md`（渲染确认/滑块检出/延迟现状）
2. `docs/spec/architecture/frontend_backend_breakdown_v1.md` §1.3 · §5（D7/D8）
3. `docs/spec/web-research-agent/SPEC-web-research-agent_v1.md`（铁律一 · A3/A5/A6）
4. 用户会话原话：「腾讯的暂时未发现反抓取」

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| 腾讯页解析适配点 | ✅ 最小适配（限 parser.py） | 真机首跑探测（2026-09-09）：http 200 · anti_bot=False · 283 blocks / 5855 tokens / 6 切片 token_count ∈ [869,1018] ⊂ [512,1024]——**提取非空、切分合法，chunker 零改动**（审查建议②「切分明显不合法」判定实例：不适用，chunker 未动，留痕于此）。唯一缺陷：`_extract_price` 首个选择器命中 `span#price` 文本为「分价」标签（非数值）误提取；真价 71.16 在 `<title>`「五 粮 液 71.16 -0.49(-0.68%)_…」。适配（parser.py 选择器/语义规则增补 ×2）：① 选择器命中文本**无数字即跳过**（纯标签不取）；② **标题正则兜底**（¥ 金额 → 两位小数）置于正文正则之前（正文首个两位小数是大盘指数 3951.51 而非个股价）。东财夹具用例（¥128.50 选择器命中含数字 / 无标题正文兜底）全部保持绿 |
| 旧测影响面处置（开工首命令 grep 实测 9 文件 26 处） | ✅ 改 8 / 保留 18 | 实测 `grep -rn "eastmoney" tests/` = **9 文件 26 处**（quote.eastmoney.com 字面量 20 处），与 R1 审查实测完全吻合。**改腾讯（默认目标语义 8 处）**：test_web_console_sse.py:26 TARGET_URL（+注释行）· test_web_console_api.py:69/86 API 入参 ×2 · test_acquisition_pipeline.py:108/114（契约 happy path）+ 145（铁律一审计）+ 209/215（live 冒烟改名 test_live_gu_qq + URL → gu.qq.com，维持默认 skipped 钉死 collected 口径）。**保留东财（反爬/失败注入/SSRF/对内透传语义 18 处）**：test_acquisition_browser.py ×8（滑块 iframe websitecaptcha/slidervalid、广告 iframe same.eastmoney、FakePage 占位 URL——反爬检出 fixture 语义）· test_acquisition_pipeline.py:159/170/185/196（超时/ANTI_BOT/空解析/EMBED 失败注入桩，URL 仅参数）· test_acquisition_url.py ×2（SSRF 白名单公网接受用例，东财仍合法公网 URL）· internal_rag_fakes.py / test_internal_rag_contract / test_internal_rag_graph / test_internal_rag_live ×4（对内 fixture/契约，URL 仅透传，本 task 不碰对内链路）。处置后复跑实测剩余 **18 处**，与标注逐条一致 |
| sz000858 真机结果 | ✅ Done（2026-09-09 23:11 本机） | NO_PROXY/no_proxy 大小写双写净化 + uvicorn:8011 全管道：Pending→Fetching(10%)→Parsing(50%)→**6 切片**（真实行情文本：昨收 71.65/今开 71.64/总市值 2762亿/股吧与个股新闻即渲染当时内容）→RAGing→progress 100→**Done**；extracted_meta：title=「五 粮 液 71.16 -0.49(-0.68%)_财经频道_腾讯网」· **price=71.16**（标题兜底实证适配生效）· http 200；结论 JSON 非空：competitor_price=「未知」· **insufficient_info=true**（价格数值已提取但对内 LLM 未硬猜，如实标注，铁律一）· sources 含半年报；**工单号 MOCK-19A83A73**；截图 `app/static/shot_5a29bdfd20_1788966704678.png`（30 亲看图：**无蒙层**、行情页完整真实，待 00 人工看图复核）；事件流 /tmp/gu_run_sz000858_events.json · 快照 /tmp/gu_run_sz000858_snapshot.json |
| sz300810 真机结果 | ✅ Done（2026-09-10 08:49 本机） | 同口径 uvicorn:8011 全管道：Pending→…→**4 切片**（中科海讯 27.73 +11.59%、流通股东、机构预测等真实文本）→RAGing→**Done**；extracted_meta：title=「中科海讯 27.73 2.88(+11.59%)_财经频道_腾讯网」· **price=27.73** · http 200；结论 JSON 非空 · insufficient_info=true（如实）· sources 含半年报；**工单号 MOCK-CE85445C**；截图 `app/static/shot_6027093525_1789001383890.png`（30 亲看图：**无蒙层**、内容真实，待 00 人工看图复核）；事件流 /tmp/gu_run_sz300810_events.json · 快照 /tmp/gu_run_sz300810_snapshot.json |

---

## 测试策略（Harness）

**test_strategy**: `required` —— fixture 用例先行；真机双 URL 闭环为一票否决级人工可见验收。

---

### 自检结论（执行者）

30/40 同上下文闭环（2026-09-09/10 · worktree `.worktrees/gu` · 分支 `task/switch_target_gu_qq`）：

| 验收项 | 结论 | 证据 |
|--------|------|------|
| 全量测试通过（基线 129=127+2 不回退） | ✅ pass | `.venv/bin/python -m pytest tests -q` exit 0：**131 passed, 2 skipped**；`--collect-only` = **133 collected**（基线 129 + 腾讯 fixture/价格适配新用例 4，零回退、skipped 无新增失败） |
| lint-wiki-delta | ✅ pass | `npx --yes dsh-coding-kit@1.11.0 task lint-wiki-delta --target .` exit 0（LINT-WIKI-DELTA: PASS · scanned 8 · issues 0） |
| fixture 解析断言 | ✅ pass | `tests/fixtures/gu_qq_sz000858.html`（真机快照 226KB · http 200 · anti_bot=False）→ `tests/test_acquisition_parser_gu_qq.py` ×4：切片 6 ≥1 且 token_count ∈ [869,1018]、section_path/xpath 全非空、正文非全占位（存在 ≥30 字符真实正文块）、price=71.16（非「分价」标签） |
| 旧测影响面处置完毕 | ✅ pass | grep 实测 9 文件 26 处逐条处置：改 8（默认目标语义 → 腾讯）/ 保留 18（反爬/失败注入/SSRF/对内透传）；处置后复跑 grep 余 18 处与标注一致（详见实现备忘行） |
| 双股票真机闭环（一票否决级） | ✅ pass（待 00 人工看图终签） | sz000858：Pending→…→Done · 6 切片 · price=71.16 · 工单 **MOCK-19A83A73** · 截图 `app/static/shot_5a29bdfd20_1788966704678.png`；sz300810：Pending→…→Done · 4 切片 · price=27.73 · 工单 **MOCK-CE85445C** · 截图 `app/static/shot_6027093525_1789001383890.png`；30 已亲看两图：无蒙层、行情内容真实 |
| 默认 URL 断言 | ✅ pass | `.env.example` L8 TASK_TARGET_URLS 与 README 演示节均为 `https://gu.qq.com/sz000858/gp` + `https://gu.qq.com/sz300810/gp`（grep 实证）；架构 §5 增 D8 决策行 + 修订记录一行 |

命令块（workdir=.worktrees/gu）：
- `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.11.0 verify --task docs/tasks/active/task_switch_target_gu_qq.md` → exit 0 **VERIFY: PASS**（开工首跑 · 首输出 GATE_VERIFY 闸扫描双闸 approved）
- `grep -rn "eastmoney" tests/` → 26 处（开工第一条命令，审查建议①落实）；处置后 → 18 处
- `.venv/bin/python -m pytest tests -q` → exit 0（131 passed, 2 skipped）；`--collect-only -q` → 133 collected
- `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.11.0 task lint-wiki-delta --target .` → exit 0
- 真机：`env NO_PROXY=localhost,127.0.0.1,::1 no_proxy=localhost,127.0.0.1,::1 .venv/bin/python -m uvicorn app.api.main:app --port 8011` + POST /api/task + SSE 全事件收集（5 分钟硬超时兜底）×2 URL → 双 Done（事件流/快照 /tmp/gu_run_* 留档，截图 app/static/）

已知未测项：① 截图 00 人工看图终签待做（30 已亲看两图无蒙层）；② live 冒烟（ACQ_LIVE_SMOKE=1）维持默认 skipped 未真跑（真机双 URL 闭环已覆盖同路径）；③ 腾讯页「分价表/大单数据」等二级页未抓取（非本 task 范围）。

---

### KPI（00）

Task_KPI%: 100

| 维度 | 评分 | 依据 |
|------|------|------|
| D1 闸完整性 | 5/5 | 双闸代签 · R1 PASS（审查员亲验 grep/pytest 数字吻合）· verify PASS |
| D2 验收覆盖 | 5/5 | 验收全勾；双股票真机闭环经 00 人工看图 ×2（真价 71.16 / 27.73 · 无蒙层） |
| D3 过程留痕 | 5/5 | invoke 三段齐；fixture 真机快照 + 双截图 + 双工单留档；子 Agent 中断后现场被 00 盘点无损接续（教训落经验） |
| D4 范围纪律 | 5/5 | 共享文件零越界；chunker 零改动判定留痕；旧测 26 处逐条处置 |
| D5 测试制品 | 5/5 | 净增 4 用例零回退（131 passed） |

---

### 经验总结

（已回填 · 2026-09-09 CLOSE）
- **换站比攻坚反爬便宜得多**：东财滑块攻坚属 V2 代理池范畴；切腾讯页后真价（71.16/27.73）直接可提取——数据源选型是采集系统的第一层架构决策。
- **价格提取的「纯标签陷阱」**：`span#price` 命中了「分价」标签文本而非价格（真价在 title/专用节点）——语义提取须「值形态校验」（无数字命中跳过 + 兜底源），不能只看选择器命中。
- **子 Agent 中断现场可无损接续**：本 task 的 30 在完工前失败，worktree 未提交但磁盘完好；00 盘点（git status + pytest 复跑）确认后续派同 Agent 收尾——worktree 隔离 + 分支即交付物的纪律让中断恢复成本为零。

---

## 思考轮（00 起草预置）

### R0 · 读人聊
用户：「https://gu.qq.com/sz000858/gp，更改抓取的目标URL，腾讯的暂时未发现反抓取」。

### R1 · 范围
默认 URL 切换 + 最小解析适配 + fixture + 双股票真机验收 + 旧测影响面。不碰对内/控制台/反爬。

### R2 · 方案对比
- 方案 A（推荐）：直接切腾讯页 + 实测后最小适配 —— 用户已实测无反爬，成本最低。
- 方案 B（弃）：东财 + 代理池攻坚 —— V2 范畴（PRD §9.1），当前过度工程。
- 方案 C（弃）：双站并行适配 —— 无需求，徒增维护面。

### R3 · 边界
解析为空走既有空 chunks 路径（铁律一不降级）；腾讯若后续上反爬按既有失败路径；适配仅限 parser 选择器层。

### R4 · 验收
fixture 断言 + 旧测影响面 + 双 URL 真机闭环（一票否决）+ 00 看图。

### R5 · 就绪
改动面小（配置 + 可能的 parser 适配），一轮 30 闭环；真机验收是主要工作量。

### 思考轮控制

| 项 | 值 |
|----|-----|
| early_stop | no |
| reason | 默认全轮执行（00 起草一轮填实） |
| residual_risks | ① 腾讯页结构适配工作量实测才知；② 腾讯未来上反爬的可能（失败路径已备）；③ 价格字段仍可能异步占位（铁律一如实输出） |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 00 起草初版（人决 D8：目标切腾讯 gu.qq.com） |
