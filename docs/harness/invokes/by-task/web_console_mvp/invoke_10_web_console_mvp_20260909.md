# invoke 留档 · hat 10-task · web_console_mvp

> **hat_id**：10-task（任务需求分析）
> **日期**：2026-09-09
> **task**：`docs/tasks/active/task_web_console_mvp.md`
> **依据**：`docs/harness/handoffs/PROMPT_10-task_mvp-bulk-split-x3.md`（00 派发 · bulk-split ×3）

## 本次动作

- 起草 Web 控制台 MVP task 初稿：背景/范围/非范围/依赖/验收（可勾选）/failure_paths 四列表/给执行帽必读列表 齐全
- Harness 元信息逐字段填实；test_strategy / wiki_delta=none(+note) / graph_delta=none(+note) / invoke_retention_profile=default / required_invoke_hats=10,30,40
- 预置 R0 + R1–R5 思考轮 + 思考轮控制表；人工闸 HG-TASK-DRAFT / HG-AUDIT-R1 均 pending（未代签）
- **吸收审计 R1 观察项②**：进程拓扑钉死为「Flask 仅渲染页面、API/SSE 全走 FastAPI」，写入范围/依赖/R2/验收（拓扑确认行）
- 跨 task 依赖明示：依赖 acquisition Payload 契约（§6.2）与 internal 结论 Schema，双轨可并行（Mock 解耦）

## 验证

- `npx --yes dsh-coding-kit@1.10.0 task lint --file docs/tasks/active/task_web_console_mvp.md` → **LINT: PASS**

## 禁区遵守

- 未写实现代码；未签发任何人工闸
