# invoke 留档 · hat 10-task · web_acquisition_subgraph

> **hat_id**：10-task（任务需求分析）
> **日期**：2026-09-09
> **task**：`docs/tasks/active/task_web_acquisition_subgraph.md`
> **依据**：`docs/harness/handoffs/PROMPT_10-task_mvp-bulk-split-x3.md`（00 派发 · bulk-split ×3）

## 本次动作

- 起草 对外子图（Web Acquisition） task 初稿：背景/范围/非范围/依赖/验收（可勾选）/failure_paths 四列表/给执行帽必读列表 齐全
- Harness 元信息逐字段填实；test_strategy / wiki_delta=none(+note) / graph_delta=none(+note) / invoke_retention_profile=default / required_invoke_hats=10,30,40
- 预置 R0 + R1–R5 思考轮 + 思考轮控制表；人工闸 HG-TASK-DRAFT / HG-AUDIT-R1 均 pending（未代签）
- 范围锁定 PRD §4.1–4.5 + SPEC 范围 1 / A2/A3/A6；R2 抓取路径分叉给推荐与弃选；SSRF 白名单入验收

## 验证

- `npx --yes dsh-coding-kit@1.10.0 task lint --file docs/tasks/active/task_web_acquisition_subgraph.md` → **LINT: PASS**

## 禁区遵守

- 未写实现代码；未签发任何人工闸
