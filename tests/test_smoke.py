"""冒烟测试（task_project_scaffold 验收 · 冒烟断言三行）。

1) FastAPI GET /api/health -> 200；
2) Flask GET / -> 200 且 Flask 进程路由清单无任何 /api/* 路由（架构 §0 拓扑）；
3) supervisor 图以 Mock 输入 {task_id, url} 空跑通过（全 stub 节点串联编译执行不报错）。
"""

from fastapi.testclient import TestClient

from app.api.main import app as fastapi_app
from app.graphs.supervisor import build_supervisor_graph
from app.web.app import app as flask_app


def test_fastapi_health_200():
    client = TestClient(fastapi_app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_flask_index_200_and_no_api_routes():
    client = flask_app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    rules = [rule.rule for rule in flask_app.url_map.iter_rules()]
    assert not any(rule.startswith("/api") for rule in rules), (
        f"Flask 进程不得含任何 /api/* 路由（架构 §0 拓扑钉死），实际路由：{rules}"
    )


def test_supervisor_graph_stub_runs_with_mock_input():
    graph = build_supervisor_graph()
    result = graph.invoke({"task_id": "mock-task-000", "url": "https://example.com/mock"})
    assert result["status"] == "Done"
    assert result["progress"] == 100
