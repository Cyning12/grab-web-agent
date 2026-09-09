"""FastAPI 进程入口：全部 API/SSE 端点（架构 §0 拓扑钉死：Flask 仅渲染，本进程独揽数据接口）。

端点清单（架构 §1.1）：
- POST /api/task                    入参 URL -> SSRF 白名单校验 -> 注册表登记 -> 后台异步触发
                                    Supervisor -> 立即返回 {task_id}（不经 HTTP 长等待 · SPEC A1）
- GET  /api/task/{id}/stream        SSE 流：订阅即回放事件历史（断线补拉），再实时转发
                                    progress/state/chunk/conclusion/warning/error 六类事件
                                    （warning 为人决 D7 滑块覆盖层降级警告 · 架构 §1.1 D7 行）
- GET  /api/task/{id}               任务快照补拉（注册表内存态直出）
- POST /api/task/{id}/regenerate    以同一 Payload 重跑对内子图（SPEC A8 · 管理员「重新生成」）
- GET  /static/<path>               截图落盘目录静态托管（Step 1 缩略图 · SPEC A6）
- GET  /api/health                  健康检查（task_project_scaffold 冒烟断言①）

SSE 以纯 Starlette StreamingResponse 手写 text/event-stream，零新依赖（sse-starlette 不引入）。

启动：uvicorn app.api.main:app --port $FASTAPI_PORT
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.graphs.supervisor import execute_task, regenerate_task
from app.services.acquisition import UrlRejected, validate_target_url
from app.services.console.registry import TERMINAL_STATUSES, TaskRegistry

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
_SSE_HEARTBEAT_SECONDS = 15.0

app = FastAPI(title="grab_web_agent API")

# 同机双进程拓扑（PRD §2.3）：Flask 页面来源直连本进程，V1 本地运行放行全部来源（T-WEB R3 实现细节）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 任务注册表：内存态（SPEC FP-5 · 服务重启即丢，日志可查）；测试经 app.state 注入隔离实例
app.state.registry = TaskRegistry()
# 子图入口注入槽：None = 真实实现；测试注入 Mock 桩驱动联调（禁止真实浏览器/LLM/外网）
app.state.acq_runner = None
app.state.rag_runner = None
# 后台任务强引用集（防 GC 提前回收）
app.state.background_tasks = set()

_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


class TaskCreateRequest(BaseModel):
    """POST /api/task 入参。"""

    url: str


def _schedule(coro: Any) -> None:
    task = asyncio.create_task(coro)
    app.state.background_tasks.add(task)
    task.add_done_callback(app.state.background_tasks.discard)


@app.get("/api/health")
def health() -> dict:
    """健康检查冒烟端点（task_project_scaffold 验收 · 冒烟断言①）。"""
    return {"status": "ok"}


@app.post("/api/task", status_code=201)
async def create_task(body: TaskCreateRequest, request: Request):
    """异步提交：SSRF 校验 -> 登记 -> 后台触发 Supervisor -> 立即返回任务 ID（SPEC A1）。"""
    try:
        url = validate_target_url(body.url)
    except UrlRejected as exc:
        # T-WEB 失败路径第 1 行业务行：4xx + 原因，不创建任务
        return JSONResponse(
            status_code=400,
            content={
                "code": "URL_REJECTED",
                "message": "请输入合法的目标 URL",
                "reason": str(exc),
            },
        )
    registry: TaskRegistry = request.app.state.registry
    record = registry.create(url)
    _schedule(
        execute_task(
            registry,
            record.task_id,
            url,
            acq_runner=request.app.state.acq_runner,
            rag_runner=request.app.state.rag_runner,
        )
    )
    return {"task_id": record.task_id}


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _is_terminal_event(envelope: dict[str, Any]) -> bool:
    """终态判定：仅 state 落 Done/Error 时关流。

    error 事件不单独关流：_fail 先发 error 再发 state Error，消费者可能在两条事件
    之间醒来，若以 error 关流会截断紧随的 state Error；未知任务的 TASK_NOT_FOUND
    由生成器入口直接 return，不经此判定。
    """
    return (
        envelope["event"] == "state"
        and envelope["data"].get("status") in TERMINAL_STATUSES
    )


async def _event_stream(registry: TaskRegistry, task_id: str) -> AsyncIterator[str]:
    """SSE 生成器：先回放事件历史（断线补拉），再实时转发；终态事件后关闭流。"""
    record = registry.get(task_id)
    if record is None:
        # SPEC FP-5：重连未命中（服务重启内存态丢失）-> error{TASK_NOT_FOUND}
        yield _format_sse(
            "error",
            {
                "code": "TASK_NOT_FOUND",
                "message": "任务不存在或已过期（服务重启后任务状态丢失），请重新提交",
                "retryable": False,
            },
        )
        return
    subscription = registry.subscribe(task_id)
    assert subscription is not None
    replay, queue = subscription
    try:
        for envelope in replay:
            yield _format_sse(envelope["event"], envelope["data"])
        if record.is_terminal:
            return  # 订阅时已终态：回放即完整状态，关闭流
        while True:
            try:
                envelope = await asyncio.wait_for(queue.get(), timeout=_SSE_HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # 心跳注释行，防代理 idle 断连
                continue
            yield _format_sse(envelope["event"], envelope["data"])
            if _is_terminal_event(envelope):
                return
    finally:
        registry.unsubscribe(task_id, queue)


@app.get("/api/task/{task_id}/stream")
async def stream_task(task_id: str, request: Request) -> StreamingResponse:
    """SSE 端点（六类事件枚举：progress/state/chunk/conclusion/warning/error · 架构 §1.1）。

    转发与回放对事件类型透明（envelope 原样透传），warning 事件无需特判；
    终态判定仍仅 state 落 Done/Error（warning 非终态，不关流）。
    """
    registry: TaskRegistry = request.app.state.registry
    return StreamingResponse(
        _event_stream(registry, task_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/task/{task_id}")
async def get_task(task_id: str, request: Request) -> dict[str, Any]:
    """任务快照补拉（断线重连 / Step 1 渲染数据源 · 架构 §1.1 注册表）。"""
    snapshot = request.app.state.registry.snapshot(task_id)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TASK_NOT_FOUND", "message": "任务不存在或已过期"},
        )
    return snapshot


@app.post("/api/task/{task_id}/regenerate")
async def regenerate(task_id: str, request: Request) -> dict[str, str]:
    """管理员「重新生成」（SPEC A8）：同一已存 Payload 重跑对内子图，不回写旧结果。

    状态先同步翻回 RAGing 并广播（保证紧随其后的 SSE 重连可观测新一轮），
    对内子图在后台任务中执行。
    """
    registry: TaskRegistry = request.app.state.registry
    record = registry.get(task_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TASK_NOT_FOUND", "message": "任务不存在或已过期"},
        )
    if record.payload is None:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_PAYLOAD", "message": "任务尚未产出 Payload，无法重新生成"},
        )
    registry.update(task_id, status="RAGing", status_detail="重新生成", error=None)
    registry.emit(task_id, "state", {"status": "RAGing", "detail": "重新生成"})
    _schedule(regenerate_task(registry, task_id, rag_runner=request.app.state.rag_runner))
    return {"task_id": task_id, "status": "regenerating"}
