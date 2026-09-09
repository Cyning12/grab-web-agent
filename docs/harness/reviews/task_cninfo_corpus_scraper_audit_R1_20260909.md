# 审查文：task_cninfo_corpus_scraper · 20-task-audit R1

> **hat_id**：20-task-audit ｜ **task**：`docs/tasks/active/task_cninfo_corpus_scraper.md`（cninfo 财报抓取脚本 · 人决 D6 兑现） ｜ **日期**：2026-09-09 ｜ **轮次**：R1

---

## 结论摘要

| 维度 | 结论 |
|------|------|
| **内容审查** | ❌ **RETURN（退回 10-task / 00 人决）** —— 1 项内容阻塞（B1） |
| **流程闸** | HG-AUDIT-R1 = `pending`（gate-check exit 2 · 30 拒开工）；20 不代签 |

---

## 机械闸实测记录（20 亲测）

| 闸 | 命令 | 结果 | exit |
|----|------|------|------|
| task lint | `npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.11.0 task lint --file docs/tasks/active/task_cninfo_corpus_scraper.md` | LINT: PASS | **0** |
| gate-check | `... dsh-coding-kit@1.11.0 gate-check --task docs/tasks/active/task_cninfo_corpus_scraper.md` | HG-AUDIT-R1 pending → ❌ 拒 30 | **2**（预期 · 未签） |
| lint-wiki-delta（验收行） | `npx --yes dsh-coding-kit task lint-wiki-delta --target .`（实跑 1.11.0） | PASS · scanned 8 · issues 0 | **0** |
| 基线 pytest | `.venv/bin/python -m pytest tests -q` | **127 passed, 2 skipped**（= 129 collected · 与 task 基线一致 · 不回退） | 0 |

注：裸 `python`（miniconda base）缺 playwright/bs4 依赖，collection 9 errors；基线仅在项目 `.venv` 下成立。

---

## 内容阻塞（B1 · 唯一 · 退回 10-task）

### B1 · 落盘目录命名口径三处真值打架，task 验收钉死的 sz 前缀与仓内实有语料及 retriever 消费语义分裂

证据链（20 亲验）：

1. **task 范围/验收**：脚本落盘 `company/sz000858/`、`company/sz300810/`，真机验收逐字检查这两目录各 ≥1 份 PDF。
2. **D6 真值 / company/README.md**：spec §5 D6 与 README 目录约定均写 `sz000858/` `sz300810/`——task 与此一致。
3. **仓内磁盘现状**：`ls company/` 实测——**人工样例内容实际在 `company/000858/`（3 份 PDF）与 `company/300810/`（2 份 PDF）**（裸 6 位数字）；`sz000858/`、`sz300810/` 两目录存在但**为空**。
4. **retriever.py 消费语义**：`load_corpus` 以**子目录原名**作 `company_code`（line 159–160）；`derive_company_code(url)` 正则 `(?:sz|sh)?(\d{6})` **剥前缀**产出 `"000858"`（line 107–113）；docstring 亦写「如 000858/ 300810/」。

后果：脚本按 task 落 `sz000858/` 后，同一公司语料**分裂为两个 company_code**（人工样例 `000858` vs 抓取 `sz000858`）；对内子图标量过滤传入 `"000858"` 时 sz 前缀目录**永不命中**（retriever line 99–104 静默回退纯向量检索，仅 info 日志），检索质量与 D6「按编号区分」语义受损。此外 task 范围允许入参 `000858`，但**入参 → 目录名的归一化规则未写**（输入 000858 落 `company/000858/` 还是 `company/sz000858/`？），属执行歧义。

处置建议（择一，须人决或 00 裁定后由 10-task 回填）：
- (a) 统一裸 6 位：脚本落 `company/<6位>/`（与磁盘现状 + retriever docstring + derive_company_code 一致），同步修订 D6 表与 README 措辞；或
- (b) 统一 sz/sh 前缀：保留 task 现口径，但须将既有 `000858/` `300810/` 样例迁移改名，并修订 retriever docstring 与过滤口径说明。

无论 (a)/(b)，task 范围须补一行「入参归一化：`000858` ≡ `sz000858` → 目录名 `<钉死形式>`」。

---

## 非阻塞观察（不拦 R2，建议顺手）

- **N1（格式）**：元信息表 `close_pr_policy` 值为 `` `exempt** `` —— 多余 `**` 笔误（markdown 失衡），task lint 不检。
- **N2（验收可命令化）**：验收首行「全量测试命令通过」未钉死命令；本仓无 `.github/workflows`（D3 仅本地运行，模板「与 CI 一致」无从对齐），且裸 `python` 环境 collection 失败。建议钉死 `.venv/bin/python -m pytest tests -q`。
- **N3（帽编号）**：task 失败路径首行与闸表写「22 未签 / 22-R1」，本仓 skill 目录已 V2 改名为 20-task-audit；与仓内嵌入 TASK_TEMPLATE 一致故不算错，模板本身滞后，记观察。
- **N4（失败路径语义）**：「PDF 损坏 → 删除坏文件」V1 可接受（与同名覆盖语义自洽）；若担心误删可考虑隔离目录，非阻断。
- **N5**：真机验收「一票否决级」**合理**——抓取脚本核心价值即 cninfo API 真实互通，mock 无法覆盖；外部可用性风险已由 residual_risks ①「接口字段/限流以实测为准」承接。

## 已核通过项

- **范围边界**：单脚本 CLI + 纯 httpx、显式不引入 Playwright，与瘦内耗/铁律三一致；非范围正确排除全文检索页 JS 爬取、FAISS 入库自动化、增量去重精细化、代理池/反爬；R2 方案 C（纳入在线管道）显式弃，与「离线批操作」定位一致。
- **失败路径**：四列齐备（触发/行为/可重试/用户可见）；限流 ≤2 重试后跳过 + 批次继续 + 末尾汇总、编号不存在建空目录明示、坏文件计数，语义合理且与验收可互查。
- **验收可命令化**：lint-wiki-delta 命令逐字可跑（实测 PASS）；真机命令、README 断言、mock 单测零外网均可判。
- **思考轮**：R0–R5 无空槽；控制表齐（early_stop=no · reason · residual_risks ×2）；元信息无占位符（N1 笔误除外）；test_strategy=required 与「mock 先行 + 真机一票否决」自洽；非行为变更类 task，无需旧测 grep 影响面项。

---

## 回填清单（退回 10-task）

1. 【B1】task §范围 与 §验收：钉死落盘目录命名唯一形式（人决 (a)/(b)），补「入参 → 目录名归一化」一行；若选 (a)，同步 D6 表 / company/README.md；若选 (b)，列明既有样例迁移步骤与 retriever 口径修订。
2. 【N1】修 `close_pr_policy` 值笔误 `exempt**` → `exempt`。
3. 【N2】验收首行钉死 `.venv/bin/python -m pytest tests -q`。

**下一棒：10-task**（B1 涉及 D6 真值措辞，先经 00/维护者裁定命名口径再回填）；**禁止**附 30 Prompt。HG-AUDIT-R1 维持 pending，20 不代签。

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 20-task-audit R1：机械闸全测（lint 0 · gate-check 2 · wiki-delta 0 · pytest 127+2 复核一致）；B1 目录命名口径阻塞 → RETURN |
