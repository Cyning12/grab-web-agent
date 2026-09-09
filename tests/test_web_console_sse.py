"""Web 控制台 SSE 端到端联调测试（task_web_console_mvp · Mock 子图驱动 · 禁真实浏览器/LLM/外网）。

接线真值：Supervisor.execute_task 串 对外子图入口 -> 对内子图真实图（FakeLLM/FakeRetriever/
内存 OA 桩全离线），经任务注册表广播五类 SSE 事件。

覆盖：A1 事件序列 · A5 闭环（工单号与 Tool Node 回调一致）· A8 重新生成 ·
A9 失败注入三桩（超时/反爬/回填失败）· 空解析信息不足 · SSE 断线重连补拉。
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api.main import app as fastapi_app
from app.graphs.internal_rag import InternalRagDeps, run_internal_rag
from app.services.acquisition import AntiBotDetected, FetchTimeout, make_error
from app.services.console.registry import TERMINAL_STATUSES, TaskRegistry
from app.services.rag.generator import ConclusionGenerator
from app.services.rag.writeback import InMemoryOAEndpoint, MockWritebackClient
from tests.internal_rag_fakes import FakeLLMClient, FakeRetriever, make_payload

TARGET_URL = "https://quote.eastmoney.com/sz000858.html"


def make_rag_runner(*, oa_fail_status: int | None = None, llm_fail: bool = False):
    """对内子图真实图 + 全 mock 依赖；返回 (runner, endpoint) 供工单号闭环断言。"""
    endpoint = InMemoryOAEndpoint(fail_status=oa_fail_status)
    deps = InternalRagDeps(
        retriever=FakeRetriever(),
        generator=ConclusionGenerator(client=FakeLLMClient(fail=llm_fail)),
        writeback_client=MockWritebackClient(endpoint=endpoint),
        rss_probe=lambda: 100.0,
    )

    def runner(payload: dict) -> dict:
        return run_internal_rag(payload, deps)

    return runner, endpoint


@pytest.fixture()
def client():
    fastapi_app.state.registry = TaskRegistry()
    fastapi_app.state.acq_runner = None
    fastapi_app.state.rag_runner = None
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.state.registry = TaskRegistry()
    fastapi_app.state.acq_runner = None
    fastapi_app.state.rag_runner = None


def wire_success(client, n_chunks: int = 3, **rag_kwargs):
    """接 Mock 对外桩 + 对内真实图，返回 (task_id, endpoint)。"""
    runner, endpoint = make_rag_runner(**rag_kwargs)
    fastapi_app.state.acq_runner = lambda url: {"payload": make_payload(url=url, n_chunks=n_chunks)}
    fastapi_app.state.rag_runner = runner
    resp = client.post("/api/task", json={"url": TARGET_URL})
    assert resp.status_code == 201
    return resp.json()["task_id"], endpoint


def collect_sse(client, task_id: str, stop_after_terminals: int = 1, max_events: int = 100):
    """流式读取 SSE 并解析为 [(event, data)]；第 N 个 state 终态（Done/Error）后停止。

    error 事件不单独计终态（服务端 error 先于 state Error 发出）；未知任务流由服务端
    在 TASK_NOT_FOUND 后直接关闭，iter_lines 自然结束。
    """
    events: list[tuple[str, dict]] = []
    terminals = 0
    with client.stream("GET", f"/api/task/{task_id}/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        event_name = None
        for line in resp.iter_lines():
            if line.startswith("event: "):
                event_name = line[len("event: "):]
            elif line.startswith("data: ") and event_name:
                data = json.loads(line[len("data: "):])
                events.append((event_name, data))
                if event_name == "state" and data.get("status") in TERMINAL_STATUSES:
                    terminals += 1
                    if terminals >= stop_after_terminals:
                        return events
                event_name = None
            if len(events) >= max_events:
                break
    return events


def states(events):
    return [d["status"] for e, d in events if e == "state"]


def progresses(events):
    return [d["percent"] for e, d in events if e == "progress"]


# --- A1 异步提交 + SSE 事件序列 -------------------------------------------------


def test_a1_sse_event_sequence(client):
    task_id, _ = wire_success(client)
    events = collect_sse(client, task_id)
    # 状态机迁移依次可观：Pending → Fetching → Parsing → RAGing → Done（PRD §6.3）
    assert states(events) == ["Pending", "Fetching", "Parsing", "RAGing", "Done"]
    # 进度三档依次可观（PRD §6.1；Parsing→RAGing 不增档）
    assert progresses(events) == [10, 50, 100]
    # chunk 事件逐条实时（A3 数据源）
    chunks = [d for e, d in events if e == "chunk"]
    assert len(chunks) == 3
    for i, c in enumerate(chunks):
        assert c["index"] == i
        assert c["title"] and c["text"]
        assert c["section_path"] and c["xpath"]  # SPEC A3 可溯源字段
        assert 512 <= c["token_count"] <= 1024
    assert sum(1 for e, _ in events if e == "conclusion") == 1


# --- A5 闭环（一票否决）：工单号非空且与对内 Tool Node 回调一致 --------------------


def test_a5_closed_loop_ticket_matches_writeback_callback(client):
    task_id, endpoint = wire_success(client)
    events = collect_sse(client, task_id)
    conclusions = [d for e, d in events if e == "conclusion"]
    assert len(conclusions) == 1
    receipt = conclusions[0]["receipt"]
    assert receipt["status"] == "success"
    assert receipt["ticket_id"]  # 非空
    assert receipt["mock"] is True
    # 与对内 Tool Node 模拟回调返回值一致（内存 OA 端点已发工单台账）
    assert receipt["ticket_id"] == endpoint.issued_tickets[-1]
    # 结论卡片三字段（A4 数据源）
    conclusion = conclusions[0]["conclusion"]
    assert {"competitor_price", "risk_level", "suggested_action"} <= set(conclusion)
    assert conclusion["insufficient_info"] is False
    # 注册表终态收敛
    snapshot = fastapi_app.state.registry.snapshot(task_id)
    assert snapshot["status"] == "Done" and snapshot["progress"] == 100
    assert snapshot["receipt"]["ticket_id"] == receipt["ticket_id"]


# --- SSE 断线重连补拉（SPEC FP-5 · 架构 §2.3） -------------------------------------


def test_sse_reconnect_replays_full_state(client):
    """任务完成后再次订阅：回放全量历史（补拉语义），含 10/50/100 与结论。"""
    task_id, endpoint = wire_success(client)
    first = collect_sse(client, task_id)
    assert states(first)[-1] == "Done"
    replay = collect_sse(client, task_id)  # 断线重连等价：以 task_id 重新订阅
    assert states(replay) == states(first)
    assert progresses(replay) == [10, 50, 100]
    assert [d for e, d in replay if e == "conclusion"][0]["receipt"]["ticket_id"] == endpoint.issued_tickets[-1]


def test_sse_unknown_task_returns_task_not_found(client):
    events = collect_sse(client, "ghost-task")
    assert events == [("error", events[0][1])]
    assert events[0][1]["code"] == "TASK_NOT_FOUND"
    assert events[0][1]["retryable"] is False


# --- A9 失败注入三桩（超时 / 反爬 / 回填失败） --------------------------------------


def test_a9_fetch_timeout_lands_error(client):
    fastapi_app.state.acq_runner = lambda url: {
        "error": make_error(FetchTimeout(url=url), "fetch_page")
    }
    runner, _ = make_rag_runner()
    fastapi_app.state.rag_runner = runner
    task_id = client.post("/api/task", json={"url": TARGET_URL}).json()["task_id"]
    events = collect_sse(client, task_id)
    errors = [d for e, d in events if e == "error"]
    assert errors and errors[0]["code"] == "FETCH_TIMEOUT"
    assert errors[0]["user_message"] == "目标页面抓取超时，请稍后重试"
    assert states(events)[-1] == "Error"  # 终态不滞留中间态
    assert fastapi_app.state.registry.snapshot(task_id)["status"] == "Error"


def test_a9_anti_bot_lands_error(client):
    fastapi_app.state.acq_runner = lambda url: {
        "error": make_error(AntiBotDetected(url=url), "fetch_page")
    }
    runner, _ = make_rag_runner()
    fastapi_app.state.rag_runner = runner
    task_id = client.post("/api/task", json={"url": TARGET_URL}).json()["task_id"]
    events = collect_sse(client, task_id)
    errors = [d for e, d in events if e == "error"]
    assert errors and errors[0]["code"] == "ANTI_BOT"
    assert errors[0]["user_message"] == "目标站点拒绝访问（反爬拦截）"
    assert states(events)[-1] == "Error"


def test_a9_writeback_failure_done_with_detail(client):
    """回填 500 桩：结论照出 + receipt 标失败原因 + Done(回填失败)，底部不出现工单号。"""
    task_id, endpoint = wire_success(client, oa_fail_status=500)
    events = collect_sse(client, task_id)
    conclusion = [d for e, d in events if e == "conclusion"][0]
    assert conclusion["receipt"]["status"] == "failed"
    assert conclusion["receipt"]["reason"]  # 「模拟写入失败：原因」数据源
    assert conclusion["receipt"]["ticket_id"] is None
    assert conclusion["conclusion"]["competitor_price"]  # 回填失败不丢结论（SPEC FP-4）
    done = [d for e, d in events if e == "state" and d["status"] == "Done"][0]
    assert done["detail"] == "回填失败"
    assert progresses(events)[-1] == 100
    assert endpoint.issued_tickets == []


def test_a9_generate_failed_lands_error(client):
    task_id, _ = wire_success(client, llm_fail=True)
    events = collect_sse(client, task_id)
    errors = [d for e, d in events if e == "error"]
    assert errors and errors[0]["code"] == "GENERATE_FAILED"  # 重试 ≤2 耗尽
    assert states(events)[-1] == "Error"


# --- 空解析路径（SPEC FP-3：不降级多模态，信息不足结论） -----------------------------


def test_empty_chunks_yields_insufficient_info(client):
    task_id, endpoint = wire_success(client, n_chunks=0)
    events = collect_sse(client, task_id)
    assert [d for e, d in events if e == "chunk"] == []  # 切片区无条目 -> 前端空态
    conclusion = [d for e, d in events if e == "conclusion"][0]
    assert conclusion["conclusion"]["insufficient_info"] is True
    assert states(events)[-1] == "Done"
    assert conclusion["receipt"]["ticket_id"] == endpoint.issued_tickets[-1]


# --- A8 管理员「重新生成」：同一 Payload 重跑对内子图并刷新结论区 ---------------------


def test_a8_regenerate_reruns_internal_rag(client):
    task_id, endpoint = wire_success(client)
    first = collect_sse(client, task_id)
    first_ticket = [d for e, d in first if e == "conclusion"][0]["receipt"]["ticket_id"]

    resp = client.post(f"/api/task/{task_id}/regenerate")
    assert resp.status_code == 200 and resp.json()["status"] == "regenerating"
    # 新一轮事件：state RAGing(重新生成) -> conclusion(新工单) -> progress 100 -> state Done
    events = collect_sse(client, task_id, stop_after_terminals=2)
    regen_states = [d for e, d in events if e == "state"]
    assert any(s["status"] == "RAGing" and s.get("detail") == "重新生成" for s in regen_states)
    conclusions = [d for e, d in events if e == "conclusion"]
    assert len(conclusions) == 2
    new_ticket = conclusions[-1]["receipt"]["ticket_id"]
    assert new_ticket and new_ticket != first_ticket  # 不回写旧结果
    assert endpoint.issued_tickets == [first_ticket, new_ticket]
    snapshot = fastapi_app.state.registry.snapshot(task_id)
    assert snapshot["receipt"]["ticket_id"] == new_ticket  # 注册表整体替换为新结论
