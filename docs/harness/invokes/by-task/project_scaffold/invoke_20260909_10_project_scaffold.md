# invoke 留档 · hat 10-task · project_scaffold

> **hat_id**：10-task（任务需求分析）
> **日期**：2026-09-09
> **task**：`docs/tasks/active/task_project_scaffold.md`
> **依据**：`docs/harness/handoffs/PROMPT_10-task_project-scaffold.md`（00 派发）

## 本次动作

- 起草 工程骨架（Project Scaffold） task 初稿：背景/范围（六项 · 依赖钉版/目录结构/.env.example/config.py/.gitignore/冒烟+README）/非范围/依赖/验收（全命令化可勾选）/failure_paths 四列表/给执行帽必读列表 齐全
- Harness 元信息逐字段填实：test_strategy=required（冒烟即真实测试制品）· code_quality_bar=recommended · wiki_delta=none(+note) · graph_delta=none(+note) · invoke_retention_profile=default · required_invoke_hats=10,30,40 · orchestration=MANIFEST 仅 · chain_prompt=等效链（30-execute-code + 40-self-check）· git_branch=task/project_scaffold
- 预置 R0 + R1–R5 思考轮 + 思考轮控制表（early_stop=no）；R2 依赖管理分叉 poetry vs uv vs pip+requirements.txt，推荐 pip+requirements 钉版（D3 本地运行下最简单可复现），双弃选给理由
- D5 模型钉死落入 .env.example 验收行：LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash · EMBEDDING_MODEL=BAAI/bge-m3，全 env 可配置、无明文 Key
- 图骨架节点名对齐架构 §1.3/§1.4（acquisition 六节点 / internal_rag 四节点 / supervisor），全 stub；人工闸 HG-TASK-DRAFT / HG-AUDIT-R1 均 pending（未代签）

## 验证

- `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 task lint --file docs/tasks/active/task_project_scaffold.md` → **LINT: PASS**（一次通过）

## 禁区遵守

- 未写实现代码；未改另外三个 task 文件；未签发任何人工闸
