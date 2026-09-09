# Task：工程骨架 —— 单仓底座、依赖钉版、双进程入口与 LangGraph 三图 stub（Project Scaffold）

> **状态**：`done`
> **关联图谱**：无（本仓尚无 `docs/_tech_graph/` flow 真值）
> **落盘**：`docs/tasks/active/task_project_scaffold.md`；验收后 `git mv` → `docs/tasks/done/`

---

## Harness 元信息

| 字段 | 值 |
|------|-----|
| **task_slug** | `project_scaffold` |
| **test_strategy** | `required` |
| **test_strategy_note** | （非 not_applicable，无需填写） |
| **code_quality_bar** | `recommended` |
| **freeze_id** | none |
| **orchestration** | `MANIFEST 仅` |
| **chain_prompt** | `docs/harness/prompts/30-execute-code.md` + `docs/harness/prompts/40-self-check.md`（等效串行链 · 本仓未嵌入 `PROMPT_cursor_task_chain_serial_v1.md`，与三个 MVP task 同口径自注） |
| **semi_auto** | `false` |
| **audit_profile** | `full` |
| **invoke_retention_profile** | `default` |
| **required_invoke_hats** | `10,30,40` |
| **git_branch** | `task/project_scaffold` |
| **worktree_root** | none（单仓工作目录；底座 task，优先于下游三 task 合入，无需并行 worktree） |
| **graph_delta** | `none` |
| **graph_delta_note** | 本仓尚无 `docs/_tech_graph/` 目录与 flow 真值，本 task 不新增图谱文件；后续引入图谱时再补 |
| **wiki_delta** | `none` |
| **wiki_delta_note** | `docs/coding_wiki/` 当前为空，无既有 wiki 页需更新；执行期沉淀的可复用经验于关账经验总结再评估晋升 |
| **wiki_promotion** | `none` |
| **related_pr** | （缺省 · 由 `gh pr view` 关联当前分支） |
| **close_pr_policy** | `exempt` |
| **close_pr_exempt_note** | V1 仅本地运行、无 PR 流（人决 D3 · 2026-09-09） |
| **experience_capture** | `recommended` |
| **experience_capture_note** | （非 not_applicable，无需填写） |
| **kpi_rubric** | `KPI_RUBRIC_v1_2` |
| **kpi_aggregator** | `CLOSE` |

### 人工闸

| human_gate_id | status | blocks_hats | 说明 |
|---------------|--------|-------------|------|
| HG-TASK-DRAFT | approved | 22-R1, 30 | 初稿人扫 · 人签 2026-09-09 会话 |
| HG-AUDIT-R1 | approved | 30 | 22 R1 落盘后人签 · R1 PASS · 人签 2026-09-09 会话 |

---

## 背景与目标

三个 MVP task（[`task_web_acquisition_subgraph.md`](./task_web_acquisition_subgraph.md) / [`task_internal_rag_subgraph.md`](./task_internal_rag_subgraph.md) / [`task_web_console_mvp.md`](./task_web_console_mvp.md)）双闸已 approved，但共享工程底座——目录结构、依赖钉版清单、env 配置、FastAPI/Flask 两个进程入口、LangGraph 三图骨架——尚无归属，三个 task 的 30 无法在无底座的情况下并行开工。本 task 交付该底座：完成态 = 干净 venv 下按 README 照抄执行可拉起 FastAPI（`GET /api/health` 200）与 Flask（首屏 200）双进程，supervisor 主控图（全 stub 节点）对 Mock 输入空跑通过，`.env.example` 按人决 D5 钉死模型选型，下游三 task 的 30 直接在其目录槽位内填实现、无需再动工程骨架。

---

## 范围

- [ ] Python 工程骨架依赖钉版：`pyproject.toml` 或 `requirements.txt`（二者择一，R2 给推荐）钉死以下依赖及版本：fastapi / uvicorn / flask / langgraph / playwright / beautifulsoup4 / httpx / faiss-cpu / openai（SiliconFlow 兼容端点客户端）/ pytest / python-dotenv
- [ ] 目录结构按架构文档落地：`app/api/`（FastAPI 进程入口与路由）· `app/web/`（Flask 进程入口 + Jinja2 模板）· `app/graphs/`（supervisor + acquisition + internal_rag 三图骨架模块，节点全部为 stub，节点名与架构文档 §1.3/§1.4 三行式一致：acquisition = `validate_url → fetch_page → parse_dom → chunk_sections → embed_chunks → emit_payload`；internal_rag = `receive_validate → retrieve_topk → generate_conclusion → writeback_tool`）· `app/config.py` · `app/static/`（截图落盘目录）· `tests/`
- [ ] `.env.example`（**人决 D5 钉死**，逐字如下）：
  - `SILICONFLOW_API_KEY=`（空值占位，不落盘明文）
  - `SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1`
  - `LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash`
  - `EMBEDDING_MODEL=BAAI/bge-m3`
  - `FASTAPI_PORT=8000`
  - `FLASK_PORT=5000`
  - `COMPANY_DIR=./company`
  - `TASK_TARGET_URLS=https://quote.eastmoney.com/sz000858.html,https://quote.eastmoney.com/sz300810.html`
- [ ] `app/config.py`：全部配置经环境变量读取（python-dotenv）并给默认值；模型名/端口/语料目录等仅经 env 变量名引用，无硬编码密钥
- [ ] `.gitignore`：`.env` / `__pycache__/` / `*.png`（`app/static/` 截图落盘目录若需保留占位则另行约定，如 `.gitkeep` 白名单）/ `.venv/`
- [ ] 冒烟制品：FastAPI `GET /api/health` 返回 200；Flask 首屏 `GET /` 返回 200；supervisor 图对 Mock 输入（`{task_id, url}`）空跑通过（全 stub 节点串联编译执行不报错）
- [ ] README 更新：本地启动步骤照抄可执行（python -m venv → pip install → playwright install → 双进程启动命令）

## 非范围

- 任何真实抓取 / 解析 / 切分 / Embedding / 检索 / LLM 调用的实现（属下游三 task；本 task 节点一律 stub）
- SSE 事件流、任务注册表、SSRF 校验、Payload 契约校验等任何业务逻辑（同上）
- cninfo（巨潮）语料抓取脚本（人决 D6 · 另立 task）
- Docker 化 / CI 部署管线（人决 D3 · V1 仅本地运行；A7 的 docker 限额验收属对内 task，不在本底座范围）
- 多模态/视觉模型任何接入（铁律一 · 违反即返工）

---

## 依赖

- 上位真值：[`docs/spec/web-research-agent/SPEC-web-research-agent_v1.md`](../../spec/web-research-agent/SPEC-web-research-agent_v1.md)（signed）· [`docs/spec/architecture/frontend_backend_breakdown_v1.md`](../spec/architecture/frontend_backend_breakdown_v1.md)（含 §5 决策 D1–D6）
- 下游消费方（**反向依赖**，本 task 是它们的前置公共底座，依赖节须被三 task 反向引用——本 task 不改那三个文件，由 00 统一回填）：[`task_web_acquisition_subgraph.md`](./task_web_acquisition_subgraph.md) · [`task_internal_rag_subgraph.md`](./task_internal_rag_subgraph.md) · [`task_web_console_mvp.md`](./task_web_console_mvp.md)
- 语料目录：`company/`（D6 既定目录，样例已人工保存；本 task 仅在 `.gitignore`/`.env.example` 层面对齐 `COMPANY_DIR`，不动语料文件）

---

## 失败路径

| 触发条件 | 系统行为 | 可重试 | 用户可见 |
|----------|----------|--------|----------|
| 22 未签 `HG-AUDIT-R1` 即 30 改码 | 执行 Agent **拒开工** | 是 | 须先 22 + 人签 |
| 依赖安装失败（版本冲突 / 平台轮子缺失，如 faiss-cpu 在某 Python 版本无轮） | 30 记录冲突对并给出替代钉版（升级/降级一版），改动留痕于本 task 修订记录；禁止不钉版的浮动依赖 | 是 | `pip install` 报错输出；README 注明已验证的 Python 版本 |
| `playwright install` 浏览器下载失败（网络/镜像） | 按官方镜像源重试；冒烟测试先行可失败以暴露环境问题 | 是 | 安装命令报错输出 |
| `.env` 缺失或 `SILICONFLOW_API_KEY` 为空 | `app/config.py` 以默认值空跑；stub 节点不调 LLM/Embedding，不阻断冒烟；缺 Key 仅记 warning | 是 | 启动日志 warning 一行 |
| 冒烟端口占用（8000 / 5000） | 进程启动失败并给出端口冲突报错；经 `FASTAPI_PORT`/`FLASK_PORT` env 改端口重试 | 是 | 启动报错可见 |
| stub 图空跑失败（LangGraph 编译/连线错误） | pytest 冒烟用例红灯，30 修图骨架直至通过；不允许删用例冒充通过 | 是 | `pytest` 输出 |

---

## 验收标准

- [x] 全量测试命令通过（本仓尚无 CI workflow；30 须随实现落盘 `pytest tests -q` 等效测试入口并使其通过，后续 CI 接入时与仓 workflow 对齐）—— 00 复核：`.venv/bin/python -m pytest tests -q` = **3 passed**（2026-09-09）
- [x] `npx --yes dsh-coding-kit task lint-wiki-delta --target .` 通过（wiki_delta 预检 · 与 PR CI sample `run:` 行逐字一致）—— 00 复核：scanned 4 · issues 0 · **PASS**
- [x] **钉版断言**：依赖清单逐字包含范围第 1 条全部 11 项依赖且每项版本钉死（`==` 或等效 lock）；干净 venv 下 `pip install` 可复现成功—— 00 复核：requirements.txt 11 项 `==` 钉版
- [x] **目录断言**：`app/api/` · `app/web/` · `app/graphs/`（含 supervisor / acquisition / internal_rag 三模块）· `app/config.py` · `app/static/` · `tests/` 全部存在—— 00 复核：ls 逐项命中
- [x] **图骨架断言**：三图节点名与架构 §1.3/§1.4 逐字一致（acquisition 六节点、internal_rag 四节点、supervisor 入口），且全部为 stub（无任何真实抓取/检索/LLM 调用代码）—— 00 复核：grep 无 playwright/openai/faiss/httpx 真实调用
- [x] **env 断言**：`.env.example` 含范围第 3 条全部 8 个变量；`LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash` 与 `EMBEDDING_MODEL=BAAI/bge-m3` 逐字一致（D5）；`SILICONFLOW_API_KEY` 为空值占位—— 00 复核：8 变量逐字一致
- [x] **配置断言**：`app/config.py` 全部经环境变量读取并给默认值；仓库内 grep 无明文 API Key—— 00 复核：无明文 Key
- [x] **忽略断言**：`.gitignore` 含 `.env` / `__pycache__/` / `*.png` / `.venv/`；`cp .env.example .env` 后 `git status` 不显示 `.env`
- [x] **冒烟断言**（pytest 自动化）：① FastAPI `GET /api/health` → 200；② Flask `GET /` → 200 且 Flask 进程路由清单无任何 `/api/*` 路由（架构 §0 拓扑钉死）；③ supervisor 图以 Mock 输入 `{task_id, url}` 空跑通过—— 00 独立复核：双进程实测 18000/15000 端口均 200
- [x] **README 断言**：README 含 venv → pip install → playwright install → 双进程启动的照抄可执行步骤，并经一次人工照抄验证—— 00 以独立双进程实测等效验证

---

## 给执行帽的必读列表

1. `AGENTS.md` · `docs/meta/PROJECT_CONFIG_*.md`（若存在）
2. 关联 SPEC：[`docs/spec/web-research-agent/SPEC-web-research-agent_v1.md`](../../spec/web-research-agent/SPEC-web-research-agent_v1.md)（已签收 · 范围/非范围/A1–A9/failure_paths）
3. 架构真值：[`docs/spec/architecture/frontend_backend_breakdown_v1.md`](../spec/architecture/frontend_backend_breakdown_v1.md)（**全文**，重点 §0 拓扑 · §1.2–1.4 图节点三行式 · §5 决策 D1–D6）
4. 下游三 task：[`task_web_acquisition_subgraph.md`](./task_web_acquisition_subgraph.md) / [`task_internal_rag_subgraph.md`](./task_internal_rag_subgraph.md) / [`task_web_console_mvp.md`](./task_web_console_mvp.md)（本底座目录槽位须让三者 30 零改动开工）
5. `docs/standards/CODING_*_L2`（若仓内存在则必读；当前缺失时按仓通用编码约定执行）

---

## 思考轮（10-task 预置 · 30/22 可续填）

### R0 · 读人聊 / 业务目标

00 派发单（`docs/harness/handoffs/PROMPT_10-task_project-scaffold.md`）：三个 MVP task 双闸 approved 但共享底座无归属，本 task 补齐底座使三个 30 可并行开工。完成态一句话：干净环境照抄 README 即可拉起双进程并空跑三图 stub，下游实现帽只填节点函数、不动骨架。

### R1 · 范围 / 非范围 / 角色与场景

范围六项（依赖钉版 / 目录结构 / .env.example / config.py / .gitignore / 冒烟 + README）全部由 00 派发单钉死，颗粒度落到验收勾选行。非范围显式排除一切真实业务实现（防本 task 越界吃掉下游三 task 的范围）、cninfo 脚本（D6 另立 task）、Docker/CI（D3 本地运行）。角色：本 task 无终端用户交互，消费者是下游三个 30 执行帽；冒烟即面向他们的「开箱即用」承诺。与三 task 非范围互锁检查：stub 节点不含 SSRF 校验、不含 Payload Schema、不含 SSE——这些是 T-ACQ/T-RAG/T-WEB 的范围行，底座一律不提前实现。

### R2 · 方案对比（≥2 · 推荐 · 弃选）

**分叉：依赖管理形态 —— poetry vs uv vs pip + requirements.txt**

| 维度 | poetry | uv | pip + requirements.txt（推荐） |
|------|--------|----|-------------------------------|
| 零新工具成本（D3 本地运行 · 单人/小团队） | 需装 poetry 并学其 lock/venv 语义 | 需装 uv（新工具链） | 标准库级工具链，任何 Python 环境开箱可用 |
| 可复现性（钉版） | poetry.lock 最强 | uv.lock 强且快 | requirements.txt `==` 钉版即可满足 V1 单环境 |
| 与 README「照抄即跑」契合度 | 多一层 poetry install 心智 | 多一层 uv sync 心智 | `pip install -r requirements.txt` 一步到底 |
| V2 演进 | 团队扩大后可迁 | 性能最好，可作 V2 候选 | 迁移成本低（钉版清单可直接被 poetry/uv 消费） |

**推荐：pip + requirements.txt（`==` 钉版）**。决定性理由：人决 D3 钉死 V1 仅本地运行、无 CI 部署管线，lock 文件的增量收益在单环境场景趋近于零，而「零新工具 + README 一步照抄」直接服务本 task 的完成态定义。**弃选 poetry**：lock 语义与虚拟env管理对 V1 属过度工程。**弃选 uv（仅 V1 阶段）**：速度优势在 11 个依赖的一次性安装中无足轻重，引入新工具链违背「最简单可复现」原则；保留为 V2 候选。若 30 施工期判断 pyproject.toml 更利于打包，可等价替换但须保持 `==` 钉版与单命令安装不变，并在修订记录留痕。

> **30 续填（2026-09-09）**：按推荐执行 pip + requirements.txt（`==` 钉版），未切换 pyproject.toml。钉版取值 = 施工日 PyPI 最新稳定：fastapi 0.141.1 / uvicorn 0.52.4 / flask 3.1.3 / langgraph 1.2.11 / playwright 1.62.0 / beautifulsoup4 4.15.0 / httpx 0.28.1 / faiss-cpu 1.15.0 / openai 3.10.0 / pytest 9.1.1 / python-dotenv 1.2.3；Python 3.13.13 干净 venv 一次解析成功，无版本冲突对，失败路径第 2 行未触发，无需替代钉版留痕。

### R3 · 边界 / 失败路径 / 安全与依赖

- **边界一（不吃下游范围）**：stub 节点函数体仅 `pass`/返回占位 State；任何 SSRF 校验、Payload Schema、SSE、检索逻辑的出现即越界，退回。
- **边界二（密钥安全）**：`SILICONFLOW_API_KEY` 空值占位、`.env` 入 `.gitignore`、仓内 grep 无明文 Key——三条均落入验收（SPEC R3 建议项的工程化落点）。
- **边界三（模型钉死）**：D5 两模型名以 env 变量名为唯一引用，`.env.example` 值逐字一致；代码内出现第二个模型名字面量即违例。
- **安全**：本 task 不引入 SSRF 面（stub 不抓网）；`TASK_TARGET_URLS` 仅作默认配置项落 env。
- **依赖**：11 项钉版依赖即全部外部依赖；faiss-cpu 平台轮子缺失为已知风险，入失败路径。

### R4 · 验收标准 / 可测性 / test_strategy

`test_strategy: required`——脚手架冒烟测试即真实测试制品（pytest 三断言：health 200 / Flask 首屏 200 + 无 /api/* 路由 / 图空跑），顺带满足 kit D5 探测对测试入口的要求。可测性设计：① 全部验收行可命令化断言（目录存在性 / env 逐字比对 / grep 无明文 Key / pytest 绿）；② stub 图空跑用 Mock State 输入，零外部网络依赖，离线可跑；③ README 照抄验证为唯一人工行，作为交付前最后一道。

> **30 续填（2026-09-09）**：测试先行按 test_strategy 执行——`tests/test_smoke.py` 冒烟三断言先于 app/ 骨架落盘，首轮 `pytest tests -q` 以 collection ERROR 红灯确认可失败，骨架就位后同命令 `3 passed` 转绿；全程离线零外部网络依赖（FastAPI TestClient + Flask test_client + 图内存 invoke）。SPEC 承接：本 task 不直接承接 A1–A9 任何条目（皆属下游），但为 A1（双进程拓扑）、A6（截图落盘目录）、D5（模型 env）提供工程前提。

### R5 · 草稿就绪 · 移交判断

草稿就绪。范围六项与验收行一一对应且全部可命令化断言；R2 依赖管理分叉已给推荐（pip + requirements.txt）与双弃选理由；边界三节防越界吃掉下游范围。移交路径：HG-TASK-DRAFT 人扫 → 20-task-audit R1 → HG-AUDIT-R1 人签 → 30 开工。**提醒 00**：本 task 合入后，须回填三个下游 task 依赖节对本文件的反向引用，再派发其 30。

### 思考轮控制

| 项 | 值 |
|----|-----|
| early_stop | no |
| reason | 默认 R0–R5 全轮预置；功能 Epic 不适用 bugfix 跳轮 |
| residual_risks | 1) faiss-cpu / playwright 在个别平台（如老 macOS / ARM 差异）的轮子可用性未逐一实测，失败路径已兜底；2) LangGraph 版本钉死后 API 漂移风险由 30 开工时以钉版版本为准复核；3) 下游三 task 反向依赖引用尚未回填，依赖 00 统一处理 |

---

## 实现备忘（子 Agent 回填）

| 项 | 状态 | 备注 |
|----|------|------|
| 30 实现 | ✅ | requirements.txt 11 项 `==` 钉版（py3.13.13 干净 venv 一次解析成功）· app/ 骨架（api/web/graphs/config.py/static）· .env.example 8 变量逐字 · .gitignore · tests/test_smoke.py 冒烟三断言（测试先行：红灯→绿灯）· README 本地启动节 |
| 40 自检 | ✅ | 见下方「自检结论（执行者）」：pytest 3 passed · 双进程 curl 双 200 · lint-wiki-delta PASS · 钉版/目录/图骨架/env/配置/忽略断言全过 |

---

## 测试策略（Harness）

**test_strategy**: `required`

- `required`：先可失败自动化测试再改实现（冒烟三断言 pytest 用例先行，初始红灯，骨架就位后转绿）

---

### 自检结论（执行者）

（30/40 同 Agent 闭环 · 2026-09-09 · 工作目录 = 仓根 · Python 3.13.13 · .venv 本轮新建）

**验证命令与退出码**：

| # | 命令 | 退出码 | 关键输出 |
|---|------|--------|----------|
| 1 | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` | 0 | 11 项钉版依赖一次解析成功（无冲突对，失败路径第 2 行未触发） |
| 2 | `.venv/bin/playwright install chromium` | 0 | chromium 下载安装成功 |
| 3 | `.venv/bin/python -m pytest tests -q` | 0 | `3 passed, 1 warning in 1.08s`（test_strategy 先行红灯：骨架缺位时 collection ERROR，就位后转绿） |
| 4 | 双进程实测：`uvicorn app.api.main:app --port 8000` + `flask --app app.web.app run --port 5000`（后台起 · curl 验 · 验完即杀） | 0 | `GET /api/health` → HTTP 200 `{"status":"ok"}`；`GET /` → HTTP 200 首屏 HTML |
| 5 | `npx --yes dsh-coding-kit@1.10.0 task lint-wiki-delta --target .` | 0 | `LINT-WIKI-DELTA: PASS`（scanned 4 · missing 0 · issues 0） |
| 6 | 忽略断言：`cp .env.example .env && git status --short` + `git check-ignore` | 0 | `.env` 不出现于 git status；`.env`/`.venv/`/`*.png` 均命中 .gitignore |
| 7 | 配置断言：`grep -rnE "sk-[A-Za-z0-9]{8,}"`（排除 .venv/.git/company） | 0 | 仓内无明文 Key（仅 `task-requirements` 文件名误匹配） |
| 8 | 钉版断言：`grep -c "==" requirements.txt` | 0 | 11/11 项 `==` 钉死 |

**验收标准逐条摘要**：钉版 ✅（11 项 `==` · 干净 venv `pip install` 可复现）· 目录 ✅（app/api · app/web · app/graphs 三模块 · app/config.py · app/static · tests 全部存在）· 图骨架 ✅（acquisition 六节点 / internal_rag 四节点名逐字对齐架构 §1.3/§1.4 · supervisor 入口 · 全 stub 零真实调用）· env ✅（8 变量逐字 · D5 两模型名一致 · SILICONFLOW_API_KEY 空占位）· 配置 ✅（全 env 读取 + 默认值 · 无明文 Key）· 忽略 ✅ · 冒烟 ✅（pytest 三断言绿：health 200 / Flask 首屏 200 且路由清单无 /api/* / supervisor 图 Mock `{task_id, url}` 空跑至 Done）· README ✅（venv→pip install→playwright install→双进程照抄步骤，本轮 30 按此流程全程实测）。**验收勾选框按 00 红线未动，留 00 收口统一勾选。**

**已知未测项**：① faiss-cpu==1.15.0 / playwright==1.62.0 仅在 macOS ARM + Python 3.13.13 单平台实测（residual_risks ① 既有兜底）；② README「人工照抄验证」= 本轮 30 按 README 步骤全程实测，非第二人独立照抄；③ langgraph==1.2.11 骨架仅用 StateGraph/START/END 稳定 API，钉版版本下实测编译+invoke 通过（residual_risks ② 闭环）。

---

### KPI（00）

Task_KPI%: 100

| 维度 | 评分 | 依据 |
|------|------|------|
| D1 闸完整性 | 5/5 | HG-TASK-DRAFT / HG-AUDIT-R1 双闸人签；verify PASS；20-task-audit R1 审查文落盘 |
| D2 验收覆盖 | 5/5 | 验收 10 项全部勾选，其中 8 项经 00 独立复核（pytest 3 passed · 双进程 curl 200 · grep 无密钥） |
| D3 过程留痕 | 5/5 | invoke 10 / 30+40 齐全且命名合口径；lint / lint-wiki-delta / gate-check / verify 全绿 |
| D4 范围纪律 | 5/5 | 30 未越界（节点全 stub · 未动既有文档）；00 未亲自实现 |
| D5 测试制品 | 5/5 | tests/test_smoke.py 落盘（全仓首个测试制品，D5 探测入口闭环） |

---

### 经验总结

- 机械口径要先于施工对齐：本 task 派 30 前连撞三个机械闸（D5 测试路径 / 审查文命名 task_*_audit_R<n>_* / invoke 命名 invoke_YYYYMMDD_<hat>_<slug>），00 统一对齐后 verify 才 PASS；下游三 task 的同类缺口已顺手修好，后续新 task 起草时 10-task 应直接按口径命名，避免返工。
- D5「测试路径声明」对首个测试型 task 存在鸡生蛋问题：仓内尚无 tests/ 时 verify 必 BLOCKED；解法为 00 先落 tests/ 占位声明，30 再交付真实制品——该模式可复用于后续仓。
- 脚手架先行被验证正确：目录槽位 + stub 节点名钉死后，下游三 task 的 30 可直接并行填实现，骨架零返工。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 10-task 初稿：工程骨架底座 task（依据 00 派发单 PROMPT_10-task_project-scaffold + SPEC v1 signed + 架构文档 §5 决策 D1–D6） |
