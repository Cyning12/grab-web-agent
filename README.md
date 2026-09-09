# grab_web_agent · 智能网页调研 Agent

企业级竞品/行业调研 Agent：统一 Web 控制台输入目标 URL → 自动采集分析 → 结构化结论回填当前页面并写入内部系统。

## 文档结构（dsh-coding-kit Harness 布局）

| 路径 | 内容 |
|------|------|
| `docs/spec/_source/PRD_web_research_agent_v2.md` | 产品技术大纲 V2.0 原文（需求真值） |
| `docs/spec/SPEC-web-research-agent_v1.md` | 需求规格（10-spec 回填 · HG-SPEC-SIGNOFF 人签） |
| `docs/tasks/active/` | 进行中 task（10-task 起草 · 20-task-audit 审查） |
| `docs/tasks/done/` | 已关账 task |
| `docs/harness/prompts/` | Harness 帽子纪律（kit `sync prompts` 嵌入真值） |
| `docs/harness/templates/TASK_TEMPLATE.md` | task 文件模板 |
| `docs/harness/handoffs/` | 00 落盘的下一棒 Prompt |
| `docs/harness/reviews/` | 20 审查文落盘 |
| `docs/harness/invokes/by-task/` | 各帽 invoke 留档 |
| `.dsh/skills/` | kit 过程技能（DSH runtime 自动扫描） |
| `.cyning-harness/manifest.json` | kit 安装清单（dsh-coding-kit@1.10.0 · harness-only） |

## 过程纪律（摘要）

- 编排：00 只编排收口，不亲自实现；10 → 20 → 30/40 → 50 + CLOSE 全链派子 Agent。
- 闸：`npx --yes dsh-coding-kit@1.10.0 verify --task <task.md>` PASS 才能进 30。
- 人签：HG-SPEC-SIGNOFF / HG-TASK-DRAFT / HG-AUDIT-R1 仅人类可签。

## 技术栈（PRD §7）

FastAPI · LangGraph · Playwright · BeautifulSoup · FAISS(MVP)/Qdrant(生产) · Streamlit 或 Flask+Jinja2(MVP 前端)
## 本地启动（V1 仅本地运行 · 人决 D3）

已验证环境：Python 3.13（`python3 --version` ≥ 3.11 即可；依赖钉版见 `requirements.txt`）。

```bash
# 1. 创建虚拟环境并安装依赖（pip + requirements.txt · R2 已决，全部 == 钉版）
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. 安装 Playwright 浏览器（仅 chromium）
.venv/bin/playwright install chromium

# 3. 配置环境变量（密钥空值占位即可空跑，stub 阶段不调 LLM/Embedding）
cp .env.example .env

# 4. 双进程启动（架构 §0 拓扑：Flask 仅渲染模板，全部 API 在 FastAPI 进程）
# 终端 A · FastAPI（API 进程，默认 8000 端口，可用 FASTAPI_PORT 覆盖）
.venv/bin/uvicorn app.api.main:app --port ${FASTAPI_PORT:-8000}
# 终端 B · Flask（渲染进程，默认 5000 端口，可用 FLASK_PORT 覆盖）
.venv/bin/flask --app app.web.app run --port ${FLASK_PORT:-5000}
```

冒烟验证：

```bash
curl -i http://127.0.0.1:8000/api/health   # → 200 {"status":"ok"}
curl -i http://127.0.0.1:5000/             # → 200 首屏 HTML
.venv/bin/python -m pytest tests -q        # → 3 passed（health 200 / 首屏 200 / 图空跑）
```

## 工程结构（task_project_scaffold 底座）

| 路径 | 内容 |
|------|------|
| `app/api/` | FastAPI 进程入口与路由（骨架：`GET /api/health`） |
| `app/web/` | Flask 进程入口 + Jinja2 首屏模板（无任何 /api/* 路由） |
| `app/graphs/` | LangGraph 三图骨架（supervisor + acquisition + internal_rag，节点全 stub） |
| `app/config.py` | 全 env 配置读取（python-dotenv）+ 默认值，无硬编码密钥 |
| `app/static/` | 截图落盘目录（`.gitkeep` 占位，`*.png` 已 gitignore） |
| `tests/` | 冒烟测试（task_project_scaffold 验收三断言） |
