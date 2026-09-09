"""可选 live 冒烟（默认关闭 · RAG_LIVE_SMOKE=1 才跑，真实调用 SiliconFlow API）。

单测纪律不受影响：本文件默认 skip；开启时验证真实链路 —— 真实 Embedding API 构造
Payload/语料索引 + 真实生成模型结论 + 内存模拟回填。Key 只经 env（app.config），不打印。
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RAG_LIVE_SMOKE") != "1", reason="live 冒烟默认关闭（RAG_LIVE_SMOKE=1 开启）"
)

from app import config  # noqa: E402
from app.graphs.internal_rag import InternalRagDeps, run_internal_rag  # noqa: E402
from app.services.rag.generator import ConclusionGenerator  # noqa: E402
from app.services.rag.retriever import CorpusDoc, FaissVectorStore  # noqa: E402
from app.services.rag.writeback import InMemoryOAEndpoint, MockWritebackClient  # noqa: E402


def _embed(texts):
    from openai import OpenAI

    client = OpenAI(base_url=config.SILICONFLOW_BASE_URL, api_key=config.SILICONFLOW_API_KEY)
    resp = client.embeddings.create(model=config.EMBEDDING_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def test_live_smoke_end_to_end():
    assert config.SILICONFLOW_API_KEY, "缺 SILICONFLOW_API_KEY（env 注入，不落盘明文）"
    # 语料侧：2 条 mock CorpusDoc 走真实 bge-m3 索引（全量 company/ PDF 索引属 live 手测，不在冒烟内）
    docs = [
        CorpusDoc(text="五粮液 2026 半年度报告：营收稳健，核心单品价格带 500-600 元。", company_code="000858", source_path="000858/mock.md"),
        CorpusDoc(text="中科海讯 2026 半年度报告：特种电子信息装备供应商。", company_code="300810", source_path="300810/mock.md"),
    ]
    store = FaissVectorStore.from_docs(docs, _embed)
    # Payload 侧：embedding 由真实 Embedding API 预计算（模拟对外轨产出，对内不重算）
    vec = _embed(["五粮液股票价格行情走势分析"])[0]
    payload = {
        "url": "https://quote.eastmoney.com/sz000858.html",
        "screenshot_path": "live-smoke.png",
        "extracted_meta": {"title": "五粮液(sz000858)股票行情", "price": "", "http_status": 200},
        "pre_chunks": [
            {
                "title": "行情概览",
                "text": "五粮液股票价格行情走势分析",
                "embedding": vec,
                "xpath": "/html/body/div[1]",
                "section_path": "正文/行情概览",
                "token_count": 512,
            }
        ],
    }
    deps = InternalRagDeps(
        retriever=store,
        generator=ConclusionGenerator(),
        writeback_client=MockWritebackClient(InMemoryOAEndpoint()),
    )
    result = run_internal_rag(payload, deps=deps)
    assert "error" not in result
    c = result["conclusion"]
    assert c.competitor_price and c.risk_level in ("低", "中", "高") and c.suggested_action
    assert result["receipt"]["status"] == "success" and result["receipt"]["ticket_id"]
