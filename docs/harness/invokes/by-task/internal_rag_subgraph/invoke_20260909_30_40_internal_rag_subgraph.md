# invoke · 30+40 · internal_rag_subgraph（2026-09-09）

> hats：30（执行编码）+ 40（执行者自检 · 同 Agent 闭环）
> task：`docs/tasks/active/task_internal_rag_subgraph.md`（HG-TASK-DRAFT=approved · HG-AUDIT-R1=approved）
> worktree：`.worktrees/rag` · 分支 `task/internal_rag_subgraph`

## 人工闸扫描（GATE_VERIFY · 首输出）

| human_gate_id | task表status | 用户/invoke声称 | 一致？ | blocks_30 | 30可开工？ |
|---------------|--------------|-----------------|--------|-----------|------------|
| HG-TASK-DRAFT | approved | 派发单称已签 | Y | 22-R1, 30 | — |
| HG-AUDIT-R1 | approved | 派发单称已签 | Y | Y | ✅ |

reviews：`task_internal_rag_subgraph_audit_R1_20260909.md` 存在且 R1 通过？ 是（verify 机械核验通过）

pre-30 invoke：required {10,30,40} ∩ {10,20,00} = {10} → `invoke_20260909_10_internal_rag_subgraph.md` 齐全？ 是

机械辅助复核（30 亲自复跑）：

```text
$ npm_config_cache=/tmp/npm-cache-dsh npx --yes dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_internal_rag_subgraph.md
| HG-TASK-DRAFT | approved | 22-R1, 30 | — |
| HG-AUDIT-R1 | approved | 30 | ✅ 可 30 |
VERIFY: PASS · task_internal_rag_subgraph.md   （exit 0）
```

结论：可进入读码/改码。

## 30 施工摘要

- **`app/graphs/internal_rag.py`**：stub 骨架内填实现，四节点三行式逐字对齐架构 §1.4：
  m1 receive_validate（Pydantic Payload 校验 · 缺 embedding/类型不符 → `CONTRACT_VIOLATION` 短路终态）
  → m2 retrieve_topk（FAISS Top-K 混合检索=向量分数序+标量 company_code 过滤拼接 · **禁 Rerank** ·
  RSS≥2560MB 降级截断 Top-K 5→2 并记降级日志 · 唯一降级手段）
  → m3 generate_conclusion（with_structured_output 等效=json_object+Pydantic 强校验 · 总尝试 ≤2 防风暴 ·
  空 chunks 不调 LLM 直出「信息不足」结论）
  → m4 writeback_tool（内存模拟 OA 端点桩 · 捕获成功/失败/工单号 · 失败不丢结论 ·
  发 RAGing→Done + progress 100 + conclusion 事件钩子供 Supervisor/SSE 消费）
- **`app/services/rag/`（新建）**：`schemas.py`（§1.5 表①Payload + 结论/回执 Schema 逐字段对齐）
  · `retriever.py`（Retriever Protocol 抽象 + FaissVectorStore 封闭 FAISS 调用，留 V2 换 Qdrant；
  `load_corpus` 读 company/ 语料（D6 按上市编号），PDF 经 pypdf 提取，离线实测 400 切片）
  · `generator.py`（SiliconFlow openai 兼容端点 · 模型/base_url 全来自 app.config · Key 仅 env）
  · `writeback.py`（InMemoryOAEndpoint 成功桩/500 桩 + MockWritebackClient · V1 恒 mock=true）
  · `resources.py`（RssSampler 周期采样 · psutil 优先、ps 回退 · A7 上限 3072MB 钉死常量）
- **`tests/`（新建 · 全 mock，零外网）**：`internal_rag_fakes.py` 公共桩 +
  `test_internal_rag_contract.py`（契约违例 ×6）· `test_internal_rag_graph.py`（三字段/闭环工单/
  空 chunks/500 桩/重试≤2/重跑不回写旧结果/事件钩子）· `test_internal_rag_degrade.py`（截断 Top-K+
  降级日志）· `test_internal_rag_audit.py`（tokenize 级禁 Rerank + 禁本地 Embedding 模型 import 审计）
  · `test_internal_rag_resources.py`（A7 RSS 峰值采样 · 原始数据留档本目录 `rss_samples_internal_rag.json`）
  · `test_internal_rag_live.py`（live 冒烟 · `RAG_LIVE_SMOKE=1` 默认关）
- 依赖注入设计（InternalRagDeps）：默认惰性构造真实 API 客户端，单测注入全 fake；
  `run_internal_rag` 每次编译新图全新 State，天然支撑 A8「重新生成」不回写旧结果

## 40 自检摘要（命令 · 退出码）

| 命令 | 退出码 | 关键输出 |
|------|--------|----------|
| `.venv/bin/python -m pytest tests -q` | 0 | `24 passed, 1 skipped, 1 warning in 0.36s`（skip=live 冒烟默认关） |
| `npx dsh-coding-kit@1.10.0 task lint-wiki-delta --target .` | 0 | `LINT-WIKI-DELTA: PASS`（scanned 4 · issues 0） |
| `npx dsh-coding-kit@1.10.0 verify --task docs/tasks/active/task_internal_rag_subgraph.md` | 0 | `VERIFY: PASS`（双闸 approved） |
| A7 RSS 采样（pytest 内 RssSampler 50ms） | 0 | 峰值 **126.42MB ≤ 3072MB** · 原始样本留档 `rss_samples_internal_rag.json` |
| 语料离线实测（load_corpus company/ + FAISS 伪向量构建） | 0 | 400 切片 · pypdf 提取中文正常 · 标量过滤 company_code=000858 命中 |
| docker 可用性 | — | 本机 docker 不可用 → A7 以 psutil 采样为等效（task residual_risks ③ 允许），已在自检注明 |

自检结论已按 40 口径回填 task 正文「### 自检结论（执行者）」；「## 实现备忘」表已更新。
验收勾选框按红线未动，留 00 收口。

## 边界确认 / 阻塞与请求

- 只动名下文件：`app/graphs/internal_rag.py` · `app/services/rag/**` · `tests/test_internal_rag_*.py`（+`tests/internal_rag_fakes.py` 公共桩）· 本 invoke 目录 · task 回填节
- **共享文件改动请求（00 合并）**：`requirements.txt` 增 `psutil`（A7 RSS 采样）与 `pypdf`（company/ PDF 语料提取）；已临时 `pip install psutil==7.2.2 pypdf==6.18.0` 进主仓 venv（.venv 为 gitignore 运行时产物，未动 tracked 文件）
- 未动 `app/config.py`（COMPANY_DIR/LLM_MODEL/EMBEDDING_MODEL 复用既有）；新 env 仅 RAG_TOP_K/RAG_TOP_K_DEGRADED/RAG_RSS_DEGRADE_MB/RAG_RSS_PEAK_LIMIT_MB（代码内默认值兜底，.env.example 更新请求同上）
- 已知未测项：live 冒烟默认关（需 `RAG_LIVE_SMOKE=1` + 真实 Key 手验）；全量 company/ PDF 真实 bge-m3 索引为 live 手测路径
