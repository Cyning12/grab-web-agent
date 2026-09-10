# 下一棒 Prompt · hat 10-spec（前后端架构拆解回填）

> 00 落盘于 2026-09-09。子 Agent 整段复制执行。

## 身份与纪律

你是 **10-spec** 帽执行架构分析回填。开工先调用 skill 工具加载 `harness-10-spec`（若不可用，改读 `.dsh/skills/harness-10-spec/SKILL.md`）。本次为**设计文档回填**，非新 SPEC：不做 R0–R5 全轮（上位 SPEC 已签收，思考轮已闭环），但每个技术决策须标注回溯锚点（SPEC 条目 / PRD 节号 / task 文件行）。

- 禁止：与 signed SPEC 冲突的新决策（发现冲突 → 文中标「⚠️ 待 SPEC 修订」而非擅自改向）；写实现代码。

## 输入（必读，按序）

1. `docs/spec/web-research-agent/SPEC-web-research-agent_v1.md`（signed · 铁律边界/A1–A9/R2 选型结论）
2. `docs/spec/_source/PRD_web_research_agent_v2.md`（§2 编排 / §3 前端 / §4 对外 / §5 对内 / §6 契约与状态机 / §7 技术栈）
3. `docs/tasks/active/` 三个 task（吸收已钉死项：A7=2C/4G+RSS≤3072MB · Flask 仅渲染/API+SSE 走 FastAPI · 双轨 Mock 解耦）
4. `docs/spec/architecture/frontend_backend_breakdown_v1.md`（你回填的壳）

## 交付要求

逐节回填，颗粒度对齐「30 执行帽可直接按图施工」：
1. **§0 拓扑总览**：ASCII 或 Mermaid 一图流（浏览器 ↔ Flask ↔ FastAPI ↔ Supervisor ↔ 双子图 ↔ 模拟 OA）。
2. **§1 后端**：每个 LangGraph 节点给出「输入 State 字段 → 处理 → 输出 State 字段」三行式；SSE 事件类型枚举（progress/state/chunk/conclusion/error）；任务注册表内存态结构。
3. **§1.5 契约**：PRD §6.2 Payload 逐字段类型表 + 结论 JSON Schema（竞品价格/风险等级/建议动作 + 回填回执）+ 状态机迁移触发条件表。
4. **§2 前端**：三区块各自「数据源（哪个 SSE 事件/哪个 API）· 渲染时机 · 空态/错误态」；SSE 客户端断线重连策略（对应 SPEC failure_paths 第 5 行）。
5. **§3 时序**：端到端时序表（用户操作 → API → 状态迁移 → SSE 事件 → 前端区块更新），须覆盖 A5 闭环一票否决路径。
6. **§4 铁律映射**：每条铁律 → ≥2 个具体技术落点（含「解析为空不降级多模态」的执行位置）。
7. 全文不出现与 SPEC 矛盾的选型；状态改 `draft`。

## 回报（≤10 行）

文档路径 · 各节回填完成度 · 与 SPEC 的一致性自检结果 · 有无「⚠️ 待 SPEC 修订」项 · 阻塞项
