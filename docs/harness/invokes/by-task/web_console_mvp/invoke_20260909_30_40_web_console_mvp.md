# invoke_20260909_30_40_web_console_mvp

- **task**：docs/tasks/active/task_web_console_mvp.md（task_slug=web_console_mvp）
- **hats**：30（执行编码）+ 40（自检）合并留档 · worktree=.worktrees/web · 分支 task/web_console_mvp
- **日期**：2026-09-09

## GATE_VERIFY（30 首动作）

```
$ npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_web_console_mvp.md
| HG-TASK-DRAFT | approved | 22-R1, 30 | — |
| HG-AUDIT-R1 | approved | 30 | ✅ 可 30 |
VERIFY: PASS · task_web_console_mvp.md
```

闸扫描结论：两闸 task 表均 approved，与 00 派发声称一致；R1 审查文存在；pre-30 invoke（10）齐全。可开工。

## 30 实现摘要

- 读真值：task 全文 → 架构 frontend_backend_breakdown_v1.md（§0/§1.1/§1.2/§1.5/§2/§3）→ SPEC A1–A5/A8/A9。
- 交付：app/services/console/registry.py（新建 · 内存注册表+Queue 广播+历史回放）· app/graphs/supervisor.py（薄壳 execute_task/regenerate_task，子图入口可注入，保留 build_supervisor_graph 兼容 scaffold 冒烟）· app/api/main.py（POST /api/task · SSE 五事件 · 快照 · regenerate · /static · CORS，纯 StreamingResponse 零新依赖）· app/web/app.py + templates/index.html（Flask 仅渲染 + vanilla JS 三区块/退避重连/角色视图）· tests/test_web_console_*.py（24 例）。
- 共享冻结文件零改动：requirements.txt / app/config.py / .env.example / app/graphs/acquisition.py / app/graphs/internal_rag.py / app/services/acquisition/** / app/services/rag/** / README.md。

## 40 自检（命令真跑）

1. python -m pytest tests/ -q → exit 0 · **104 passed, 2 skipped**（基线 80 保持 + 新增 24）
2. npx dsh-coding-kit@1.10.0 task lint-wiki-delta --target . → exit 0 · LINT-WIKI-DELTA: PASS
3. npx dsh-coding-kit@1.10.0 verify --task … → exit 0 · VERIFY: PASS
4. 实机双进程冒烟（uvicorn :18000 + flask :15000）：health ok · admin/调研员视图分流正确 · file:// 400 · SSE TASK_NOT_FOUND 正确

A5 闭环证据：test_a5_closed_loop_ticket_matches_writeback_callback —— SSE conclusion 事件 receipt.ticket_id 非空且 == InMemoryOAEndpoint.issued_tickets[-1]；模板含「已模拟写入内部系统（工单号：」横幅，工单号逐字取自 receipt.ticket_id。

## 已知偏差 / 留待事项

- build_supervisor_graph 仅为 scaffold 冒烟兼容保留（同步串联、无事件广播）；真实事件化编排 = execute_task。若后续 scaffold 冒烟用例退役，可收编为单一路径。
- 页面侧 A5/A8 在无浏览器约束下以「SSE 契约测试 + 模板静态断言」替代真实 DOM 断言；人工演示时复核。
- 验收勾选框未动，留 50 复检 / CLOSE 勾选。

## wiki_delta

none（task 表 wiki_delta=none；docs/coding_wiki/ 为空，本轮无晋升）。
