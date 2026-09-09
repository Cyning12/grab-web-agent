# SPEC 书面审查：web-research-agent · R1

> **审查文**：`spec_web-research-agent_audit_R1_20260909.md`
> **审查者**：20-spec-audit（书面审查 · 不代签）
> **日期**：2026-09-09
> **被审对象**：[`docs/spec/SPEC-web-research-agent_v1.md`](../../spec/SPEC-web-research-agent_v1.md)（draft · R0–R5 已回填）
> **对照真值**：[`docs/spec/_source/PRD_web_research_agent_v2.md`](../../spec/_source/PRD_web_research_agent_v2.md)（PRD V2.0 原文）
> **审查方式**：轻量单轮 R1（10-spec 思考轮已充分回填，符合轻量路径条件）

---

## 结论：**PASS（建议人签 HG-SPEC-SIGNOFF）**

无阻塞缺口；2 条非阻塞观察项留 task 阶段处理（见下）。本审查不构成签收，HG-SPEC-SIGNOFF 仅人类可签。

## 核对表

| 审查项 | 结果 | 依据 |
|--------|------|------|
| 范围 ↔ PRD §8.1–8.3 忠实 | ✅ | 对外/对内双轨、单页控制台三块回填区、状态机（Pending→Fetching→Parsing→RAGing→Done 与 §6.3 逐字一致）逐条可回溯 |
| 非范围 ↔ PRD §8.4 + §9 忠实 | ✅ | §8.4 三项全收（批量/像素级视觉/复杂权限）；扩展 4 项均挂 PRD 锚点（§9.1 代理池、§9.3 真实审批流、§9.4 私有化、Rerank 为铁律三推论），无灰色重叠项 |
| 三大铁律转为约束边界 | ✅ | §1.2 逐字转录；R3 逐条落成边界（截图仅落盘/展示/复核；Embedding 不下沉对内、禁 Rerank；2核4G 内唯一降级手段=截断 Top-K），并与 failure_paths、A6/A7 双向锁定 |
| 验收 A1–A9 可观测 | ✅ | 每条均有可观测判据；A3 钉死 section_path/xpath 与 512–1024 tokens；A6 日志无多模态调用 + screenshot_path 可追溯 |
| A5 闭环一票否决 | ✅ | 明示「一票否决项」，判据=页面底部工单号非空且与 Tool Node 模拟回调一致，直接对应 PRD §8.3 |
| failure_paths 四列齐备 | ✅ | 六条（超时/反爬/解析为空/回填失败/SSE 中断/资源超限）「触发→行为→可重试→用户可见」四列全部填实；关键设计（解析为空不降级、回填失败不丢结论、所有失败落终态）与铁律一致 |
| R0–R5 无空槽 | ✅ | 六轮全部填实，无空槽、无裁量跳轮 |
| 思考轮控制表填实 | ✅ | early_stop=no；reason 说明默认全轮执行；residual_risks 4 条如实披露（内存态状态重启即丢/反爬无兜底/角色无认证/Embedding 选型后置） |
| R2 选型自洽 | ✅ | 分叉一 Flask+Jinja2 over Streamlit：决定性理由（SSE 契约与三块异步回填是 §3.1/§3.2 硬需求，Streamlit rerun 模型结构性冲突）成立且与范围第 3 条一致；分叉二 FAISS over Qdrant：铁律三 2核4G 约束 + 单任务 MVP，Qdrant 保留为 V2 迁移候选并建议接口抽象，推理闭环 |
| 残留风险披露 | ✅ | 任务点名的 4 项（内存态/反爬/无认证/Embedding 后置）全部在 residual_risks 如实披露，未粉饰 |

## 非阻塞观察项（不退回，建议 10-task 阶段吸收）

1. **A7 内存阈值为软表述**：「可约定阈值，建议 ≤3GB」留了约定口。SPEC 层可接受，建议 task 阶段钉死具体数值与测量方式（容器限额 + 峰值采样）。
2. **前端 Flask 与后端 FastAPI 的进程拓扑未在 SPEC 层钉死**：R2 分叉一表格中「与 FastAPI 后端契约一致（或同进程直接挂 SSE 端点）」存在两种拓扑解读。PRD §2.3 允许同机部署，不构成 SPEC 缺陷；建议 task 阶段明确「Flask 仅渲染页面、API/SSE 全走 FastAPI」或同进程方案之一。

## 阻塞项

无。

## HG-SPEC-SIGNOFF 建议

**建议人签**。SPEC 忠实于 PRD V2.0，验收全部可观测且含 §8.3 一票否决闭环，failure_paths 与 R0–R5 思考轮闭合，残留风险如实披露。本人不代签，签收闸待人类执行。

## 下一棒

人签 HG-SPEC-SIGNOFF 通过后 → 00 按 R5 建议路径拆 task（对外子图 / 对内子图 / 前端控制台双轨拆分），task 草稿完成后走 20-task-audit → HG-AUDIT-R1。
