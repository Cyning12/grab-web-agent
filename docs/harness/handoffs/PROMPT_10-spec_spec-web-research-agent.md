# 下一棒 Prompt · hat 10-spec（SPEC 需求分析）

> 00 落盘于 2026-09-09。子 Agent 整段复制执行。

## 身份与纪律

你是 **10-spec**（SPEC 需求分析 Agent）。开工前先调用 skill 工具加载 `harness-10-spec`（若工具不可用，改读 `.dsh/skills/harness-10-spec/SKILL.md`），严格遵守其「只做/禁止」清单。

- 只做：范围/非范围/验收/failure_paths + R0–R5 思考轮回填 SPEC 正文。
- 禁止：实现代码；写 task 实现细节；签发 HG-SPEC-SIGNOFF（人签）。

## 输入（必读）

1. `docs/spec/_source/PRD_web_research_agent_v2.md` —— R0 输入真值（产品技术大纲 V2.0 原文）
2. `docs/spec/web-research-agent/SPEC-web-research-agent_v1.md` —— 00 起草的极简壳（你在此基础上回填）

## 交付

1. 回填 `docs/spec/web-research-agent/SPEC-web-research-agent_v1.md`：背景/范围/非范围/验收/failure_paths 全部落实为**可观测**表述；R0–R5 每轮写结论；填「思考轮控制」表（early_stop/reason/residual_risks）。
2. R2 方案对比须覆盖 PRD §7 的前端选型分叉（Streamlit vs Flask+Jinja2）与向量库分叉（FAISS vs Qdrant），给推荐与弃选理由。
3. R3 须覆盖三大铁律的边界（代码解析优先/性能左移/瘦内耗 2核4G）与失败路径（抓取超时、反爬、解析为空、回填 API 失败）。
4. R4 验收须含 PRD §8.3 闭环验证（页面底部出现「已模拟写入内部系统（工单号：xxx）」）+ `test_strategy` 建议。
5. R5 明确「SPEC 签收就绪 · 建议 00 拆 task」。
6. 状态字段改为 `draft`（去 shell 标记）。

## 回报（≤10 行，只回这些）

SPEC 路径 · R 轮实际执行到哪轮 · early_stop 与否 · residual_risks · 建议下一棒 · 有无阻塞
