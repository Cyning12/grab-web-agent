"""对内子图主链路单测（全 mock：LLM/检索/回填/RSS 均离线 · test_strategy: required）。

覆盖验收行：
- 结构化结论三字段齐全且过内部 Schema（SPEC A4）
- Tool Node 闭环：工单号非空且与回调一致（SPEC A5 对内侧一票否决）
- 空 chunks → 「信息不足」结论不中断（SPEC FP-3）
- 回填 500 桩 → 结论保留 + 回执标失败 + Done(回填失败)（SPEC FP-4）
- LLM 失败有限重试（总尝试 ≤2，防重试风暴）→ GENERATE_FAILED
- 同一 Payload 重跑：新结论、不回写旧结果（SPEC A8「重新生成」入口）
- 状态上报钩子：RAGing → Done 迁移事件（进度 100）供 Supervisor/SSE 消费
"""

from internal_rag_fakes import FakeLLMClient, FakeRetriever, make_deps, make_payload
from app.graphs.internal_rag import run_internal_rag
from app.services.rag.generator import ConclusionGenerator
from app.services.rag.schemas import Conclusion, Receipt
from app.services.rag.writeback import InMemoryOAEndpoint, MockWritebackClient


def _state_events(result, event_name):
    return [e["data"] for e in result["events"] if e["event"] == event_name]


def test_happy_path_conclusion_schema_and_three_fields():
    result = run_internal_rag(make_payload(), deps=make_deps())
    assert "error" not in result
    conclusion = result["conclusion"]
    # SPEC A4 三字段齐全 + 通过内部 API Schema 校验
    validated = Conclusion.model_validate(conclusion.model_dump())
    assert validated.competitor_price == "52.30元"
    assert validated.risk_level in ("低", "中", "高")
    assert validated.suggested_action
    assert validated.insufficient_info is False
    assert validated.sources  # 溯源列表来自检索命中 source_path


def test_writeback_tool_node_ticket_closed_loop():
    endpoint = InMemoryOAEndpoint()
    deps = make_deps()
    deps.writeback_client = MockWritebackClient(endpoint=endpoint)
    result = run_internal_rag(make_payload(), deps=deps)
    receipt = Receipt.model_validate(result["receipt"].model_dump())
    # SPEC A5 闭环一票否决（对内侧）：工单号非空且与 Tool Node 回调一致
    assert receipt.status == "success"
    assert receipt.ticket_id and receipt.ticket_id in endpoint.issued_tickets
    assert receipt.mock is True


def test_state_transition_events_raging_to_done():
    result = run_internal_rag(make_payload(), deps=make_deps())
    states = _state_events(result, "state")
    assert states[0]["status"] == "RAGing"
    assert states[-1]["status"] == "Done" and states[-1]["detail"] is None
    assert any(p["percent"] == 100 for p in _state_events(result, "progress"))
    conclusion_events = _state_events(result, "conclusion")
    assert conclusion_events and conclusion_events[0]["receipt"]["ticket_id"]


def test_empty_chunks_produce_insufficient_info_conclusion():
    endpoint = InMemoryOAEndpoint()
    deps = make_deps()
    deps.writeback_client = MockWritebackClient(endpoint=endpoint)
    payload = make_payload(n_chunks=0)  # 对外解析为空失败路径（SPEC FP-3）：正常流转
    result = run_internal_rag(payload, deps=deps)
    assert "error" not in result  # 不视为错误，任务不中断
    conclusion = result["conclusion"]
    assert conclusion.insufficient_info is True
    Conclusion.model_validate(conclusion.model_dump())  # 占位文案仍过同一 Schema
    # 空 chunks 不触发检索与 LLM
    assert deps.retriever.calls == []
    assert deps.generator._client.calls == 0
    # 链路继续走到模拟回填，工单号照常下发
    assert result["receipt"].status == "success" and result["receipt"].ticket_id


def test_writeback_500_keeps_conclusion_and_marks_receipt_failed():
    deps = make_deps(oa_fail_status=500)
    result = run_internal_rag(make_payload(), deps=deps)
    assert "error" not in result  # 回填失败不丢结论（SPEC FP-4）
    Conclusion.model_validate(result["conclusion"].model_dump())
    receipt = result["receipt"]
    assert receipt.status == "failed" and receipt.ticket_id is None
    assert receipt.reason  # 回执标注失败原因
    # 终态 Done(回填失败)：state 事件 detail 区分
    states = _state_events(result, "state")
    assert states[-1]["status"] == "Done" and states[-1]["detail"] == "回填失败"


def test_llm_failure_retries_at_most_twice_then_generate_failed():
    fake_llm = FakeLLMClient(fail=True)
    deps = make_deps()
    deps.generator = ConclusionGenerator(client=fake_llm)
    result = run_internal_rag(make_payload(), deps=deps)
    assert result["error"]["code"] == "GENERATE_FAILED"
    assert fake_llm.calls <= 2  # 防重试风暴：总尝试 ≤2 次（SPEC A7 操作化）
    assert "receipt" not in result  # 短路终态 Error，不进入回填
    assert any(
        e["event"] == "error" and e["data"]["code"] == "GENERATE_FAILED" for e in result["events"]
    )


def test_rerun_same_payload_produces_new_conclusion_without_overwrite():
    deps = make_deps()
    payload = make_payload()
    first = run_internal_rag(payload, deps=deps)
    second = run_internal_rag(payload, deps=deps)  # SPEC A8：同一 Payload 重跑对内子图
    assert "error" not in first and "error" not in second
    # 产出新结论（生成器第 2 次调用）且不回写旧结果：两轮结论/工单各自独立
    assert first["conclusion"].suggested_action != second["conclusion"].suggested_action
    assert first["receipt"].ticket_id != second["receipt"].ticket_id
    assert first["receipt"].status == second["receipt"].status == "success"


def test_scalar_filter_company_code_passed_to_retriever():
    retriever = FakeRetriever()
    deps = make_deps(retriever=retriever)
    run_internal_rag(make_payload(url="https://quote.eastmoney.com/sz300810.html"), deps=deps)
    assert retriever.calls[0]["company_code"] == "300810"  # 向量+标量过滤拼接（D6 编号）
