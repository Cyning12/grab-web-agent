# 审查文 · task_project_scaffold R1（20-task-audit）

| 项 | 值 |
|----|-----|
| **审查对象** | `docs/tasks/active/task_project_scaffold.md` |
| **task_slug** | `project_scaffold` |
| **审查轮次** | R1 |
| **审查日期** | 2026-09-09 |
| **审查帽** | 20-task-audit（skill 已加载并遵守「只做/禁止」） |
| **对照真值** | `docs/spec/SPEC-web-research-agent_v1.md`（signed）+ `docs/spec/_source/PRD_web_research_agent_v2.md` + `docs/spec/architecture/frontend_backend_breakdown_v1.md`（§5 决策 D1–D6） |
| **结构真值** | `docs/harness/templates/TASK_TEMPLATE.md` |
| **前置闸** | HG-TASK-DRAFT = approved（人签 2026-09-09 会话）✅ |

---

## 结论摘要

- **内容审查：PASS** —— 范围/非范围/验收/failure_paths/思考轮/元信息全部零内容阻塞。
- **流程闸：HG-AUDIT-R1 = pending** —— 须维护者签 task 表后方可下发 30（见文末签闸清单）。
- **总结论：PASS（建议人签 HG-AUDIT-R1）**。

## 机械闸复核（实测）

| 命令 | 结果 | exit code |
|------|------|-----------|
| `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 task lint --file docs/tasks/active/task_project_scaffold.md` | `LINT: PASS` | **0** |
| `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 gate-check --task docs/tasks/active/task_project_scaffold.md` | HG-TASK-DRAFT=approved；HG-AUDIT-R1=pending → 拒 30 | **2**（预期：流程闸未签，非内容缺陷） |

## 核对项明细

### 1. 范围纯底座 · 无业务实现越界 ✅
- 范围六项（依赖钉版 / 目录结构 / .env.example / config.py / .gitignore / 冒烟 + README）全为工程底座，节点明确「全部为 stub」，完成态定义为「下游三 task 的 30 直接在其目录槽位内填实现、无需再动工程骨架」，定位清晰。
- 非范围显式排除：真实抓取/解析/切分/Embedding/检索/LLM 调用（属下游三 task）、SSE/任务注册表/SSRF/Payload 契约校验等业务逻辑、cninfo 抓取脚本（人决 D6 另立 task）、Docker/CI（人决 D3）、多模态接入（铁律一）——派发单要求的排除项全部在列。
- R1 互锁检查句（stub 不含 SSRF/Payload Schema/SSE，与 T-ACQ/T-RAG/T-WEB 范围行互锁）与三下游 task 的非范围无冲突；R3 边界一「任何 SSRF 校验、Payload Schema、SSE、检索逻辑的出现即越界，退回」防越界机制明确。
- 背景节「三个 MVP task 双闸已 approved」经核实为真（三 task 的 HG-TASK-DRAFT 与 HG-AUDIT-R1 均 approved）。

### 2. .env.example 8 变量与人决 D5 逐字一致 ✅
- 8 个变量齐备：`SILICONFLOW_API_KEY`（空值占位）/ `SILICONFLOW_BASE_URL` / `LLM_MODEL` / `EMBEDDING_MODEL` / `FASTAPI_PORT` / `FLASK_PORT` / `COMPANY_DIR` / `TASK_TARGET_URLS`。
- `LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash` 与架构文档 §5 D5「生成：deepseek-ai/DeepSeek-V4-Flash」**逐字一致**；`EMBEDDING_MODEL=BAAI/bge-m3` 与 D5「Embedding：bge-m3（BAAI/bge-m3）」括号内规范名**逐字一致**。
- `TASK_TARGET_URLS` 两 URL 与 D4 东财股票页 ×2（sz000858/sz300810）逐字一致；`COMPANY_DIR=./company` 与 D6 目录约定一致。
- Key 不落盘明文三重锁定：`SILICONFLOW_API_KEY=` 空值占位 + `.env` 入 `.gitignore`（验收含 `cp .env.example .env` 后 `git status` 不显示）+ 验收「仓库内 grep 无明文 API Key」，与 D2/D5「经环境变量注入、不落盘明文」一致。

### 3. 目录/节点名与架构 §1.3/§1.4 三行式一致 ✅
- acquisition 六节点 `validate_url → fetch_page → parse_dom → chunk_sections → embed_chunks → emit_payload` 与架构 §1.3 链**逐字一致**。
- internal_rag 四节点 `receive_validate → retrieve_topk → generate_conclusion → writeback_tool` 与架构 §1.4 链**逐字一致**。
- supervisor 主控图入口与架构 §1.2 一致；验收「图骨架断言」将六/四节点逐字一致性 + 全 stub 列为可勾选项。
- 冒烟断言②「Flask 进程路由清单无任何 `/api/*` 路由」与架构 §0 拓扑钉死项一致。

### 4. 验收可勾选 · failure_paths 四列 · 思考轮与元信息 ✅
- **验收 10 行全部可命令化断言**：钉版断言（11 项依赖 `==` 钉死 + 干净 venv 可复现）、目录断言、图骨架断言、env 断言、配置断言、忽略断言、冒烟三断言（pytest 自动化：health 200 / Flask 首屏 200 且无 `/api/*` 路由 / supervisor 图 Mock `{task_id, url}` 空跑）、README 照抄验证——冒烟三断言可执行，且 R4 明确「零外部网络依赖，离线可跑」。
- **failure_paths**：6 行四列（触发→行为→可重试→用户可见）齐备；首行为模板默认流程闸行（拒开工）；依赖冲突/playwright 下载/端口占用/stub 图空跑失败均为脚手架特有风险，与 SPEC failure_paths 不矛盾（SPEC 六条属业务运行时，本 task 为工程底座期）。
- **思考轮**：R0–R5 六槽全部填实无空槽；R2 依赖管理分叉（poetry/uv/pip+requirements.txt）三方案对比含推荐与双弃选理由，与人决 D3（V1 仅本地运行）自洽；控制表 early_stop=no、reason 合法、residual_risks 三条具体（轮子可用性 / LangGraph API 漂移 / 下游反向依赖回填）。
- **元信息**：必填字段无占位；`graph_delta=none` 与 `wiki_delta=none` 均有 note 理由；`invoke_retention_profile=default` 已选定；`semi_auto=false`；`required_invoke_hats=10,30,40`（不含 20，本轮无需 invoke 快照落盘）；`wiki_promotion=none`；`close_pr_policy=required`。
- **test_strategy=required 与本仓无测试制品的关系已说清**：R4 明示「脚手架冒烟测试即真实测试制品（pytest 三断言）……顺带满足 kit D5 探测对测试入口的要求」，验收首行亦注明「本仓尚无 CI workflow；30 须随实现落盘 `pytest tests -q` 等效测试入口」——本 task 交付 `tests/` 即全仓首个测试制品，逻辑闭环。

### 5. 依赖相对路径真实存在 ✅
- 上位真值 SPEC ✅、架构文档 ✅；下游三 task（`task_web_acquisition_subgraph.md` / `task_internal_rag_subgraph.md` / `task_web_console_mvp.md`）✅ 均真实存在。
- 反向依赖回填（三下游 task 依赖节引用本文件）已声明「本 task 不改那三个文件，由 00 统一回填」，且 R5 与 residual_risks ③ 双重提醒 00，归属清晰，非本 task 阻塞。
- 必读列表 `AGENTS.md` / `docs/meta/` / `docs/standards/` 当前缺失，task 均标注「若存在」，豁免合理。
- `chain_prompt` 指向 `docs/harness/prompts/30-execute-code.md` + `40-self-check.md`，两文件**均真实存在**，并自注「本仓未嵌入 PROMPT_cursor_task_chain_serial_v1.md，与三个 MVP task 同口径」——优于下游三 task 的同类标注（其指向文件尚不存在），无 30 派发前置缺口。

### 行为变更类 checklist（K7）
- 本 task 为绿地新建（仓内无既有实现/旧测/CI），非行为变更类，「旧测 grep 影响面」项不适用。

## 非阻塞观察（不退回 · 供 00/维护者知悉）

- **O1**：范围第 1 条允许「`pyproject.toml` 或 `requirements.txt` 二者择一」，R2 推荐 pip + requirements.txt 且留了「30 施工期可等价替换 pyproject.toml」的活口（须保持 `==` 钉版与单命令安装不变并留痕）——裁量已约束，不阻塞；维护者签闸时可一并知悉。
- **O2**：验收「README 照抄验证」为唯一人工行，R4 已声明其为「交付前最后一道」，与 `test_strategy=required` 的自动化主体不冲突；提醒 40 自检时确认该人工行已被真实执行并留痕。

## 阻塞项

**无内容阻塞。**

## 维护者签闸（20 后 · 30 前）

- [ ] 已读 R1 审查结论
- [ ] 在 task 人工闸表将 HG-AUDIT-R1 改为 approved（维护者 · 日期）
- [ ] commit task 文档或确认已签
- [ ] 再下发 Harness 30 Prompt

30 Agent 将以 task 表为准；pending 时必须拒开工（见 TEMPLATE_30_gate_stop.md）。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R1：内容 PASS（零阻塞 · 非阻塞观察 2 条）；机械闸 lint exit 0 / gate-check exit 2（预期）；建议人签 HG-AUDIT-R1 |
