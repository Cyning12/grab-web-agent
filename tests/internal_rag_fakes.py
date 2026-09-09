"""对内子图单测公共桩（非测试文件 · pytest 不收集）。

纪律：单测禁止真实调用 LLM/Embedding/外网 —— LLM 走 FakeLLMClient，检索走 FakeRetriever，
回填走 InMemoryOAEndpoint（内存模拟端点），rss_probe 注入常量。
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from app.graphs.internal_rag import InternalRagDeps
from app.services.rag.generator import ConclusionGenerator
from app.services.rag.retriever import RetrievedChunk
from app.services.rag.writeback import InMemoryOAEndpoint, MockWritebackClient

EMBED_DIM = 8


def make_embedding(seed: float = 1.0) -> list[float]:
    """确定性伪向量（对外轨预计算向量的 mock，对内不重算）。"""
    return [seed + i * 0.1 for i in range(EMBED_DIM)]


def make_chunk(i: int = 0) -> dict[str, Any]:
    return {
        "title": f"产品参数-{i}",
        "text": f"五粮液 2026 半年度营收与价格带片段 {i}",
        "embedding": make_embedding(float(i + 1)),
        "xpath": f"/html/body/div[{i}]/section",
        "section_path": f"正文/产品参数/{i}",
        "token_count": 512,
    }


def make_payload(
    url: str = "https://quote.eastmoney.com/sz000858.html", n_chunks: int = 2
) -> dict[str, Any]:
    """PRD §6.2 标准 Payload（mock · 字段逐一对齐架构 §1.5 表①）。"""
    return {
        "url": url,
        "screenshot_path": "mock-shot-000858.png",
        "extracted_meta": {
            "title": "五粮液(sz000858)股票行情",
            "price": "52.30元",
            "http_status": 200,
            "meta": {"description": "mock"},
        },
        "pre_chunks": [make_chunk(i) for i in range(n_chunks)],
    }


class FakeLLMClient:
    """openai 兼容客户端桩：返回固定 JSON 结论；fail=True 时恒抛错（生成失败路径）。"""

    def __init__(self, conclusion: dict[str, Any] | None = None, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail
        self.conclusion = conclusion
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages, response_format=None):
        self.calls += 1
        if self.fail:
            raise RuntimeError("mock llm down")
        data = self.conclusion or {
            "competitor_price": "52.30元",
            "risk_level": "中",
            "suggested_action": f"建议关注竞品价格带（第 {self.calls} 次生成）",
            "insufficient_info": False,
            "sources": [],
        }
        content = json.dumps(data, ensure_ascii=False)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeRetriever:
    """检索桩：记录 top_k / company_code 入参，返回确定分数序命中（无 Rerank）。"""

    def __init__(self, company_code: str = "000858") -> None:
        self.calls: list[dict[str, Any]] = []
        self.company_code = company_code

    def search(
        self, query_embedding, top_k: int, company_code: str | None = None
    ) -> list[RetrievedChunk]:
        self.calls.append({"top_k": top_k, "company_code": company_code})
        code = company_code or self.company_code
        return [
            RetrievedChunk(
                text=f"内部财报切片 {i}：价格带与风险提示",
                company_code=code,
                source_path=f"{code}/2026年半年度报告.pdf",
                score=0.95 - i * 0.05,
            )
            for i in range(top_k)
        ]


def make_deps(
    *,
    llm_fail: bool = False,
    oa_fail_status: int | None = None,
    rss_mb: float = 100.0,
    retriever: Any = None,
) -> InternalRagDeps:
    """组装全 mock 依赖（LLM/检索/回填/RSS 全部离线）。"""
    endpoint = InMemoryOAEndpoint(fail_status=oa_fail_status)
    return InternalRagDeps(
        retriever=retriever if retriever is not None else FakeRetriever(),
        generator=ConclusionGenerator(client=FakeLLMClient(fail=llm_fail)),
        writeback_client=MockWritebackClient(endpoint=endpoint),
        rss_probe=lambda: rss_mb,
    )
