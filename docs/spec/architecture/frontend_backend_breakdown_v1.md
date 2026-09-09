# 前后端技术架构拆解（web-research-agent）v1

> **状态**：`draft`（10-spec 帽回填完毕 · 2026-09-09）  
> **上位真值**：[`../SPEC-web-research-agent_v1.md`](../SPEC-web-research-agent_v1.md)（signed）· [`../_source/PRD_web_research_agent_v2.md`](../_source/PRD_web_research_agent_v2.md)  
> **下游消费者**：`docs/tasks/active/` 三个 MVP task 的 30 执行帽  
> **锚点记法**：【SPEC A#】= SPEC 验收条目 ·【SPEC FP-n】= SPEC failure_paths 第 n 行 ·【SPEC R#】= SPEC 思考轮 ·【PRD §x.y】= PRD 节号 ·【T-ACQ/T-RAG/T-WEB】= docs/tasks/active/ 下 task_web_acquisition_subgraph / task_internal_rag_subgraph / task_web_console_mvp  
> **纪律**：本文不引入与 signed SPEC 冲突的新决策；所有选型均可回溯锚点；不含实现代码。

---

## 0. 拓扑总览

进程拓扑已钉死【T-WEB 背景节「进程拓扑」· 审计观察项②】：**Flask 仅渲染页面模板，全部 API/SSE 端点由 FastAPI 进程提供**；两进程同机部署【PRD §2.3】；Supervisor 主控图 + 对外/对内双轨并行子图【PRD §2.1 · SPEC 背景节】。

```
┌────────────────────────────── 单容器 / 同机（PRD §2.3）──────────────────────────────┐
│                                                                                      │
│   浏览器（vanilla JS：fetch + EventSource）                                            │
│      │ ① GET /            （首屏 HTML）                                                │
│      ▼                                                                               │
│  ┌─────────┐   仅渲染 Jinja2 模板骨架，无任何 /api/* 路由【T-WEB 验收·拓扑确认行】        │
│  │ Flask   │                                                                          │
│  │ (render)│                                                                          │
│  └────▲────┘                                                                          │
│       │ 首屏后页面内 JS 直连 FastAPI（CORS 或同源反代，30 实现细节【T-WEB R3】）           │
│      │ ② POST /api/task            ④ GET /static/<shot>.png（截图）                    │
│      │ ③ GET /api/task/{id}/stream (SSE)  ⑤ POST /api/task/{id}/regenerate（admin）    │
│      ▼                                                                               │
│  ┌───────────────────────── FastAPI 进程 ─────────────────────────┐                   │
│  │ API 层：task 提交 / SSE 流 / static / regenerate                │                   │
│  │ 任务注册表：内存 dict + 每订阅者 asyncio.Queue【SPEC FP-5】       │                   │
│  │ Supervisor 主控图（LangGraph）                                  │                   │
│  │   │ 状态机 Pending→Fetching→Parsing→RAGing→Done【PRD §6.3】     │                   │
│  │   ├──▶ 对外子图 Web Acquisition（胖采集 · 铁律二下沉）            │                   │
│  │   │      Fetch(Playwright+CDP)→Parse(BS4+CSS语义)→Chunk         │                   │
│  │   │      (H1/H2,512–1024tok)→Screenshot→Embed → 标准 Payload     │                   │
│  │   │                                  │ PRD §6.2 契约            │                   │
│  │   └──▶ 对内子图 Internal RAG（瘦内耗 · 2核4G 资源盒 · 铁律三）     │                   │
│  │          Receive→Retrieve(FAISS Top-K,禁Rerank)→Generate        │                   │
│  │          (with_structured_output)→Writeback Tool Node            │                   │
│  └────────────────────────────────────────│───────────────────────┘                   │
│                                            ▼ 模拟 POST                                 │
│                                    ┌──────────────┐                                    │
│                                    │ 模拟内部 OA  │ 回调：成功/失败/工单号【PRD §5.3】   │
│                                    │ (Tool 桩)    │                                    │
│                                    └──────────────┘                                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

要点：

- Flask 与 FastAPI 为**两个进程**；Flask 进程零业务 API（路由清单断言验收【T-WEB 验收末行】）。
- 对外子图不依赖内部大模型、对内子图可全 Mock Payload 独立闭环，双轨并行开发【PRD §2.2 · T-ACQ/T-RAG 非范围互锁】。
- 模拟 OA 为对内子图末节点 Tool Node 的可注入桩（成功桩 / 500 桩）【T-RAG R4】。

---

## 1. 后端架构（FastAPI + LangGraph）

### 1.1 API 层

**端点清单**（全部位于 FastAPI 进程【T-WEB 范围】）：

| 端点 | 方法 | 职责 | 锚点 |
|------|------|------|------|
| `/api/task` | POST | 入参 URL → SSRF 白名单校验（仅 http/https，拒 file:// 与内网段）→ 创建 task_id → 注册表登记 → **后台异步**触发 Supervisor → 立即返回 `{task_id}`，不经 HTTP 长等待 | 【SPEC A1 · T-ACQ 范围 SSRF 行 · T-WEB 失败路径第 1 行业务行】 |
| `/api/task/{id}/stream` | GET | SSE 流：订阅即先回放当前状态快照（断线补拉语义），再实时转发进度/状态/chunk/结论/错误事件 | 【PRD §3.1 · SPEC A1 · SPEC FP-5】 |
| `/static/<path>` | GET | 截图落盘目录的静态托管，供 Step 1 缩略图与人工复核 | 【SPEC A6 · PRD §6.2 `screenshot_path`】 |
| `/api/task/{id}/regenerate` | POST | 以同一已存 Payload 重跑对内子图，产出新结论并刷新 Step 3；**不回写旧结果** | 【SPEC A8 · T-RAG 范围「重新生成」行】 |

**SSE 事件类型枚举**（`event:` 字段五类，数据均为 JSON）：

| event | data 字段 | 触发时机 | 锚点 |
|-------|-----------|----------|------|
| `progress` | `{percent: 10\|50\|100}` | 进入 Fetching→10%；Fetching→Parsing 迁移→50%；RAGing→Done 迁移→100% | 【PRD §6.1 · T-ACQ 验收末行 · T-RAG 验收末行】 |
| `state` | `{status: Pending\|Fetching\|Parsing\|RAGing\|Done, detail?: string}` | 每次状态机迁移；终态含 `Done(回填失败)` 语义于 detail | 【PRD §6.3 · SPEC 范围 4】 |
| `chunk` | `{index, title, text, section_path, xpath, token_count}` | Parsing 期间每产出一个已嵌入 chunk 即推一条（Step 2「实时展示」） | 【SPEC A3 · PRD §3.2 Step 2】 |
| `conclusion` | `{conclusion: <结论JSON>, receipt: <回填回执>}` | 对内子图 Writeback 节点完成后推送一次（A5 闭环数据源） | 【SPEC A4/A5 · PRD §3.2 Step 3】 |
| `error` | `{code, message, retryable: bool}` | 任一 failure_paths 行触发、任务转终态 Error 时推送 | 【SPEC A9 · 六条 failure_paths】 |

**任务注册表内存态结构**【SPEC FP-5「内存态可接受，须日志可查」· SPEC residual_risks ①】：

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | str (uuid4) | 创建时生成，SSE 重连与 regenerate 的定位键 |
| `url` | str | 已过 SSRF 白名单的目标 URL |
| `status` | 状态机枚举 | 见 §1.5 状态机表；迁移全部落日志 |
| `progress` | int ∈ {0,10,50,100} | 与 progress 事件同源 |
| `payload` | dict \| None | 对外子图产出的 PRD §6.2 标准 Payload（regenerate 的输入源） |
| `conclusion` / `receipt` | dict \| None | 对内子图结论 JSON 与回填回执 |
| `error` | dict \| None | 终态 Error 的 code/message |
| `created_at` / `updated_at` | datetime | 日志与停滞检测用 |
| `subscribers` | list[Queue] | 每个 SSE 连接一个 asyncio.Queue，Supervisor 钩子广播写入 |

服务重启内存态即丢（V1 接受）；SSE 重连时以 task_id 查表，命中则回放快照，未命中返回 `error{code:"TASK_NOT_FOUND"}`【SPEC FP-5 · T-WEB R3】。

### 1.2 编排层：Supervisor 主控图

职责：接单 → 顺序驱动对外子图 → 对内子图 → 广播状态/进度事件；本身不做任何 CPU/内存密集计算（铁律二/三职责在子图内）【PRD §2.1 · SPEC 背景节】。

- **节点三行式**
  - 输入 State：`{task_id, url}`（来自注册表）
  - 处理：入口校验（复用 SSRF 结果）→ 调对外子图 → 将 Payload 落注册表并调对内子图 → 收集结论+回执落注册表 → 推终态；任一子图失败按 failure_paths 映射为 `error` 事件 + 终态 Error / Done(回填失败)
  - 输出 State：`{status, progress, payload?, conclusion?, receipt?, error?}`（回写注册表，即 SSE 广播源）

- **进度映射**：`Pending→Fetching`=10% · `Fetching→Parsing`=50% · `RAGing→Done`=100%（中间 Parsing→RAGing 不增进度档，仅发 state 事件）【PRD §6.1 仅定义三档 · T-ACQ/T-RAG 验收末行】。

### 1.3 对外子图（Web Acquisition · 胖采集）

链：`validate_url → fetch_page → parse_dom → chunk_sections → embed_chunks → emit_payload`【PRD §4.1–4.5 · T-ACQ 范围】。截图在 fetch 阶段完成【T-ACQ 范围截图行】。每节点三行式：

**n1 validate_url**
- 输入 State：`{url}`
- 处理：协议白名单（仅 http/https）+ 内网地址段（10.x/172.16.x/192.168.x/127.x）拒绝；违例即终止管道
- 输出 State：`{url_validated}` 或失败终态 `error{code:"URL_REJECTED"}`【T-ACQ 失败路径非法 URL 行 · SPEC R3 安全节】

**n2 fetch_page**
- 输入 State：`{url_validated}`
- 处理：Playwright 渲染抓取（主路径，超时阈值可配置）+ CDP Turbo 加速；检测 403/验证码/验证页重定向等反爬特征；整页/视口截图落盘；抓取 HTTP 状态码与原始 DOM
- 输出 State：`{raw_dom, http_status, screenshot_path, anti_bot_flag}`；超时→`error{code:"FETCH_TIMEOUT"}`，反爬→`error{code:"ANTI_BOT"}`【PRD §4.1/4.4 · T-ACQ R2 抓取路径裁定 · SPEC FP-1/FP-2】

**n3 parse_dom**
- 输入 State：`{raw_dom}`
- 处理：BeautifulSoup + CSS 语义推断（微格式）提取标题/Meta/价格/SKU/正文，并为提取节点绑定 BoundingRect 与 XPath；**解析为空时不降级多模态**（铁律一，执行位置见 §4），以空结果继续流转
- 输出 State：`{extracted_meta: {title, meta, price, http_status}, blocks: [{text, bbox, xpath}]}`（可为空 blocks）【PRD §4.2 · SPEC FP-3 · SPEC A2 要求 meta 含状态码 → `extracted_meta` 在 PRD §6.2 示例字段基础上扩展 `http_status`，属 SPEC A2 强制、非冲突】

**n4 chunk_sections**
- 输入 State：`{blocks}`
- 处理：按 H1/H2 标题语义切分，每块 512–1024 tokens，附父级 `section_path` 与 `xpath`；空 blocks → 空 `pre_chunks`
- 输出 State：`{pre_chunks: [{title, text, section_path, xpath, token_count}]}`【PRD §4.3 · SPEC A3 · T-ACQ 验收切分断言行】

**n5 embed_chunks**
- 输入 State：`{pre_chunks}`
- 处理：逐 chunk 调轻量 Embedding 模型生成向量（模型选型留 30 实现期，约束：轻量、可离线或小模型 API）；Embedding 服务失败 → 终态 Error
- 输出 State：`{pre_chunks[].embedding}`（就地补字段）；失败 `error{code:"EMBED_FAILED"}`【PRD §4.5 · T-ACQ 失败路径 Embedding 行 · T-ACQ R2 Embedding 注】

**n6 emit_payload**
- 输入 State：`{url, screenshot_path, extracted_meta, pre_chunks}`
- 处理：组装 PRD §6.2 标准 Payload 并按 §1.5 Schema 校验；状态钩子发 Fetching→Parsing 迁移事件
- 输出 State：`{payload}`（交 Supervisor 落注册表并转对内）【T-ACQ 范围 Payload 校验行与状态钩子行 · T-ACQ 验收契约测试行】

### 1.4 对内子图（Internal RAG · 瘦内耗）

链：`receive_validate → retrieve_topk → generate_conclusion → writeback_tool`【PRD §5.1–5.3 · T-RAG 范围】。每节点三行式：

**m1 receive_validate**
- 输入 State：`{payload}`
- 处理：按 §1.5 Schema 校验 Payload（字段缺失/类型不符/缺 `embedding` 即契约违例）；**禁止重算 Embedding**（铁律二，进程内不加载 Embedding 模型）
- 输出 State：`{payload_validated}` 或 `error{code:"CONTRACT_VIOLATION"}`【T-RAG 失败路径契约行 · T-RAG R3 铁律二边界】

**m2 retrieve_topk**
- 输入 State：`{payload_validated.pre_chunks}`
- 处理：FAISS 进程内索引 Top-K 混合检索（向量 + 标量过滤拼接；**禁用 Rerank**；检索接口抽象、FAISS 调用不散落业务逻辑，留 V2 换 Qdrant）；内存逼近阈值时降级 = 截断 Top-K（减少条数）并记降级日志——**唯一允许的降级手段**
- 输出 State：`{context_chunks: [...], degraded: bool}`【SPEC R2 分叉二 · T-RAG R2 接口抽象约束 · SPEC FP-6 · T-RAG 验收降级用例行】

**m3 generate_conclusion**
- 输入 State：`{context_chunks, payload_validated}`
- 处理：`with_structured_output` 强制生成符合 §1.5 结论 Schema 的 JSON（竞品价格/风险等级/建议动作）；空 `pre_chunks` → 正常产出「信息不足」结论（非错误）；LLM 失败有限重试 ≤2 次（防重试风暴）
- 输出 State：`{conclusion}`；重试耗尽 → `error{code:"GENERATE_FAILED"}`【PRD §5.2 · SPEC A4 · T-RAG 失败路径 LLM 行 · T-RAG R3 防重试风暴】

**m4 writeback_tool（Tool Node · 末节点）**
- 输入 State：`{conclusion}`
- 处理：绑定**模拟**内部系统 POST API 的可注入桩，推送结论 JSON，捕获回调（成功/失败/工单号）；回填失败**不丢结论**，仅回执标失败原因，终态 Done(回填失败)；发 RAGing→Done 迁移事件（进度 100%）
- 输出 State：`{receipt: {status, ticket_id?, reason?}}`【PRD §5.3 · SPEC FP-4 · SPEC A5 · T-RAG 验收 Tool Node 闭环行】

### 1.5 跨子图契约

**① PRD §6.2 标准 Payload 逐字段类型表**（对外产出 / 对内消费双向校验【SPEC R4-1 · T-ACQ 验收契约行】）：

| 字段路径 | 类型 | 必填 | 说明 | 锚点 |
|----------|------|------|------|------|
| `url` | string (http/https) | 是 | 目标页 URL | 【PRD §6.2】 |
| `screenshot_path` | string | 是 | 落盘截图相对 `/static` 的可追溯路径 | 【PRD §6.2 · SPEC A6】 |
| `extracted_meta` | object | 是 | 代码级提取的元数据 | 【PRD §6.2】 |
| `extracted_meta.title` | string | 是 | 页面标题（可空串） | 【PRD §6.2 示例 · SPEC A2】 |
| `extracted_meta.price` | string | 是 | 提取价格原文（可空串） | 【PRD §6.2 示例】 |
| `extracted_meta.meta` | object | 否 | description/keywords 等 Meta | 【SPEC A2「标题/Meta/状态码」】 |
| `extracted_meta.http_status` | int | 是 | 抓取 HTTP 状态码（PRD 示例未列，SPEC A2 强制展示，属扩展非冲突） | 【SPEC A2】 |
| `pre_chunks` | array | 是（可空数组） | 空数组 = 解析为空失败路径，正常流转 | 【SPEC FP-3】 |
| `pre_chunks[].title` | string | 是 | 块标题（如「产品参数」） | 【PRD §6.2 示例】 |
| `pre_chunks[].text` | string | 是 | 正文片段 | 【PRD §6.2 示例】 |
| `pre_chunks[].embedding` | array[float] | 是 | 对外轨预计算向量；缺失 = 契约违例（对内禁重算） | 【PRD §6.2 · T-RAG R3】 |
| `pre_chunks[].xpath` | string | 是（非空） | 可溯源坐标 | 【PRD §4.3/§6.2 · SPEC A3】 |
| `pre_chunks[].section_path` | string | 是（非空） | 父级标题路径（PRD 示例未列，PRD §4.3 与 SPEC A3 强制） | 【PRD §4.3 · SPEC A3】 |
| `pre_chunks[].token_count` | int | 是 | ∈ [512, 1024]，供 A3 区间断言 | 【PRD §4.3 · SPEC A3 · T-ACQ 验收切分行】 |

**② 结论 JSON Schema**（对内产出 / 前端 Step 3 消费【SPEC A4 · PRD §3.2 Step 3】）：

```
Conclusion = {
  "competitor_price":  string,          // 竞品价格（SPEC A4 字段一）
  "risk_level":        "低"|"中"|"高",   // 风险等级枚举（SPEC A4 字段二）
  "suggested_action":  string,          // 建议动作（SPEC A4 字段三）
  "insufficient_info": boolean,         // true = 「信息不足」结论（空 chunks 路径）
  "sources":           string[]         // 溯源 section_path/xpath 列表（可空）
}
Receipt = {                             // 回填回执（随 conclusion 事件同行）
  "status":    "success"|"failed",
  "ticket_id": string | null,           // 非空且与 Tool Node 回调一致（SPEC A5 一票否决）
  "reason":    string | null,           // status=failed 时的失败原因（SPEC FP-4）
  "mock":      true                     // V1 恒为 true（模拟回填 · PRD §8.3 / §9.3 边界）
}
```

「信息不足」结论 = `insufficient_info: true` 且三字段给占位文案，仍通过同一 Schema 校验【SPEC FP-3 · T-RAG 范围空 chunks 行】。

**③ 状态机迁移触发条件表**【PRD §6.3 · SPEC 范围 4 · failure_paths】：

| 迁移 | 触发条件 | 伴随 SSE 事件 |
|------|----------|---------------|
| → Pending | POST /api/task 校验通过、注册表登记 | `state` |
| Pending → Fetching | Supervisor 调起对外子图 n2 | `state` + `progress 10` |
| Fetching → Parsing | n2 完成（DOM+截图到手） | `state` + `progress 50` |
| Parsing → RAGing | n6 Payload 校验通过并转交对内 | `state`（进度保持 50，期间逐条发 `chunk`） |
| RAGing → Done | m4 回填回调捕获（成功或失败均落 Done，失败以 `detail="回填失败"` 区分） | `state` + `progress 100` + `conclusion` |
| 任意 → Error | FP-1 超时 / FP-2 反爬 / 非法 URL / Embedding 失败 / 契约违例 / 生成重试耗尽 | `error` + `state{status:"Error"}` |

终态不滞留中间态：所有失败路径均落 Error 或 Done(回填失败)【SPEC A9】。

### 1.6 资源与部署

- **限额**：对内子图运行于 2 核 4G 资源盒【铁律三 · SPEC A7】；钉死值 = `docker run --cpus=2 --memory=4g`（或等效 cgroup），每 1s 采样 RSS（`/proc/<pid>/status` VmRSS 或 `docker stats`），**峰值 ≤ 3072MB**，采样原始数据留档【T-RAG 验收 A7 行 · 审计观察项①】。
- **进程归属（设计决策，不冲突）**：V1 单容器双进程——Flask（渲染）+ FastAPI（API/SSE + Supervisor + 双子图同进程 asyncio 执行）；A7 采样对象为运行对内子图的 FastAPI 进程（docker stats 容器视图兜底；macOS 无 /proc 的等效采样属 30 制品）【PRD §2.3 · T-WEB 进程拓扑 · T-RAG residual_risks ③】。
- **降级手段唯一**：内存逼近阈值 → 截断 Top-K，禁止引入常驻重服务（Qdrant 等独立服务进程 V1 不引入）【SPEC FP-6 · SPEC R3 铁律三边界 · T-RAG 非范围】。
- **LLM**：POC 期外部 API，Key 不落盘明文【SPEC R3 建议项 · T-RAG 非范围】；服务商钉死 **SiliconFlow**（人决 D2 · 见 §5 决策记录），对内结论生成与 Embedding 均走其 API（调用即出域，不占本地 2核4G 配额，与铁律三兼容）。
- **运行形态**：V1 **仅本地运行**，不考虑发布/上线（人决 D3）；A7 验收仍按 docker 限额执行（本地 docker 即可），容器镜像发布、CI 部署管线均为非目标。

---

## 2. 前端架构（Flask + Jinja2 + 原生 JS）

### 2.1 渲染职责边界

Flask 仅交付首屏 HTML 骨架（输入框 + 「开始调研」按钮 + 三区块容器 + 底部回执条），**不含任何 /api/* 路由**；首屏后全部动态数据由页面内 vanilla JS（fetch / EventSource）直连 FastAPI【T-WEB 进程拓扑 · T-WEB 非范围前端框架行 · PRD §7】。CORS 放行 Flask 页面来源或同源反代为 30 实现细节【T-WEB R3】。

### 2.2 单页三区块组件拆解

| 区块 | 数据源 | 渲染时机 | 空态 / 错误态 |
|------|--------|----------|----------------|
| **Step 1 预览区**（截图缩略图 + 标题/Meta/状态码） | `state` 事件进入 Parsing（Fetching 完成）后，以注册表快照 / Payload 的 `screenshot_path`（经 `/static`）+ `extracted_meta`；重连时由订阅即回放的快照恢复 | 收到 `state{Parsing}` 或快照含 `screenshot_path` 即渲染 | 抓取超时/反爬：`error` 事件渲染对应文案「目标页面抓取超时，请稍后重试」/「目标站点拒绝访问（反爬拦截）」+ 状态码【SPEC FP-1/FP-2】；保留的部分截图仍可展示【SPEC FP-1】 |
| **Step 2 知识切片区**（pre_chunks 实时列表） | `chunk` 事件逐条追加（title/text 片段 + `section_path`/`xpath` 展示）；快照含已发 chunk 序列 | Parsing 期间随 `chunk` 事件实时渲染【SPEC A3】 | 空 chunks：显示「未提取到有效内容」【SPEC FP-3】；Embedding 失败：`error` 渲染「向量化失败，请稍后重试」【T-ACQ 失败路径】 |
| **Step 3 结论回填区**（结论卡片 + 回填回执） | `conclusion` 事件（`conclusion` 三字段卡片 + `receipt`）；admin 点「重新生成」→ `POST /api/task/{id}/regenerate` 后等新一轮 `conclusion` 刷新 | 收到 `conclusion` 即渲染；regenerate 返回后旧卡片标「生成中…」占位 | 信息不足：渲染 `insufficient_info` 卡片【SPEC FP-3】；回填失败：卡片照出 + 回执区「模拟写入失败：原因」，底部不出现工单号【SPEC FP-4】；生成失败：`error`「结论生成失败」【T-RAG 失败路径】；非 admin 视角整块不渲染（§2.4） |

**页面底部闭环条**：`conclusion.receipt.status=="success" && ticket_id 非空` → 显示「已模拟写入内部系统（工单号：xxx）」，文案与工单号逐字取自回执（SPEC A5 一票否决项的页面侧）【PRD §8.3 · SPEC A5 · T-WEB 范围闭环行】。

### 2.3 SSE 客户端与状态同步

- **订阅**：提交成功后 `new EventSource("/api/task/{id}/stream")`；服务端订阅即回放当前快照，前端以快照幂等重建三区块【SPEC FP-5 · T-WEB R3】。
- **断线重连策略**（对应 SPEC FP-5）：EventSource `onerror` 触发 → 以同一 task_id 指数退避自动重连（如 1s/2s/4s，上限 5 次）→ 每次重连依赖服务端快照补拉当前状态（无数据空洞）→ 进度条停滞超过阈值（如 15s 无事件）显示「连接中断，正在重连」→ 超上限提示「连接中断，请刷新页面」；后端任务状态内存态不丢、日志可查【SPEC FP-5 · T-WEB 范围断线行 · T-WEB 验收 SSE 断线演练行】。
- **终态收敛**：收到 `error` 或 `state{Done}`（含 Done(回填失败)）即关闭 EventSource，UI 锁定终态，不滞留中间态【SPEC A9】。

### 2.4 角色视图（最小实现）

- 角色判定 = URL 参数 `?role=admin`，无认证、仅演示权限语义【SPEC 范围 5 · T-WEB R1 · SPEC residual_risks ③】。
- 默认（调研员）：模板/JS 仅渲染 Step 1+2，Step 3 容器不渲染、即使收到 `conclusion` 事件也不展示【SPEC A8】。
- `?role=admin`（决策层/管理员）：全量渲染 + 「重新生成」按钮 → `POST /api/task/{id}/regenerate` → 新一轮 `conclusion` 事件刷新结论区【SPEC A8 · T-RAG 范围重跑行】。

---

## 3. 数据流端到端时序

### 3.1 主路径（含 A5 闭环一票否决段）

| # | 用户操作 / 系统动作 | API | 状态迁移 | SSE 事件 | 前端区块更新 | 锚点 |
|---|--------------------|-----|----------|----------|--------------|------|
| 1 | 输入 URL 点「开始调研」 | POST /api/task → `{task_id}` 立即返回 | →Pending | — | 按钮置忙、三区块空态骨架 | 【SPEC A1 · PRD §3.1】 |
| 2 | Supervisor 调起对外子图 | — | Pending→Fetching | `state` + `progress 10` | 进度条 10% | 【PRD §6.1/6.3】 |
| 3 | n2 抓取+截图完成 | — | Fetching→Parsing | `state` + `progress 50` | 进度 50%；**Step 1 渲染截图缩略图+标题/Meta/状态码** | 【SPEC A2】 |
| 4 | n4/n5 切分+向量逐块完成 | — | 保持 Parsing | `chunk` × N | **Step 2 逐条追加 pre_chunks**（含 section_path/xpath） | 【SPEC A3】 |
| 5 | n6 Payload 转交对内 | — | Parsing→RAGing | `state` | — | 【PRD §6.3】 |
| 6 | m2 检索 → m3 生成结论 | — | 保持 RAGing | — | —（内部计算） | 【PRD §5.1/5.2】 |
| 7 | m4 模拟 POST 内部系统，回调 `ticket_id` | — | RAGing→Done | `state` + `progress 100` + `conclusion` | **Step 3 结论卡片**；**页面底部「已模拟写入内部系统（工单号：xxx）」= A5 闭环，工单号与 Tool Node 回调一致** | 【SPEC A4/A5 · PRD §8.3 · T-RAG 验收 Tool Node 闭环行】 |
| 8 | （admin 可选）点「重新生成」 | POST /api/task/{id}/regenerate | RAGing→Done（新一轮） | `conclusion`（新） | Step 3 刷新新结论，不回写旧结果 | 【SPEC A8 · T-RAG 验收重跑用例行】 |

### 3.2 失败分支时序（终态收敛 · SPEC A9）

| 触发 | 断点 | 状态终态 | SSE | 用户可见 | 锚点 |
|------|------|----------|-----|----------|------|
| 抓取超时 | n2 | Error | `error{FETCH_TIMEOUT}` | 「目标页面抓取超时，请稍后重试」 | 【SPEC FP-1】 |
| 反爬拦截 | n2 | Error | `error{ANTI_BOT}` | 「目标站点拒绝访问（反爬拦截）」+ 状态码 | 【SPEC FP-2】 |
| 解析为空 | n3 → 全链照常 | Done | `chunk` 无 + `conclusion{insufficient_info:true}` | 切片区「未提取到有效内容」+ 信息不足结论；**不调多模态** | 【SPEC FP-3】 |
| 非法 URL | POST 入口 / n1 | 不创建任务 / Error | 4xx / `error{URL_REJECTED}` | 「请输入合法的目标 URL」/「目标 URL 不被允许」 | 【T-WEB/T-ACQ 失败路径】 |
| Embedding 失败 | n5 | Error | `error{EMBED_FAILED}` | 「向量化失败，请稍后重试」 | 【T-ACQ 失败路径】 |
| 契约违例 | m1 | Error | `error{CONTRACT_VIOLATION}` | 「数据契约异常」 | 【T-RAG 失败路径】 |
| 生成重试耗尽 | m3 | Error | `error{GENERATE_FAILED}` | 「结论生成失败」 | 【T-RAG 失败路径】 |
| 回填失败 | m4 | Done(回填失败) | `conclusion`（receipt.status=failed） | 结论卡片照出 + 底部「模拟写入失败：原因」 | 【SPEC FP-4】 |
| SSE 中断 | 客户端 | 不变 | 重连后快照补拉 | 「连接中断，正在重连」→ 超上限提示刷新 | 【SPEC FP-5】 |
| 内存逼近阈值 | m2 | 不变（继续） | 无（用户无感知） | 降级日志可查（截断 Top-K） | 【SPEC FP-6】 |

---

## 4. 铁律映射表

| 铁律（PRD §1.2 · SPEC R3） | 技术落点（≥2） | 锚点 |
|---------------------------|----------------|------|
| **一、代码解析优先**（DOM/CSS 可提取则禁多模态；截图仅留痕复核） | ① n3 parse_dom 为唯一内容提取路径，BeautifulSoup + CSS 语义推断；对外子图非范围首行即「多模态/视觉大模型调用（违反即返工）」；验收含全流程日志 grep 无多模态调用【T-ACQ 非范围/验收铁律一审计行】 ② 截图职责封闭为「落盘 + `/static` 展示 + 人工复核」三用途，无任何以截图为输入的模型调用节点（n2 仅 `screenshot_path` 落盘）【SPEC A6 · PRD §4.4】 ③ **「解析为空不降级多模态」执行位置 = n3 出口与 m3 入口两处钉死**：n3 空 blocks 直接以空 `pre_chunks` 流转（无降级分支代码路径），m3 对空 chunks 产出 `insufficient_info` 结论——处置固定为「空流转 + 信息不足」而非视觉模型回退【SPEC FP-3 · T-ACQ R3 铁律一边界 · T-RAG 范围空 chunks 行】 | 【SPEC A6 · FP-3 · R3】 |
| **二、性能左移（胖采集）** | ① 解析（n3）、切分（n4）、Embedding（n5）、截图（n2）全部在对外子图；对内子图 m1 校验 Payload 必含 `embedding`，缺失即契约违例【T-ACQ 范围 · T-RAG 失败路径契约行】 ② 对内进程**不加载任何 Embedding 模型**，验收含「对内进程无 Embedding 模型加载」审计行【T-RAG 验收禁 Rerank 审计行 · R3 铁律二边界】 | 【SPEC 范围 1/2 · R3】 |
| **三、瘦内耗（2核4G）** | ① 向量库选 FAISS 进程内库、零额外服务；Qdrant 等独立进程 V1 禁入（检索接口抽象留 V2 迁移）【SPEC R2 分叉二 · T-RAG R2 · 非范围常驻重服务行】 ② 禁用 Rerank + LLM 重试 ≤2 次防风暴 + 唯一降级手段 = 截断 Top-K【SPEC 非范围 7 · FP-6 · T-RAG R3】 ③ A7 数值钉死：容器 2CPU/4096MB 限额、每 1s 采样 RSS、峰值 ≤ 3072MB、数据留档【T-RAG 验收 A7 行 · 审计观察项①】 | 【SPEC A7 · R2/R3 · FP-6】 |

---

## 一致性自检（10-spec 回填时执行）

- 全文选型（Flask 渲染 / FastAPI API+SSE / LangGraph Supervisor+双子图 / Playwright+CDP / BS4 / FAISS / 轻量 Embedding / 禁 Rerank / 模拟回填）与 SPEC signed 及三个 task 钉死项逐项对齐，无新分叉决策。
- 两处对 PRD §6.2 示例的**字段扩展**（`extracted_meta.http_status`、`pre_chunks[].section_path`/`token_count`）均由 SPEC A2/A3 或 PRD §4.3 强制，属补齐非改写，已在 §1.5 表内逐字段标注。
- 未发现与 signed SPEC 的冲突项，**无「⚠️ 待 SPEC 修订」条目**。

---

## 5. 决策记录（2026-09-09 人决 · 00 落盘）

| # | 决策 | 结论 | 理由 / 影响面 |
|---|------|------|---------------|
| D1 | 前后端是否分库 | **否 · 单仓 monorepo**：`git@github.com:Cyning12/grab-web-agent.git` | PRD §2.2 双轨是**子图/模块级**解耦而非仓库级；前端仅 Flask 模板 + vanilla JS（§2.1），无独立构建链；本地运行（D3）无分库收益。V2 前端独立 SPA 时再议 |
| D2 | LLM / Embedding API 服务商 | **SiliconFlow** | 对内结论生成（with_structured_output）+ 对外/对内 Embedding 统一走 SiliconFlow API；`SILICONFLOW_API_KEY` 经环境变量注入、不落盘明文【T-RAG 非范围】；具体模型选型（生成 / Embedding 各一）为 30 开工第一个人工确认项（原 SPEC residual_risks ④ 的落点） |
| D3 | 发布/部署 | **V1 仅本地运行**，不考虑发布 | §1.6 部署节降级为本地拓扑说明；A7 docker 限额验收保留（本地 docker 可执行）；远程仓仅作代码备份/协作，不配 CI 部署。远程已首推（2026-09-09 人执） |
| D4 | MVP 验证场景 | **实时股票页抓取（对外）+ 财报内部文档（对内）** | 对外目标页 ×2：`https://quote.eastmoney.com/sz000858.html`（五粮液）、`https://quote.eastmoney.com/sz300810.html`（中科海讯）；对内语料来源：巨潮全文检索（五粮液 / 中科海讯），样例已人工保存。SPEC 通用「竞品/行业调研」表述的场景实例化，非范围变更。**D4 修订注（2026-09-09 · task_fetch_render_wait_lite）**：真机验收发现标准页触发滑块验证且字段 JS 异步未渲染即解析，对外目标页默认切换为 concept 极速版 `https://quote.eastmoney.com/concept/sz000858.html` / `https://quote.eastmoney.com/concept/sz300810.html`（`.env.example` TASK_TARGET_URLS 同步）；fetch 节点增加渲染完成确认 + 滑块覆盖层检出（ANTI_BOT 终态） |
| D5 | SiliconFlow 模型选型 | 生成：`deepseek-ai/DeepSeek-V4-Flash`；Embedding：`bge-m3`（BAAI/bge-m3） | 人决（P2 闭环）；全部经 `.env` 可配置，不落盘明文 Key；30 施工以 env 变量名为唯一引用 |
| D6 | 内部语料目录约定 | `company/` 按**上市编号**命名区分（如 `company/sz000858/`、`company/sz300810/`） | 样例已人工保存；**后续**补抓取脚本（cninfo 全文检索 → 按编号落盘），单独立 task，不占本批 30 范围 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-09 | 00 起草极简壳（无初稿第一步） |
| 2026-09-09 | 10-spec 帽全量回填：§0 拓扑一图流 · §1 后端（API/SSE 枚举/注册表 + Supervisor + 双子图节点三行式）· §1.5 契约（Payload 字段表/结论 Schema/状态机触发表）· §1.6 资源部署 · §2 前端三区块与 SSE 重连 · §3 端到端时序（含 A5 闭环与失败分支）· §4 铁律映射；一致性自检无冲突；状态 draft-shell → draft |
| 2026-09-09 | 00 落盘人决 D1–D3（§5 决策记录）：单仓 monorepo · SiliconFlow · V1 仅本地运行；§1.6 同步修订 |
| 2026-09-09 | 00 落盘人决 D4–D6：MVP 场景=东财股票页 ×2 + 巨潮财报语料 · 模型=DeepSeek-V4-Flash + bge-m3 · company/ 语料目录约定 |
| 2026-09-09 | 30 补 D4 修订注（task_fetch_render_wait_lite）：对外目标页默认切 concept 极速版 + fetch 渲染完成确认/滑块检出 |
