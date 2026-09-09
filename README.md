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
