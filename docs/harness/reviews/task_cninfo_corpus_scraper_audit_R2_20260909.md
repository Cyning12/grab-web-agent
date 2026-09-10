# 审查文：task_cninfo_corpus_scraper · 20-task-audit R2

> **hat_id**：20-task-audit ｜ **task**：`docs/tasks/active/task_cninfo_corpus_scraper.md`（cninfo 财报抓取脚本 · 人决 D6 兑现） ｜ **日期**：2026-09-09 ｜ **轮次**：R2（复审 R1 回填）
> **前轮**：`docs/harness/reviews/task_cninfo_corpus_scraper_audit_R1_20260909.md`（RETURN · B1 唯一阻塞）

---

## 结论摘要

| 维度 | 结论 |
|------|------|
| **内容审查** | ✅ **PASS** —— R1 唯一阻塞 B1 已闭合，非阻塞①②已修，修订无新问题 |
| **流程闸** | HG-AUDIT-R1 = `pending`（gate-check exit 2 · 30 拒开工）；20 不代签，维护者签闸后方可 30 |

---

## 机械闸实测记录（R2 复跑）

| 闸 | 命令 | 结果 | exit |
|----|------|------|------|
| task lint | `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.11.0 task lint --file docs/tasks/active/task_cninfo_corpus_scraper.md` | LINT: PASS | **0** |
| gate-check | `... dsh-coding-kit@1.11.0 gate-check --task docs/tasks/active/task_cninfo_corpus_scraper.md` | HG-AUDIT-R1 pending → ❌ 拒 30 | **2**（预期 · 未签） |

---

## B1 闭合核验（R1 唯一阻塞 · 逐字核对 + 语义闭合）

00 裁定 (a) 统一裸 6 位，task 三处口径逐字核对一致：

1. **背景（§背景与目标）**：「按**上市编号裸 6 位**命名区分、自动落盘（sz/sh 前缀废弃——retriever derive_company_code 剥前缀产出裸号，前缀致语料分裂 + 标量过滤静默失效）」，完成态落盘 `company/000858/`、`company/300810/`。
2. **范围 CLI 行（§范围 首行）**：「接受 `sz000858` / `000858` 等写法，**归一化为裸 6 位**——剥前缀正则 `^(sz|sh|bj)` 不区分大小写，非法编号报错不建目录；按裸号建目录 `company/<6位code>/`」——R1 要求的「入参 → 目录名归一化」一行已补齐，且覆盖非法入参行为。
3. **真机验收行（§验收）**：`python -m scripts.fetch_cninfo 000858 300810` 实跑 exit 0，`company/000858/` 与 `company/300810/` 各 ≥1 份 PDF，pypdf 提取文本非空。

与外部真值闭合（20 亲验）：

- **磁盘实有**：`ls company/` = `000858/`（3 份 PDF）、`300810/`（2 份 PDF）、README.md；**无任何 sz\* 目录**（R1 记录的空 sz 目录已不复存在），裸号口径与磁盘零冲突。
- **retriever 语义**：`derive_company_code` 正则 `(?:sz|sh)?(\d{6})` 剥前缀产出裸号（line 107–113）；`load_corpus` 以子目录原名作 company_code（line 159–160）。裸 6 位落盘 ⇒ 抓取语料与人工样例同 company_code，标量过滤不再静默失效，B1 后果链根除。
- **架构 §5**：D6-修订行（line 321）已增——「**统一裸 6 位编号**（`company/000858/`、`company/300810/`），废弃 sz 前缀写法」，依据（磁盘裸号 + retriever 剥前缀 + 用户原话「按上市编号」）与入参归一规则均写明；原 D6 行（line 320）保留为历史记录、由修订行显式覆盖，决策表写法自洽。
- **company/README.md**：已对齐——首行 D6 + D6-修订裸 6 位口径、目录树 000858//300810/、末行「入参 `sz000858`/`000858` 均归一为裸 6 位」。

**B1 → 闭合。**

## R1 非阻塞项核销

| 项 | 处置 | 核验 |
|----|------|------|
| N1 `close_pr_policy` 笔误 `exempt**` | 已修为 `exempt`（元信息表 line 32） | ✅ |
| N2 验收首行钉死 pytest 命令 | 已钉死 `.venv/bin/python -m pytest tests -q` + 基线 129 collected（127+2）不回退（§验收首行） | ✅ |
| N3 模板 22/20 帽编号滞后 | 00 裁定不在本 task 修（kit 模板滞后）；task 失败路径首行「22 未签」为模板原文，维持观察 | ✅（不拦） |
| N4/N5 | R1 已判定可接受/合理，无需处置 | — |

## 修订无新问题（增量扫描）

- 修订记录已增 R2 送审行，HG-AUDIT-R1 维持 `pending` 未冒签。
- 范围/非范围/失败路径/思考轮（R0–R5 · 控制表 early_stop=no · residual_risks ×2）较 R1 无实质变更，R1 已核通过项继续有效。
- 剥前缀正则新增 `bj`（北交所）为前瞻性收紧，与裸 6 位口径不冲突；retriever 侧 URL 提取正则不在本 task 范围，无耦合问题。
- 非行为变更类 task（新增脚本），无旧测 grep 影响面项要求。

---

## 维护者签闸（20 后 · 30 前）

- [ ] 已读 R2 审查结论（内容 PASS · R1/R2 均已阅）
- [ ] 在 task 人工闸表将 HG-AUDIT-R1 改为 approved（维护者 · 日期）
- [ ] commit task 文档或确认已签
- [ ] 再下发 Harness 30 Prompt

30 Agent 将以 task 表为准；pending 时必须拒开工（见 TEMPLATE_30_gate_stop.md）。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R2：B1 三处口径逐字核对一致 + 磁盘/retriever/D6-修订/README 语义闭合 → **PASS**；lint exit 0 · gate-check exit 2（HG-AUDIT-R1 pending，维护者签闸清单已附） |
