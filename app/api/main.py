"""FastAPI 进程入口。

骨架阶段仅提供 GET /api/health 冒烟端点；
/api/task、/api/task/{id}/stream、/static、/api/task/{id}/regenerate
属下游 task（T-WEB）范围，骨架不提前实现。

启动：uvicorn app.api.main:app --port $FASTAPI_PORT
"""

from fastapi import FastAPI

app = FastAPI(title="grab_web_agent API")


@app.get("/api/health")
def health() -> dict:
    """健康检查冒烟端点（task_project_scaffold 验收 · 冒烟断言①）。"""
    return {"status": "ok"}
