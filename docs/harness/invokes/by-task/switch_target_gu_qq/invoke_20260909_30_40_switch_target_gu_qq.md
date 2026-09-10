# Invoke 留档 · 30+40 · switch_target_gu_qq

- **task**：`docs/tasks/active/task_switch_target_gu_qq.md`
- **hats**：30（执行编码）+ 40（自检，同上下文闭环）
- **分支 / 工作区**：`task/switch_target_gu_qq` · `.worktrees/gu`
- **解释器**：`/Users/cyning/Desktop/grab_web_agent/.venv/bin/python`

## 人工闸扫描（GATE_VERIFY · 首输出）

| human_gate_id | task表status | 用户/invoke声称 | 一致？ | blocks_30 | 30可开工？ |
|---------------|--------------|-----------------|--------|-----------|------------|
| HG-TASK-DRAFT | approved | 派发 Prompt 称已签 | Y | Y（22-R1,30） | — |
| HG-AUDIT-R1 | approved | 派发 Prompt 称已签 | Y | Y | ✅ 可 30 |

- reviews：`docs/harness/reviews/task_switch_target_gu_qq_audit_R1_20260909.md` 存在且 R1 PASS（内容零阻塞 + 2 条非阻塞建议）。
- pre-30 invoke：required ∩ {10,20,00} = 10 → `invoke_20260909_10_switch_target_gu_qq.md` 齐全（verify 硬闸通过）。
- 机械校验（首动作）：`npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.11.0 verify --task docs/tasks/active/task_switch_target_gu_qq.md` → exit 0 **VERIFY: PASS**。
- 开工第一条命令（审查建议①）：`grep -rn "eastmoney" tests/` → **9 文件 26 处**（URL 字面量 20 处），与审查实测吻合。
- 结论：**可进入读码/改码**。

## 30 实施摘要

| 改动 | 落点 | 要点 |
|------|------|------|
| 默认 URL 切换 | `.env.example` / `README.md` / `docs/spec/architecture/frontend_backend_breakdown_v1.md` | TASK_TARGET_URLS → `https://gu.qq.com/sz000858/gp` + `https://gu.qq.com/sz300810/gp`；README 演示节双链改腾讯 + D8 注；架构 §5 增 **D8 决策行**（人决：腾讯暂无反爬；东财保遗留痕——D4/D7 与 README 已知事项 2 不删）+ 修订记录一行 |
| parser 最小适配 | `app/services/acquisition/parser.py` `_extract_price` | 真机实测：提取非空（283 blocks/5855 tokens/6 切片全合规），唯一缺陷 = 选择器首个命中 `span#price`「分价」纯标签误提取。增补 ×2：① 命中文本无数字跳过；② 标题正则兜底先于正文正则（腾讯标题带实时价；正文首个两位小数是大盘指数）。东财夹具用例全保持绿。**chunker 零改动**（审查建议②：切分合法，「明显不合法」判定实例不适用，已留痕实现备忘） |
| 腾讯 fixture + 新用例 | `tests/fixtures/gu_qq_sz000858.html` · `tests/test_acquisition_parser_gu_qq.py` ×4 | 真机渲染 DOM 快照落盘（226KB · 2026-09-09）；用例：fixture 解析（title/price=71.16/blocks+xpath 非空/正文非全占位）· fixture 切分（6 切片 token ∈ [512,1024] · section_path/xpath 非空）· 价格标签跳过回归 ×2 |
| 旧测处置（9 文件 26 处逐条） | tests/ | **改腾讯 8 处**（默认目标语义）：sse TARGET_URL · api 入参 ×2 · pipeline 契约/铁律一/live 冒烟（改名 test_live_gu_qq，维持 skipped）；**保留东财 18 处**（反爬检出 fixture / 失败注入桩 / SSRF 白名单 / 对内透传），处置后复跑 grep 余 18 处与标注一致 |

## 40 自检（同上下文闭环）

| 命令 | 退出码 | 结果 |
|------|--------|------|
| `verify --task`（开工首跑） | 0 | **VERIFY: PASS**（双闸 approved · pre-30 invoke 齐全） |
| `grep -rn "eastmoney" tests/` | — | 26 处（处置前）→ 18 处（处置后，与逐条标注一致） |
| `.venv/bin/python -m pytest tests --collect-only -q` | 0 | **133 collected**（基线 129 + 净增 4） |
| `.venv/bin/python -m pytest tests -q` | 0 | **131 passed, 2 skipped**（基线 127+2 零回退） |
| `task lint-wiki-delta --target .` | 0 | **LINT-WIKI-DELTA: PASS** |
| 真机 sz000858（NO_PROXY 双写净化 · uvicorn :8011 · POST + SSE 5 分钟硬超时） | — | **Done** · 6 切片真实行情 · price=71.16 · insufficient_info=true（铁律一如实）· 工单 **MOCK-19A83A73** · 截图 `app/static/shot_5a29bdfd20_1788966704678.png`（无蒙层，30 亲看）· 事件流 /tmp/gu_run_sz000858_events.json |
| 真机 sz300810（同口径） | — | **Done** · 4 切片 · price=27.73 · insufficient_info=true · 工单 **MOCK-CE85445C** · 截图 `app/static/shot_6027093525_1789001383890.png`（无蒙层，30 亲看）· 事件流 /tmp/gu_run_sz300810_events.json |

验收逐条对照与已知未测项已回填 task `### 自检结论（执行者）`；实现备忘四行已回填（含旧测处置行）。验收勾选框未动（留 00 验收）。

## 共享改动申报

- `app/config.py` / `requirements.txt` / app/api / app/web / app/services/rag / supervisor / graphs **全部未动**（冻结遵守）；生产码改动仅 `parser.py` 一处函数（task 范围明文放行）。
- 新增 env 变量：无（TASK_TARGET_URLS 仅改 `.env.example` 值）。
- `tests/fixtures/` 为新增目录（task 范围放行）。

## 阻塞/风险

- 无阻塞。残余风险（task 已留档）：腾讯未来上反爬 → 既有 ANTI_BOT/超时路径；价格字段若异步占位 → 如实 insufficient_info（本轮实测两 URL 均提取到真实价 71.16/27.73，结论层 LLM 仍保守标 insufficient_info=true，未硬猜，符合铁律一）。
