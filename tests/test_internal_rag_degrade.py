"""降级用例（SPEC FP-6）：内存逼近阈值 → 截断 Top-K（唯一允许降级手段），
任务照常完成且日志含降级事件记录。"""

import logging

from internal_rag_fakes import FakeRetriever, make_deps, make_payload
from app.graphs.internal_rag import run_internal_rag


def test_memory_pressure_truncates_topk_and_logs_degradation(caplog):
    retriever = FakeRetriever()
    deps = make_deps(retriever=retriever, rss_mb=2600.0)  # ≥ 降级阈值 2560MB
    with caplog.at_level(logging.WARNING):
        result = run_internal_rag(make_payload(), deps=deps)
    assert "error" not in result  # 任务继续完成（质量降级）
    assert result["degraded"] is True
    assert retriever.calls[0]["top_k"] == deps.degraded_top_k  # Top-K 截断
    assert len(result["context_chunks"]) == deps.degraded_top_k
    assert any("降级事件" in rec.message for rec in caplog.records)  # 降级日志可观测


def test_normal_memory_uses_full_topk_without_degradation(caplog):
    retriever = FakeRetriever()
    deps = make_deps(retriever=retriever, rss_mb=100.0)
    with caplog.at_level(logging.WARNING):
        result = run_internal_rag(make_payload(), deps=deps)
    assert result["degraded"] is False
    assert retriever.calls[0]["top_k"] == deps.top_k
    assert not any("降级事件" in rec.message for rec in caplog.records)
