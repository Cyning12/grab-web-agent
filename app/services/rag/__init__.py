"""对内子图服务层（Internal RAG · 瘦内耗）。

模块职责：
- schemas：PRD §6.2 Payload 与结论/回执 Schema（架构 §1.5）
- retriever：FAISS Top-K 混合检索（禁 Rerank · 接口抽象留 V2 换 Qdrant）
- generator：with_structured_output 等效结论生成（JSON mode + Pydantic 强校验 · 重试 ≤2）
- writeback：模拟内部系统回填 Tool Node 桩（成功桩 / 500 桩）
- resources：RSS 采样与截断 Top-K 降级（SPEC A7 / FP-6）
"""
