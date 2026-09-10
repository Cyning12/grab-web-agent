# MVP V1.0 最终端到端验收留痕（00 · 2026-09-09/10）

> 终态代码：main @ 286ed0a（goal ① ② 已 CLOSE）· 演示进程 = 最终 main 重启实例
> 全量回归：`.venv/bin/python -m pytest tests -q` = **148 passed, 2 skipped**（live 冒烟默认关）

## 双 URL 闭环（最终代码 · Web 控制台链路真实跑通）

### sz000858 五粮液（https://gu.qq.com/sz000858/gp）

- task_id: `94a85dcf6c6d4a1dae90178ef1737757`
- SSE 事件序列：state Pending → state Fetching → progress 10 → state Parsing → progress 50 → chunk ×6 → state RAGing → conclusion → progress 100 → state Done
- 切片：6 条真实行情文本（腾讯页无蒙层、无反爬）
- 结论：risk_level=中 · sources 命中 **抓取脚本产物**（`000858/2026年半年度报告.pdf` + `000858/2025年半年度报告（更新后）.pdf`）· insufficient_info=true（价格字段异步入 chunk 弱，铁律一如实）
- **回执：已模拟写入内部系统（工单号：MOCK-E170356F）** ✅ A5 一票否决通过
- SSE 原始留档：/tmp/final_858.log

### sz300810 中科海讯（https://gu.qq.com/sz300810/gp）

- task_id: `51d97236fc2c48f7bbe94914ea4d8d65`
- SSE 事件序列同上；chunk ×4
- 结论：risk_level=**高**（「公司持续亏损，市盈率为负」——与 2025 年报事实吻合，RAG 真实基于抓取语料推理）· insufficient_info=false · sources = `300810/2025年年度报告.pdf` + `300810/2026年半年度报告.pdf`
- **回执：工单号 MOCK-1DA503B8** ✅ A5 通过
- SSE 原始留档：/tmp/final_810.log

## MVP 交付对照（PRD §8）

| 条目 | 状态 | 证据 |
|------|------|------|
| §8.1 后端异步采集管道（对外+对内） | ✅ | task_web_acquisition_subgraph / task_internal_rag_subgraph（done/） |
| §8.2 前端单页三区块 + 进度 | ✅ | task_web_console_mvp（done/）· 双进程 5000/8000 可演示 |
| §8.3 闭环验证（工单号提示） | ✅ | 本留痕双工单号 |
| §8.4 非目标遵守 | ✅ | 无批量/无像素级视觉/无复杂权限 |
| D6 语料自动化 | ✅ | task_cninfo_corpus_scraper（done/）· company/ 双目录实抓 4 份 |
| D8 目标切换腾讯 | ✅ | task_switch_target_gu_qq（done/）· 双股票真价提取 |

## 已知限制（V1.x 候选）

1. 结论 JSON 的 `competitor_price` 仍为「未知」——extracted_meta.price 已提取（71.16/27.73）但未强注入结论上下文；候选改进：对内 generate 节点显式消费 extracted_meta
2. 东财渠道因反爬下线为默认目标（仍可手动输入，走 D7 警告/拦截语义）
3. 任务状态内存态，服务重启即丢（SPEC residual_risks ① 已接受）
