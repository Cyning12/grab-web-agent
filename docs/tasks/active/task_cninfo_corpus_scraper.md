# Task：cninfo 财报语料抓取脚本（cninfo_corpus_scraper · 人决 D6 兑现）

> **状态**：`draft`  
> **关联图谱**：无  
> **落盘**：`docs/tasks/active/task_cninfo_corpus_scraper.md`；验收后 `git mv` → `docs/tasks/done/`

---

## Harness 元信息

| 字段 | 值 |
|------|-----|
| **task_slug** | `cninfo_corpus_scraper` |
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
| **git_branch** | `task/cninfo_corpus_scraper` |
| **worktree_root** | `.worktrees/cninfo`（00 建） |
| **graph_delta** | `none` |
| **graph_delta_note** | 独立脚本，不入 LangGraph 图 |
| **wiki_delta** | `none` |
| **wiki_delta_note** | 单脚本交付，经验入 task 经验总结 |
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
| HG-AUDIT-R1 | approved | 30 | 20-task-audit R2 PASS · 00 代签 2026-09-09（授权在案） |

---

## 背景与目标

人决 D6 + D6-修订（2026-09-09 · 20 审实证裁定）：内部语料来源为巨潮资讯（cninfo）公告查询，样例已人工保存于 `company/`（磁盘实有 `000858/`、`300810/` 裸号目录）；需补一个**抓取脚本**，按**上市编号裸 6 位**命名区分、自动落盘（sz/sh 前缀废弃——retriever derive_company_code 剥前缀产出裸号，前缀致语料分裂 + 标量过滤静默失效）。完成态 = 一条命令 `python -m scripts.fetch_cninfo 000858 300810` 把两家公司的定期报告（年报/半年报优先）PDF 抓取到 `company/000858/`、`company/300810/`，对内子图 FAISS 检索可直接消费。

---

## 范围

- [ ] `scripts/fetch_cninfo.py` CLI：入参 = 一个或多个上市编号（接受 `sz000858` / `000858` 等写法，**归一化为裸 6 位**——剥前缀正则 `^(sz|sh|bj)` 不区分大小写，非法编号报错不建目录）；按裸号建目录 `company/<6位code>/` 落盘 PDF
- [ ] 抓取源：cninfo 公告查询接口（30 实测选型：hisAnnouncement 查询 API 优先于全文检索页爬取；纯 httpx，**不引入 Playwright**）；过滤定期报告类目（年报/半年报），每公司默认最新 N 份（N env 或参数可配，默认 2）
- [ ] 礼貌抓取：请求间隔 + User-Agent；失败单文件跳过不中断整批
- [ ] README 增「语料更新」节：命令照抄可执行
- [ ] 单测：mock httpx 响应（列表页 + PDF 下载），断言目录创建/命名/跳过坏文件；**单测零外网**
- [ ] 真机验收：双编号实跑，`company/` 两目录各 ≥1 份 PDF 且 pypdf 可打开提取文本

## 非范围

- 全文检索页（fulltextSearch）的 JS 渲染爬取（先用公告 API；API 不可用再议）
- 语料入库/FAISS 索引构建自动化（对内子图运行时自行构建，既有）
- 增量更新/去重策略精细化（V1 同名覆盖即可）
- 代理池/反爬（PRD §9.1）

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| 22 未签 `HG-AUDIT-R1` 即 30 改码 | 执行 Agent **拒开工** | 是 | 须先 22 + 签 |
| cninfo API 限流/超时 | 单文件重试 ≤2 后跳过，批次继续；末尾汇总失败清单 | 是（重跑命令） | 终端输出成功/失败计数 |
| 编号不存在/无定期报告 | 目录建空 + 明示「未找到」 | 是 | 终端提示 |
| PDF 下载损坏（pypdf 打不开） | 删除坏文件并计入失败清单 | 是 | 终端提示 |

---

## 验收标准

- [ ] 全量测试命令通过（**钉死**：`.venv/bin/python -m pytest tests -q` 仓根执行；基线 129 collected = 127 passed + 2 skipped 不回退，20 审实测复核）
- [ ] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过
- [ ] **CLI 单测**：mock 下双编号跑通，目录/命名/跳过语义断言；零外网
- [ ] **真机验收（一票否决级）**：`python -m scripts.fetch_cninfo 000858 300810` 实跑 exit 0，`company/000858/` 与 `company/300810/` 各 ≥1 份 PDF，pypdf 提取文本非空
- [ ] **README 断言**：含语料更新命令节

---

## 给执行帽的必读列表

1. `company/README.md`（D6 目录约定）
2. `docs/spec/architecture/frontend_backend_breakdown_v1.md` §5 D6 · §1.4（对内消费方式：pypdf 提取 + FAISS）
3. `app/services/rag/retriever.py`（确认语料消费格式，保证落盘兼容）
4. 用户会话原话：「内部资料来源：cninfo 全文检索（五粮液/中科海讯）；按上市编号命名区分，保存 company/」

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| cninfo API 选型实测 | ⏳ | |
| 双编号真机结果 | ⏳ | |

---

## 测试策略（Harness）

**test_strategy**: `required` —— mock 用例先行；真机抓取为一票否决级验收。

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
人决 D6：cninfo 语料按上市编号落盘 company/；样例已人工保存，需脚本自动化。

### R1 · 范围
单脚本 CLI + 单测 + README + 真机双编号验收。不动对内检索实现。

### R2 · 方案对比
- 方案 A（推荐）：cninfo 公告查询 API + httpx —— 无浏览器开销，符合瘦内耗。
- 方案 B（弃）：Playwright 爬 fulltextSearch 页 —— 重、慢，且 API 可满足。
- 方案 C（弃）：纳入对外子图管道 —— 语料更新是离线批操作，不该进在线管道。

### R3 · 边界
纯离线脚本；限流礼貌；坏文件跳过；与对内消费格式兼容（pypdf 可读）。

### R4 · 验收
mock 单测 + 真机双编号抓取（一票否决）+ README 节。

### R5 · 就绪
单文件脚本，一轮 30 闭环。

### 思考轮控制

| 项 | 值 |
|----|-----|
| early_stop | no |
| reason | 默认全轮执行（00 起草一轮填实） |
| residual_risks | ① cninfo 接口字段/限流策略以实测为准；② 全文检索场景（关键词非公司名）V1 不支持 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 00 起草初版（人决 D6 兑现 · 长程 goal ②） |
| 2026-09-09 | 20 R1 RETURN 修订（00 代行 10-task）：B1 命名口径统一裸 6 位（D6-修订）+ 入参归一规则 + exempt 笔误 + pytest 命令钉死，送 R2 |
