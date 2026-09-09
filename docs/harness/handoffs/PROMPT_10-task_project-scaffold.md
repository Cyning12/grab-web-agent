# 下一棒 Prompt · hat 10-task（task_project_scaffold 起草）

> 00 落盘于 2026-09-09。子 Agent 整段复制执行。

## 身份与纪律

你是 **10-task**。开工先调用 skill 工具加载 `harness-10-task`（若不可用，改读 `.dsh/skills/harness-10-task/SKILL.md`）。只起草 task，不写实现代码，不签人工闸。

## 输入（必读）

1. `docs/spec/architecture/frontend_backend_breakdown_v1.md`（架构真值 · 含 §5 决策记录 D1–D6）
2. `docs/spec/SPEC-web-research-agent_v1.md`（signed）
3. `docs/harness/templates/TASK_TEMPLATE.md`（结构真值）
4. `docs/tasks/active/` 现有三 task（本 task 是它们的**前置公共底座**，依赖节须被三 task 反向引用——你只写本 task 文件，不改那三个文件，但在回报中提醒 00 需要补反向依赖）

## task 内容要求（task_slug: `project_scaffold`）

**背景**：三个 MVP task 双闸已 approved，但共享工程底座（目录结构 / 依赖清单 / env 配置 / 两个进程入口 / LangGraph 图骨架）尚无归属。本 task 交付该底座，使三个 task 的 30 可以并行开工。

**范围**（颗粒度按此写验收）：
1. Python 工程骨架：`pyproject.toml`（或 requirements.txt）钉依赖：fastapi / uvicorn / flask / langgraph / playwright / beautifulsoup4 / httpx / faiss-cpu / openai（SiliconFlow 兼容端点）/ pytest / python-dotenv
2. 目录结构按架构文档：`app/api/`（FastAPI）· `app/web/`（Flask 模板）· `app/graphs/`（supervisor + acquisition + internal_rag 三图骨架，节点为 stub，节点名与架构文档 §1.3/§1.4 三行式一致）· `app/config.py` · `app/static/` · `tests/`
3. `.env.example`（**人决 D5 钉死**）：`SILICONFLOW_API_KEY=`（空值占位）· `SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1` · `LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash` · `EMBEDDING_MODEL=BAAI/bge-m3` · `FASTAPI_PORT=8000` · `FLASK_PORT=5000` · `COMPANY_DIR=./company` · `TASK_TARGET_URLS=https://quote.eastmoney.com/sz000858.html,https://quote.eastmoney.com/sz300810.html`；`app/config.py` 全部经环境变量读取并给默认值
4. `.gitignore`：`.env` / `__pycache__/` / `*.png`（截图落盘目录除外则另行约定）/ `.venv/`
5. 冒烟：FastAPI `GET /api/health` 返回 200；Flask 首屏 200；supervisor 图可对 Mock 输入空跑通过（全 stub 节点）
6. README 更新：本地启动步骤（venv → pip install → playwright install → 双进程启动）

**非范围**：任何真实抓取/解析/检索/LLM 调用实现（属三个下游 task）；cninfo 抓取脚本（人决 D6，另立 task）；Docker 化。

**元信息钉死**：`test_strategy=required`（脚手架冒烟测试即真实测试制品，顺带满足 kit D5 探测）；`code_quality_bar=recommended`；`wiki_delta=none`+note；`graph_delta=none`+note；`invoke_retention_profile=default`；`chain_prompt` 填等效链：`docs/harness/prompts/30-execute-code.md` + `docs/harness/prompts/40-self-check.md`（本仓未嵌入 Cursor 串行链模板，00 已在三 task 自注同口径）；`orchestration=MANIFEST 仅`；git_branch=`task/project_scaffold`；人工闸 HG-TASK-DRAFT / HG-AUDIT-R1 均 pending。

**R 轮**：R0 + R1–R5 槽 + 控制表预置；R2 至少对比「poetry vs uv vs pip+requirements」依赖管理分叉给推荐（本地运行 D3 下推荐最简单可复现者）。

## 交付

`docs/tasks/active/task_project_scaffold.md`，跑 `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 task lint --file docs/tasks/active/task_project_scaffold.md` 必须 PASS（不 PASS 修到 PASS）。invoke 留档落 `docs/harness/invokes/by-task/project_scaffold/invoke_10_project_scaffold_20260909.md`。

## 回报（≤10 行）

task 路径 · lint 结果 · 依赖三 task 反向引用提醒 · 建议下一棒 · 阻塞项
