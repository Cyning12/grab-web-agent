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
.venv/bin/python -m pytest tests -q        # → 104 passed（scaffold + 双子图 + 控制台联调）
```

打开 `http://127.0.0.1:5000/`（管理员视角 `?role=admin`），输入目标 URL 点「开始调研」即可看到三区块渐进回填与底部工单回执。

演示目标 URL（腾讯自选股 · 人决 D8 · 默认 `TASK_TARGET_URLS` 同款）：

- `https://gu.qq.com/sz000858/gp`（五粮液）
- `https://gu.qq.com/sz300810/gp`（中科海讯）

> 人决 D8（2026-09-09）：东财对本机 IP 持续下发滑块验证，默认目标切腾讯 gu.qq.com（用户实测暂无反爬）；东财旧链仍可手动输入但不保证成功率（遗留痕见架构 §5 D4/D7 与下方已知事项 2）。

### 已知事项（真机 E2E 实测踩坑 · 2026-09-09）

1. **NO_PROXY 含 `[::1]` 会导致 LLM/Embedding 调用炸 `InvalidURL`**（httpx2 解析 bracketed IPv6 缺陷）。启动服务前净化：
   ```bash
   export NO_PROXY=localhost,127.0.0.1,::1   # 去掉 [::1] 项
   ```
2. 东财**标准**个股页价格为 JS 异步渲染且可能触发「拖动下方滑块完成拼图」滑块验证（软反爬）。默认目标已切 concept 极速版链接（干扰少）；fetch 节点已加渲染完成确认（networkidle 优先 / domcontentloaded 兜底 + 非占位文本等待，`FETCH_RENDER_TIMEOUT_MS` 可调），检出滑块覆盖层即 ANTI_BOT 终态不解析半成品；仍渲染不出有效内容时结论如实输出 `insufficient_info=true`（铁律一：不降级多模态硬猜）。
3. live 冒烟默认关：置 `ACQ_LIVE_SMOKE=1` / `RAG_LIVE_SMOKE=1` 才会真实调用外网/SiliconFlow（会烧 Key 额度）。

## 语料更新（人决 D6 / D6-修订 · cninfo 定期报告抓取）

内部语料目录 `company/` 按**上市编号裸 6 位**命名（`company/000858/`、`company/300810/`），对内子图（Internal RAG · pypdf + FAISS）直接消费。更新语料照抄执行：

```bash
# 抓取两家公司的最新 2 份定期报告（年报/半年报）PDF
.venv/bin/python -m scripts.fetch_cninfo 000858 300810

# 前缀写法自动归一为裸 6 位；每公司份数可调（env CNINFO_LIMIT 亦可）
.venv/bin/python -m scripts.fetch_cninfo sz000858 sh600519 --limit 3
```

- 数据源：巨潮资讯公告查询 API（`hisAnnouncement/query`），纯 httpx 直连（不读代理环境变量），无浏览器开销。
- 礼貌抓取：默认请求间隔 1s（`CNINFO_INTERVAL` 可调）+ 浏览器 UA；单文件失败重试 ≤2 次后跳过、不中断整批，末尾汇总失败清单。
- 坏文件（pypdf 打不开）自动删除并计入失败清单；编号不存在则提示「未找到」且不建目录。
- 落盘即覆盖同名文件（V1 无增量去重）；抓取后对内子图运行时自动重建索引，无需额外操作。

## 工程结构（task_project_scaffold 底座）

| 路径 | 内容 |
|------|------|
| `app/api/` | FastAPI 进程入口与路由（骨架：`GET /api/health`） |
| `app/web/` | Flask 进程入口 + Jinja2 首屏模板（无任何 /api/* 路由） |
| `app/graphs/` | LangGraph 三图骨架（supervisor + acquisition + internal_rag，节点全 stub） |
| `app/config.py` | 全 env 配置读取（python-dotenv）+ 默认值，无硬编码密钥 |
| `app/static/` | 截图落盘目录（`.gitkeep` 占位，`*.png` 已 gitignore） |
| `tests/` | 冒烟测试（task_project_scaffold 验收三断言） |
