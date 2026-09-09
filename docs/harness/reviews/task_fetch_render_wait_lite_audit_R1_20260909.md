# 审查文 · task_fetch_render_wait_lite 书面审查 R1（20-task-audit）

| 项 | 值 |
|----|-----|
| 审查帽 | 20-task-audit（R1） |
| 被审对象 | `docs/tasks/active/task_fetch_render_wait_lite.md`（task_slug: `fetch_render_wait_lite`） |
| 审查日期 | 2026-09-09 |
| 前置闸 | HG-TASK-DRAFT=approved（00 代签 · 授权 `docs/harness/AUTHORIZATION_00_signoff_20260909.md`）✅ |
| 对照真值 | SPEC-web-research-agent_v1.md（signed · 铁律一 / FP-1/FP-2/FP-3）· architecture/frontend_backend_breakdown_v1.md（§1.3 n2 三行式 · §5 D4）· tasks/done/task_web_acquisition_subgraph.md · TASK_TEMPLATE.md |
| 机械闸 | `task lint` exit **0**（LINT: PASS）· `gate-check` exit **2**（HG-AUDIT-R1=pending → 拒 30，与当前流程态一致，非缺陷） |

## 结论摘要

- **内容审查：RETURN（退回 10-task，2 项回填 + 1 项建议，见下）**
- **流程闸：HG-AUDIT-R1 保持 pending，本帽不代签；RETURN 轮不出签闸清单。**

## 核对项明细（通过部分）

1. **范围/非范围 ✅**：范围 4 行全部落在 fetch_page 节点行为增强 + 文档默认值 + 真机复跑，与架构 §1.3 n2 三行式（渲染抓取/反爬特征检测/截图落盘，超时→FETCH_TIMEOUT、反爬→ANTI_BOT）逐点对应；非范围显式排除自动过滑块/打码/代理池/UA 轮换（与 SPEC 非范围 #4「动态反爬 V2.0+」一致），并排除 parse_dom/chunker/embedder/对内/控制台，无越界。
2. **失败路径 ✅**：新增 3 行与 SPEC 语义逐字对齐——渲染等待超时=FP-1（「目标页面抓取超时，请稍后重试」· 保留部分截图）；滑块检出=FP-2（ANTI_BOT 终态 Error ·「目标站点拒绝访问（反爬拦截）」· 截图留痕 · 不承诺绕过 ≈ SPEC「不承诺成功率」）；concept 版空解析=FP-3（不降级 · 空 chunks 流转 ·「信息不足」结论）。「检出滑块不绕过」为 DOM 特征检测 + 终止管道，不引入任何模型调用，与铁律一（代码解析优先 · 禁多模态）无冲突。首行 22 未签拒开工行符合模板。
3. **验收可命令化 ✅（结构层面）**：渲染等待 mock 单测、滑块 fixture + 正常 fixture 不误报、.env.example/README 默认 URL 断言、真机 A5 复跑（00 人工看图 · 一票否决级）均可执行可勾选；真机项人工可见。
4. **思考轮 ✅**：R0–R5 六槽全部填实无空槽；控制表 early_stop=no + reason + residual_risks 两条（concept 版亦可能触发反爬 · 选择器锚点依赖页面结构）合法。
5. **元信息 ✅**：必填字段无占位；graph_delta/wiki_delta=none 均有 note 理由；invoke_retention_profile=default 已选定；semi_auto=false；close_pr_policy=exempt 附 D3 理由（V1 仅本地运行无 PR 流），与 done 区 4 个 task 先例一致。
6. **必读列表 ✅**：4 条仓内相对路径全部真实存在（含 reviews/task_web_acquisition_subgraph_audit_R1_20260909.md）；第 5 条为用户会话截图留痕，非仓内路径，可接受。

## 阻塞项（退回 10-task 回填清单）

1. **「验收标准」节 · 缺「旧测 grep 影响面」项**（K7 纪律 · 行为变更类 task 必列）。本 task 改默认值（TASK_TARGET_URLS 标准页→concept）且给 fetch 节点加渲染等待/滑块检测行为，属行为变更类。实测 `grep -rn "sz000858|sz300810|eastmoney" tests/` 命中 9 文件约 25 处（`test_web_console_sse.py` TARGET_URL、`test_acquisition_pipeline.py` 失败注入/live 冒烟、`test_acquisition_url.py` 白名单用例、`test_web_console_api.py`、`test_internal_rag_*` / `internal_rag_fakes.py`、`test_acquisition_parser.py` fixture）。须补一验收项：逐条标注「不受影响 / 需更新」，并显式断言新增渲染等待不破坏既有 mock fetcher 失败注入用例（ANTI_BOT/FETCH_TIMEOUT 现行断言口径）。
2. **「验收标准」节 · 基线数失实**：task 写「基线 104 passed 不回退」，实测 `.venv/bin/python -m pytest tests -q --collect-only` = **106 tests collected**。请更正为 106 或改述为「不回退（以起工时实测基线为准）」。

## 非阻塞建议（不拦下一轮）

3. **「范围」节措辞**：README 现无东财 URL（仅 localhost 演示行），「README 演示步骤改为 concept 极速版两条」实为「新增」；验收断言行仍成立，建议措辞对齐以免 30 误判为「已有旧值可改」。

## 处置

退回 **10-task**：补上述 2 项阻塞 + 1 项建议后重交 20 R2。本轮禁止附 30 Prompt；HG-AUDIT-R1 维持 pending。

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R1：lint PASS / gate-check exit 2（符合 pending 态）；2 阻塞 + 1 建议，RETURN 10-task |
