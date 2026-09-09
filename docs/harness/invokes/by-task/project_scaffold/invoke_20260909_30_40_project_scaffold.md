# invoke · 30+40 · task_project_scaffold（2026-09-09）

> hats：30（执行编码）+ 40（执行者自检 · 同 Agent 闭环）
> task：`docs/tasks/active/task_project_scaffold.md`（HG-TASK-DRAFT=approved · HG-AUDIT-R1=approved）
> 派发：00（工程骨架底座 · 使下游三 task 的 30 可并行开工）

## 人工闸扫描（GATE_VERIFY · 首输出）

| human_gate_id | task表status | 用户/invoke声称 | 一致？ | blocks_30 | 30可开工？ |
|---------------|--------------|-----------------|--------|-----------|------------|
| HG-TASK-DRAFT | approved | 00 派发单称已签 | Y | 22-R1, 30 | — |
| HG-AUDIT-R1 | approved | 00 派发单称已签 | Y | Y | ✅ |

reviews：`task_project_scaffold_audit_R1_*.md` 存在且 R1 通过？ 是（verify 机械核验通过）

pre-30 invoke：required {10,30,40} ∩ {10,20,00} = {10} → `invoke_20260909_10_project_scaffold.md` 齐全？ 是

机械辅助复核（30 亲自复跑）：

```text
$ npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_project_scaffold.md
| HG-TASK-DRAFT | approved | 22-R1, 30 | — |
| HG-AUDIT-R1 | approved | 30 | ✅ 可 30 |
VERIFY: PASS · task_project_scaffold.md   （exit 0）
```

结论：可进入读码/改码。

## 30 施工摘要

- `requirements.txt`：11 项依赖全部 `==` 钉版（R2 已决 pip+requirements，弃 poetry/uv）：fastapi 0.141.1 · uvicorn 0.52.4 · flask 3.1.3 · langgraph 1.2.11 · playwright 1.62.0 · beautifulsoup4 4.15.0 · httpx 0.28.1 · faiss-cpu 1.15.0 · openai 3.10.0 · pytest 9.1.1 · python-dotenv 1.2.3（施工日 PyPI 最新稳定 · Python 3.13.13 干净 venv 一次解析成功）
- 目录骨架：`app/api/`（FastAPI 入口 + `GET /api/health`）· `app/web/`（Flask 入口 + Jinja2 首屏模板）· `app/graphs/`（supervisor + acquisition + internal_rag 三图骨架）· `app/config.py`（全 env 读取 + 默认值）· `app/static/.gitkeep` · `tests/`
- 图节点逐字对齐架构 §1.3/§1.4：acquisition = validate_url→fetch_page→parse_dom→chunk_sections→embed_chunks→emit_payload；internal_rag = receive_validate→retrieve_topk→generate_conclusion→writeback_tool；全部 stub，零真实抓取/解析/检索/LLM 调用
- `.env.example`：8 变量逐字按 task 范围节（D5 模型名逐字 · SILICONFLOW_API_KEY 空占位）
- `.gitignore`：.env / .venv/ / __pycache__/ / *.png（app/static/ 经 .gitkeep 白名单）
- `tests/test_smoke.py`：冒烟三断言 **先行落盘**（test_strategy: required）——骨架缺位时 collection ERROR 红灯，骨架就位后转绿
- `README.md`：本地启动节（venv → pip install → playwright install chromium → 双进程启动命令 + 冒烟验证）

## 40 自检摘要（命令 · 退出码）

| 命令 | 退出码 | 关键输出 |
|------|--------|----------|
| `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` | 0 | 11 项一次解析成功，无冲突 |
| `.venv/bin/playwright install chromium` | 0 | chromium 安装成功 |
| `.venv/bin/python -m pytest tests -q` | 0 | `3 passed, 1 warning in 1.08s` |
| 双进程实测（uvicorn :8000 + flask :5000，后台起·验完即杀） | 0 | `/api/health` → 200 `{"status":"ok"}`；`/` → 200 首屏 HTML |
| `npx --yes dsh-coding-kit@1.10.0 task lint-wiki-delta --target .` | 0 | `LINT-WIKI-DELTA: PASS`（scanned 4 · issues 0） |
| 忽略断言（cp .env → git status · git check-ignore） | 0 | .env 不入 git status；.env/.venv//*.png 命中忽略 |
| 配置断言（grep 明文 Key） | 0 | 无明文 Key（仅文件名 task-requirements 误匹配） |
| 钉版断言（grep -c == requirements.txt） | 0 | 11/11 |

自检结论已按 40 口径回填 task 正文「### 自检结论（执行者）」；「## 实现备忘」表已更新；R2/R4 续填钉版与测试先行留痕。验收勾选框按 00 红线未动，留 00 收口。

## 边界确认

- 未动 docs/ 下既有 SPEC/审查文/另外三个 task 文件；未 git commit（00 统一收口）；
- 节点全 stub：无 SSRF 校验 / Payload Schema / SSE / 检索 / LLM / Embedding 任何真实实现；
- 已知未测项：faiss-cpu / playwright 仅 macOS ARM + py3.13.13 单平台实测；README 照抄验证为本轮 30 全程按步骤实测（非第二人独立照抄）。
