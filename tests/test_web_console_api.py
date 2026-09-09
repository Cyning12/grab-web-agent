"""Web 控制台 API 层测试（task_web_console_mvp · 禁止真实浏览器/LLM/外网）。

覆盖：
- POST /api/task 入参校验（SSRF 白名单复用对外轨 · T-WEB 失败路径第 1 行业务行）
- 异步提交立即返回 task_id（SPEC A1 不经 HTTP 长等待）
- GET /api/task/{id} 快照补拉与 404
- 拓扑确认（验收末行）：Flask 进程零 /api/* 路由；API/SSE 端点仅在 FastAPI
- A8 角色视图：调研员 Step 3 不渲染；?role=admin 渲染 Step 3 + 重新生成按钮
- A5 页面侧静态断言：模板含闭环横幅文案模板且工单号取自 receipt.ticket_id
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app as fastapi_app
from app.services.console.registry import TaskRegistry
from app.web.app import app as flask_app

TEMPLATE = Path(__file__).resolve().parents[1] / "app" / "web" / "templates" / "index.html"


@pytest.fixture()
def client():
    """每测试全新注册表 + 默认（真实）子图入口槽位复位。"""
    fastapi_app.state.registry = TaskRegistry()
    fastapi_app.state.acq_runner = None
    fastapi_app.state.rag_runner = None
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.state.registry = TaskRegistry()
    fastapi_app.state.acq_runner = None
    fastapi_app.state.rag_runner = None


def _fake_acq_ok(url: str) -> dict:
    return {"payload": {"url": url, "screenshot_path": "", "extracted_meta": {}, "pre_chunks": []}}


def _fake_rag_ok(payload: dict) -> dict:
    return {
        "conclusion": {"competitor_price": "x", "risk_level": "低", "suggested_action": "y",
                       "insufficient_info": True, "sources": []},
        "receipt": {"status": "success", "ticket_id": "MOCK-TEST", "reason": None, "mock": True},
    }


# --- POST /api/task 入参校验（T-WEB 失败路径第 1 行业务行） ----------------------


@pytest.mark.parametrize(
    "bad_url",
    ["", "ftp://example.com/x", "file:///etc/passwd", "http://127.0.0.1/", "http://192.168.1.1/x", "not-a-url"],
)
def test_post_task_rejects_illegal_url(client, bad_url):
    resp = client.post("/api/task", json={"url": bad_url})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "URL_REJECTED"
    assert body["message"] == "请输入合法的目标 URL"  # 输入框旁提示文案
    assert fastapi_app.state.registry._tasks == {}  # 不创建任务


def test_post_task_async_returns_task_id(client):
    """A1：合法 URL 立即返回 task_id，不经 HTTP 长等待（后台异步执行）。"""
    fastapi_app.state.acq_runner = _fake_acq_ok
    fastapi_app.state.rag_runner = _fake_rag_ok
    resp = client.post("/api/task", json={"url": "https://quote.eastmoney.com/sz000858.html"})
    assert resp.status_code == 201
    task_id = resp.json()["task_id"]
    assert task_id
    snapshot = fastapi_app.state.registry.snapshot(task_id)
    assert snapshot is not None and snapshot["url"].startswith("https://")


def test_snapshot_unknown_task_404(client):
    resp = client.get("/api/task/does-not-exist")
    assert resp.status_code == 404


def test_regenerate_guards(client):
    """未知任务 404；尚无 Payload 的任务 409（架构 §1.1 regenerate 端点契约）。"""
    assert client.post("/api/task/nope/regenerate").status_code == 404
    fastapi_app.state.acq_runner = lambda url: {"error": {"code": "FETCH_TIMEOUT", "message": "t", "retryable": True}}
    resp = client.post("/api/task", json={"url": "https://quote.eastmoney.com/sz000858.html"})
    task_id = resp.json()["task_id"]
    import time
    for _ in range(100):  # 等后台任务落定（失败终态，无 Payload）
        snap = fastapi_app.state.registry.snapshot(task_id)
        if snap and snap["status"] == "Error":
            break
        time.sleep(0.01)
    resp = client.post(f"/api/task/{task_id}/regenerate")
    assert resp.status_code == 409


# --- 拓扑确认（验收末行 · 审计观察项②） ------------------------------------------


def test_topology_flask_has_no_api_routes():
    rules = [rule.rule for rule in flask_app.url_map.iter_rules()]
    assert not any(rule.startswith("/api") for rule in rules), f"Flask 不得含 /api/* 路由：{rules}"


def test_topology_fastapi_owns_api_endpoints():
    paths = {route.path for route in fastapi_app.routes}
    assert "/api/task" in paths
    assert "/api/task/{task_id}/stream" in paths
    assert "/api/task/{task_id}" in paths
    assert "/api/task/{task_id}/regenerate" in paths
    assert "/api/health" in paths


# --- A8 角色视图（界面层最小实现 · 无认证安全语义） --------------------------------


def test_researcher_view_hides_step3():
    client = flask_app.test_client()
    html = client.get("/").get_data(as_text=True)
    assert 'id="step3-conclusion"' not in html  # 调研员视角 Step 3 不渲染
    assert 'id="step1-preview"' in html and 'id="step2-chunks"' in html


def test_admin_view_shows_step3_and_regenerate():
    client = flask_app.test_client()
    html = client.get("/?role=admin").get_data(as_text=True)
    assert 'id="step3-conclusion"' in html
    assert 'id="regen-btn"' in html and "重新生成" in html


# --- A5 页面侧静态断言（禁真实浏览器 · 横幅文案模板 + 工单号数据源） ----------------


def test_template_contains_a5_banner_wired_to_receipt():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "已模拟写入内部系统（工单号：" in html  # 一票否决文案模板
    assert "receipt.ticket_id" in html           # 工单号逐字取自回填回执
    assert "模拟写入失败：" in html                # SPEC FP-4 回填失败文案
    assert 'id="receipt-bar"' in html
