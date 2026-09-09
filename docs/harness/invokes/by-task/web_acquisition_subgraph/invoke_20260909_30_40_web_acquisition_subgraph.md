# Invoke 留档 · 30+40 · web_acquisition_subgraph

- **task**：`docs/tasks/active/task_web_acquisition_subgraph.md`
- **hats**：30（执行编码）+ 40（自检，同上下文闭环）
- **分支 / 工作区**：`task/web_acquisition_subgraph` · `.worktrees/acq`
- **解释器**：`/Users/cyning/Desktop/grab_web_agent/.venv/bin/python`

## 人工闸扫描（GATE_VERIFY · 首输出）

| human_gate_id | task表status | 用户/invoke声称 | 一致？ | blocks_30 | 30可开工？ |
|---------------|--------------|-----------------|--------|-----------|------------|
| HG-TASK-DRAFT | approved | 派发 Prompt 称已签 | Y | Y（22-R1,30） | — |
| HG-AUDIT-R1 | approved | 派发 Prompt 称已签 | Y | Y | ✅ 可 30 |

- 机械校验：`npx --yes dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_web_acquisition_subgraph.md` → **VERIFY: PASS**（exit 0）
- 结论：**可进入读码/改码**。

## 30 实施摘要

按架构 §1.3 六节点三行式在 stub 骨架内填实现，实现细节下沉服务层：

| 节点 | 实现落点 | 要点 |
|------|----------|------|
| n1 validate_url | `app/services/acquisition/url_validator.py` | http/https 白名单 + 内网/环回/保留段拒绝（inet_aton 兼容 127.1 短写）+ SSRF 拦截日志 |
| n2 fetch_page | `app/services/acquisition/browser.py` | Playwright 渲染 + 路由拦截 font/media（CDP Turbo）+ 超时阈值 env 可配 + 403/验证页特征反爬检测 + 整页截图落盘 `app/static/` + JS 采集 xpath→BoundingRect 映射 |
| n3 parse_dom | `app/services/acquisition/parser.py` | BS4 + CSS 语义推断（title/meta/price/blocks），同规则 xpath 推导绑定 bbox；空解析走空 blocks 流转（铁律一，无降级路径） |
| n4 chunk_sections | `app/services/acquisition/chunker.py` | H1/H2 语义切分 512–1024 tokens；贪婪打包 + 句边界切片/字符硬切 + 尾部再平衡；整页 < 512 → 空 pre_chunks（FP-3） |
| n5 embed_chunks | `app/services/acquisition/embedder.py` | SiliconFlow openai 兼容客户端，base_url/key/model 全部来自 `app.config`（D2/D5）；空 chunks 不调 API |
| n6 emit_payload | `app/services/acquisition/payload.py` + 图内组装 | PRD §6.2 字段 + §1.5 逐字段校验（自实现最小检查器）+ Fetching→Parsing(progress=50) 状态钩子广播 |

- 图层 `app/graphs/acquisition.py`：六节点闭包 + `build_acquisition_graph(fetcher=, embedder=)` 依赖注入；异常归一为 error dict + 下游节点短路；状态钩子 `register_status_hook/clear_status_hooks`。
- 错误码词汇表对齐 §1.5：URL_REJECTED / FETCH_TIMEOUT / FETCH_FAILED / ANTI_BOT / EMBED_FAILED / CONTRACT_VIOLATION，均含用户可见文案与 retryable。

## 40 自检（同上下文闭环）

| 命令 | 退出码 | 结果 |
|------|--------|------|
| `python -m pytest tests -q` | 0 | **59 passed, 1 skipped**（live 冒烟默认关） |
| `npx --yes dsh-coding-kit@1.10.0 task lint-wiki-delta --target .` | 0 | **LINT-WIKI-DELTA: PASS** |

验收逐条对照与已知未测项已回填 task `### 自检结论（执行者）`；实现期裁定回填「实现备忘」。验收勾选框未动（留 00 验收）。

## 新增文件清单

- `app/services/__init__.py`（空包标记 ·  plumbing，见回报）
- `app/services/acquisition/`：__init__ / errors / url_validator / browser / parser / chunker / embedder / payload
- `tests/test_acquisition_url.py` / `_parser.py` / `_chunker.py` / `_embedder.py` / `_pipeline.py`
- 修改：`app/graphs/acquisition.py`（stub → 实现）· 本 task 文件（仅允许回填节）
