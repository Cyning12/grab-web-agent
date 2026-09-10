# Invoke 留档：cninfo_corpus_scraper · 30/40 合并（2026-09-09）

> **task**：`docs/tasks/active/task_cninfo_corpus_scraper.md`（cninfo 财报抓取脚本 · 人决 D6/D6-修订兑现）
> **hats**：30（执行编码）+ 40（自检，同上下文闭环）｜ **分支**：task/cninfo_corpus_scraper ｜ **worktree**：.worktrees/cninfo

## 30 · 开工闸（GATE_VERIFY 首输出）

| human_gate_id | task表status | blocks_30 | 30可开工？ |
|---------------|--------------|-----------|------------|
| HG-TASK-DRAFT | approved | Y（22-R1,30） | — |
| HG-AUDIT-R1 | approved | Y | ✅ |

- reviews：R1（RETURN · B1）+ R2（PASS · B1 闭合）均在 `docs/harness/reviews/`
- 机械闸：`npx dsh-coding-kit@1.11.0 verify --task ...` → **VERIFY: PASS · exit 0**
- 结论：可进入读码/改码

## 30 · 实施摘要

- `scripts/fetch_cninfo.py`（新建 · 纯 httpx + pypdf，无新依赖）：
  - CLI `python -m scripts.fetch_cninfo 000858 300810`；入参正则 `^(sz|sh|bj)`（不区分大小写）剥前缀归一裸 6 位，非法编号 stderr 报错 exit 2 且**不建目录**
  - 源选型实测：topSearch（须 POST，GET 返 500）→ orgId；hisAnnouncement/query（category_ndbg_szsh;category_bndbg_szsh）→ 定期报告列表；static.cninfo.com.cn/<adjunctUrl> 下载
  - 标题剔除 摘要/英文/更新前/已取消；按报告期去重取最新 N（--limit / env CNINFO_LIMIT，默认 2）
  - 礼貌抓取：请求间隔 1s（CNINFO_INTERVAL）+ 浏览器 UA；单文件重试 ≤2 后跳过不中断，末尾汇总失败清单
  - 落盘 `company/<裸6位>/<标题>.pdf`；pypdf 打不开的坏文件删除并计失败
  - 客户端 `trust_env=False` 直连（环境 no_proxy 含 [::1] 会炸 httpx 0.28 URLPattern 解析）
- `tests/test_fetch_cninfo.py`（新建 · 17 例 · MockTransport 零外网）
- `README.md` 增「语料更新」节（命令照抄可执行）

## 40 · 自检证据

| 命令 | 退出码 | 结果 |
|------|--------|------|
| verify --task | 0 | VERIFY: PASS |
| .venv/bin/python -m pytest tests -q | 0 | 144 passed + 2 skipped（基线 127+2 不回退） |
| task lint-wiki-delta --target . | 0 | LINT-WIKI-DELTA: PASS |
| NO_PROXY/no_proxy 双写后实跑 fetch_cninfo 000858 300810 | 0 | 成功 4 份失败 0；两目录各 +2 PDF；pypdf 提取非空 |

验收逐项结论已回填 task「自检结论（执行者）」；验收勾选框未动（留维护者/00）。

## 真机产物（落 worktree company/ · 00 合并带回主仓）

- `company/000858/2026年半年度报告.pdf`、`company/000858/2025年半年度报告（更新后）.pdf`
- `company/300810/2026年半年度报告.pdf`、`company/300810/2025年年度报告.pdf`
