"""对内子图（Internal RAG · 瘦内耗）。

链（架构 §1.4 逐字）：receive_validate -> retrieve_topk -> generate_conclusion -> writeback_tool

- m1 receive_validate：PRD §6.2 Payload Schema 校验（缺 embedding 即契约违例 · 禁重算 Embedding 铁律二）
- m2 retrieve_topk：FAISS Top-K 混合检索（向量+标量过滤拼接 · 禁 Rerank）；内存逼近阈值
  降级 = 截断 Top-K（唯一允许降级手段 · SPEC FP-6）并记降级日志
- m3 generate_conclusion：with_structured_output 等效结论 JSON（重试 ≤2 防风暴）；
  空 chunks → 「信息不足」结论（SPEC FP-3 不中断）
- m4 writeback_tool（Tool Node）：模拟 POST 回填内部系统，捕获回调（成功/失败/工单号）；
  回填失败不丢结论，终态 Done(回填失败)（SPEC FP-4）；发 RAGing→Done 迁移事件（进度 100%）
"""

from __future__ import annotations

import logging
import operator
import os
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, TypedDict

import numpy as np
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app import config
from app.services.rag.generator import ConclusionGenerator, GenerateFailedError
from app.services.rag.resources import RAG_RSS_DEGRADE_MB, current_rss_mb
from app.services.rag.retriever import (
    Retriever,
    build_index_from_corpus,
    derive_company_code,
)
from app.services.rag.schemas import Conclusion, Payload, Receipt
from app.services.rag.writeback import MockWritebackClient

_logger = logging.getLogger(__name__)

RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
RAG_TOP_K_DEGRADED: int = int(os.getenv("RAG_TOP_K_DEGRADED", "2"))


class InternalRagState(TypedDict, total=False):
    """对内子图 State（字段名对齐架构 §1.4 各节点三行式输入/输出）。

    events：状态上报钩子（RAGing→Done 迁移 / progress 100 / conclusion / error），
    供 Supervisor/SSE 消费（task 范围「子图状态上报钩子」行 · 验收末行）。
    """

    payload: dict[str, Any]
    payload_validated: Payload
    context_chunks: list[dict[str, Any]]
    degraded: bool
    conclusion: Conclusion
    receipt: Receipt
    error: dict[str, Any]
    events: Annotated[list[dict[str, Any]], operator.add]


@dataclass
class InternalRagDeps:
    """可注入依赖（单测全 mock · 默认走 SiliconFlow API + 内存模拟回填桩）。"""

    retriever: Retriever | None = None
    generator: ConclusionGenerator | None = None
    writeback_client: MockWritebackClient | None = None
    rss_probe: Callable[[], float] = current_rss_mb
    top_k: int = RAG_TOP_K
    degraded_top_k: int = RAG_TOP_K_DEGRADED
    degrade_threshold_mb: float = RAG_RSS_DEGRADE_MB
    corpus_dir: str = config.COMPANY_DIR
    _embedder: Any = field(default=None, repr=False)

    def _default_embed(self, texts: list[str]) -> list[list[float]]:
        """语料索引构建用 Embedding（SiliconFlow bge-m3 API · D5；非 Payload 重算，铁律二不违例）。"""
        if self._embedder is None:
            from openai import OpenAI

            self._embedder = OpenAI(
                base_url=config.SILICONFLOW_BASE_URL, api_key=config.SILICONFLOW_API_KEY
            )
        resp = self._embedder.embeddings.create(model=config.EMBEDDING_MODEL, input=texts)
        return [d.embedding for d in resp.data]

    def get_retriever(self) -> Retriever | None:
        """惰性构建默认 FAISS 索引（语料为空/构建失败 → None，检索降级为空 context 不中断）。"""
        if self.retriever is not None:
            return self.retriever
        try:
            self.retriever = build_index_from_corpus(self.corpus_dir, self._default_embed)
        except Exception as exc:
            _logger.warning("内部知识库索引构建失败，以空 context 继续：%s", exc)
            self.retriever = None
        return self.retriever


# --- m1 receive_validate -----------------------------------------------------


def _m1_receive_validate(state: InternalRagState) -> dict[str, Any]:
    events: list[dict[str, Any]] = [
        {"event": "state", "data": {"status": "RAGing", "detail": "receive_validate"}}
    ]
    try:
        payload = Payload.model_validate(state.get("payload") or {})
    except ValidationError as exc:
        _logger.error("Payload 契约违例（CONTRACT_VIOLATION）：%s", exc)
        err = {"code": "CONTRACT_VIOLATION", "message": str(exc), "retryable": True}
        return {"error": err, "events": events + [{"event": "error", "data": err}]}
    return {"payload_validated": payload, "events": events}


# --- m2 retrieve_topk --------------------------------------------------------


def _mean_embedding(chunks: list[Any]) -> list[float]:
    """对 pre_chunks 预计算向量做均值池化为查询向量（不重算 Embedding · 铁律二）。"""
    arr = np.asarray([c.embedding for c in chunks], dtype=np.float32)
    return arr.mean(axis=0).tolist()


def _make_m2_retrieve_topk(deps: InternalRagDeps):
    def retrieve_topk(state: InternalRagState) -> dict[str, Any]:
        payload: Payload = state["payload_validated"]
        chunks = payload.pre_chunks
        if not chunks:
            return {"context_chunks": [], "degraded": False}

        # 降级判定（SPEC FP-6 · 唯一手段=截断 Top-K）
        rss_mb = deps.rss_probe()
        degraded = rss_mb >= deps.degrade_threshold_mb
        k = deps.degraded_top_k if degraded else deps.top_k
        if degraded:
            _logger.warning(
                "降级事件：RSS %.0fMB 逼近阈值 %.0fMB，截断 Top-K %d→%d（SPEC FP-6）",
                rss_mb, deps.degrade_threshold_mb, deps.top_k, deps.degraded_top_k,
            )

        retriever = deps.get_retriever()
        if retriever is None:
            return {"context_chunks": [], "degraded": degraded}

        query = _mean_embedding(chunks)
        company_code = derive_company_code(payload.url)
        hits = retriever.search(query, k, company_code)
        context = [
            {
                "text": h.text,
                "company_code": h.company_code,
                "source_path": h.source_path,
                "score": h.score,
            }
            for h in hits
        ]
        return {"context_chunks": context, "degraded": degraded}

    return retrieve_topk


# --- m3 generate_conclusion --------------------------------------------------


def _make_m3_generate_conclusion(deps: InternalRagDeps):
    def generate_conclusion(state: InternalRagState) -> dict[str, Any]:
        payload: Payload = state["payload_validated"]
        generator = deps.generator or ConclusionGenerator()
        try:
            conclusion = generator.generate(state.get("context_chunks", []), payload)
        except GenerateFailedError as exc:
            _logger.error("结论生成失败（GENERATE_FAILED）：%s", exc)
            err = {"code": "GENERATE_FAILED", "message": str(exc), "retryable": True}
            return {"error": err, "events": [{"event": "error", "data": err}]}
        if not conclusion.insufficient_info:
            conclusion.sources = sorted(
                {c["source_path"] for c in state.get("context_chunks", []) if c.get("source_path")}
            )
        return {"conclusion": conclusion}

    return generate_conclusion


# --- m4 writeback_tool（Tool Node · 末节点） -----------------------------------


def _make_m4_writeback_tool(deps: InternalRagDeps):
    def writeback_tool(state: InternalRagState) -> dict[str, Any]:
        conclusion: Conclusion = state["conclusion"]
        client = deps.writeback_client or MockWritebackClient()
        receipt = client.post(conclusion)  # 回填失败不丢结论，仅回执标失败（SPEC FP-4）
        detail = "回填失败" if receipt.status == "failed" else None
        events = [
            {
                "event": "conclusion",
                "data": {"conclusion": conclusion.model_dump(), "receipt": receipt.model_dump()},
            },
            {"event": "progress", "data": {"percent": 100}},
            {"event": "state", "data": {"status": "Done", "detail": detail}},
        ]
        return {"receipt": receipt, "events": events}

    return writeback_tool


# --- 图编排 -------------------------------------------------------------------


def _route_after_validate(state: InternalRagState) -> str:
    return END if state.get("error") else "retrieve_topk"


def _route_after_generate(state: InternalRagState) -> str:
    return END if state.get("error") else "writeback_tool"


def build_internal_rag_graph(deps: InternalRagDeps | None = None):
    """编译对内子图（四节点链式 + 契约违例/生成失败短路至终态）。"""
    deps = deps or InternalRagDeps()
    graph = StateGraph(InternalRagState)
    graph.add_node("receive_validate", _m1_receive_validate)
    graph.add_node("retrieve_topk", _make_m2_retrieve_topk(deps))
    graph.add_node("generate_conclusion", _make_m3_generate_conclusion(deps))
    graph.add_node("writeback_tool", _make_m4_writeback_tool(deps))
    graph.add_edge(START, "receive_validate")
    graph.add_conditional_edges("receive_validate", _route_after_validate)
    graph.add_edge("retrieve_topk", "generate_conclusion")
    graph.add_conditional_edges("generate_conclusion", _route_after_generate)
    graph.add_edge("writeback_tool", END)
    return graph.compile()


def run_internal_rag(payload: dict[str, Any], deps: InternalRagDeps | None = None) -> dict[str, Any]:
    """对内子图入口（每次调用编译新图、全新 State —— 「重新生成」即以同一 Payload 再次调用，
    天然不回写旧结果 · SPEC A8 / T-RAG 验收重跑用例行）。"""
    return build_internal_rag_graph(deps).invoke({"payload": payload})
