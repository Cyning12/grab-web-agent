"""Supervisor 主控图薄壳接线（架构 §1.2 · task_web_console_mvp 范围）。

职责：接单 -> 顺序驱动对外子图 -> 对内子图 -> 广播状态/进度/chunk/结论/警告/错误事件；
本身不做任何 CPU/内存密集计算（铁律二/三职责在子图内）。

两条调用路径共享同一组子图入口：
- execute_task / regenerate_task（async）：FastAPI 后台任务路径，逐步迁移状态机并经
  任务注册表广播 SSE 事件（架构 §1.5 状态机迁移触发表逐行对齐）；
- build_supervisor_graph（sync LangGraph 包装）：task_project_scaffold 冒烟契约保留
  （Mock 输入空跑 Done/100），不含事件广播，事件化编排以 execute_task 为准。

子图入口可注入（acq_runner / rag_runner），测试以 Mock 桩驱动全链联调；
默认调用两子图真实入口 build_acquisition_graph().invoke / run_internal_rag。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from app.graphs.acquisition import build_acquisition_graph
from app.graphs.internal_rag import build_internal_rag_graph, run_internal_rag
from app.services.console.registry import TaskRegistry

logger = logging.getLogger(__name__)

# 子图入口签名：同步可调用（真实子图为 LangGraph sync invoke），由 asyncio.to_thread 驱动
AcqRunner = Callable[[str], dict[str, Any]]
RagRunner = Callable[[dict[str, Any]], dict[str, Any]]


def default_acq_runner(url: str) -> dict[str, Any]:
    """对外子图真实入口（架构 §1.3 六节点链）。"""
    return build_acquisition_graph().invoke({"url": url})


def default_rag_runner(payload: dict[str, Any]) -> dict[str, Any]:
    """对内子图真实入口（架构 §1.4 四节点链 · 每次调用全新 State）。"""
    return run_internal_rag(payload)


def _dump(obj: Any) -> Any:
    """pydantic 模型 -> dict（结论/回执落注册表与 SSE data 的统一出口）。"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def _fail(registry: TaskRegistry, task_id: str, error: dict[str, Any]) -> None:
    """失败终态收敛：error 事件 + state Error（SPEC A9 不滞留中间态）。"""
    err = {
        "code": error.get("code", "SUPERVISOR_FAILED"),
        "message": error.get("message", ""),
        "retryable": bool(error.get("retryable", True)),
    }
    if error.get("user_message"):
        err["user_message"] = error["user_message"]
    registry.update(task_id, status="Error", status_detail=None, error=err)
    registry.emit(task_id, "error", err)
    registry.emit(task_id, "state", {"status": "Error", "detail": err["code"]})


def _emit_state(
    registry: TaskRegistry, task_id: str, status: str, detail: str | None = None
) -> None:
    registry.update(task_id, status=status, status_detail=detail)
    registry.emit(task_id, "state", {"status": status, "detail": detail})


def _emit_progress(registry: TaskRegistry, task_id: str, percent: int) -> None:
    registry.update(task_id, progress=percent)
    registry.emit(task_id, "progress", {"percent": percent})


async def _run_rag_and_broadcast(
    registry: TaskRegistry, task_id: str, payload: dict[str, Any], rag_runner: RagRunner
) -> None:
    """驱动对内子图并广播 conclusion/progress 100/state Done（或失败终态）。

    RAGing→Done：回填回调成功或失败均落 Done，失败以 detail="回填失败" 区分（SPEC FP-4）。
    """
    rag_state = await asyncio.to_thread(rag_runner, payload)
    if rag_state.get("error"):
        _fail(registry, task_id, rag_state["error"])
        return
    conclusion = _dump(rag_state.get("conclusion") or {})
    receipt = _dump(rag_state.get("receipt") or {})
    record = registry.get(task_id)
    if record is not None and record.warning:
        # 人决 D7 结论标注：warning 为 Conclusion Schema 外附加字段（pydantic 默认
        # 忽略 extra，对内 app/services/rag/schemas.py 不动），供页面侧人工复核提示
        conclusion["warning"] = record.warning
    registry.update(task_id, conclusion=conclusion, receipt=receipt)
    registry.emit(task_id, "conclusion", {"conclusion": conclusion, "receipt": receipt})
    _emit_progress(registry, task_id, 100)
    detail = "回填失败" if receipt.get("status") == "failed" else None
    _emit_state(registry, task_id, "Done", detail)


async def execute_task(
    registry: TaskRegistry,
    task_id: str,
    url: str,
    acq_runner: AcqRunner | None = None,
    rag_runner: RagRunner | None = None,
) -> None:
    """主路径编排（架构 §3.1 时序 #2–#7 · 失败分支 §3.2 全行）。

    状态机：Pending（注册时已发）→ Fetching(10%) → Parsing(50%，逐条 chunk)
    → RAGing → Done(100%)；任一子图失败 → error + Error 终态。
    """
    acq_runner = acq_runner or default_acq_runner
    rag_runner = rag_runner or default_rag_runner
    try:
        # Pending → Fetching（调起对外子图）
        _emit_state(registry, task_id, "Fetching")
        _emit_progress(registry, task_id, 10)

        acq_state = await asyncio.to_thread(acq_runner, url)
        if acq_state.get("error"):
            _fail(registry, task_id, acq_state["error"])
            return

        # 人决 D7 警告透传（滑块覆盖层检出但渲染探针通过）：注册表留痕 +
        # 第六类 SSE 事件 warning（架构 §1.1 D7 行）；不阻断管道，结论落盘时再标注
        warning = acq_state.get("warning")
        if warning:
            registry.update(task_id, warning=warning)
            registry.emit(task_id, "warning", warning)

        # Fetching → Parsing（n6 Payload 校验通过）
        payload: dict[str, Any] = acq_state.get("payload") or {}
        registry.update(task_id, payload=payload)
        _emit_state(registry, task_id, "Parsing")
        _emit_progress(registry, task_id, 50)

        # Parsing 期间逐条推 chunk（Step 2 实时展示 · 架构 §1.1 chunk 事件字段表）
        for index, chunk in enumerate(payload.get("pre_chunks", [])):
            registry.emit(
                task_id,
                "chunk",
                {
                    "index": index,
                    "title": chunk.get("title", ""),
                    "text": chunk.get("text", ""),
                    "section_path": chunk.get("section_path", ""),
                    "xpath": chunk.get("xpath", ""),
                    "token_count": chunk.get("token_count", 0),
                },
            )

        # Parsing → RAGing（Payload 转交对内；进度保持 50，仅发 state）
        _emit_state(registry, task_id, "RAGing")
        await _run_rag_and_broadcast(registry, task_id, payload, rag_runner)
    except Exception as exc:  # 编排层未预期异常：落 Error 终态，不留僵尸任务
        logger.exception("Supervisor 编排异常 task_id=%s", task_id)
        _fail(registry, task_id, {"code": "SUPERVISOR_FAILED", "message": str(exc), "retryable": True})


async def regenerate_task(
    registry: TaskRegistry,
    task_id: str,
    rag_runner: RagRunner | None = None,
) -> None:
    """管理员「重新生成」：以同一已存 Payload 重跑对内子图（SPEC A8）。

    新结论/回执整体替换注册表旧值（不回写旧结果）；调用方须先把状态翻回 RAGing
    并广播 state 事件（端点同步完成，保证 SSE 重连可观测新一轮）。
    """
    rag_runner = rag_runner or default_rag_runner
    record = registry.get(task_id)
    if record is None or record.payload is None:
        logger.warning("regenerate 命中无 Payload 任务 task_id=%s（已忽略）", task_id)
        return
    try:
        await _run_rag_and_broadcast(registry, task_id, record.payload, rag_runner)
    except Exception as exc:
        logger.exception("重新生成编排异常 task_id=%s", task_id)
        _fail(registry, task_id, {"code": "SUPERVISOR_FAILED", "message": str(exc), "retryable": True})


# --- LangGraph 同步包装（scaffold 冒烟契约保留 · 无事件广播） ---------------------


class SupervisorState(TypedDict, total=False):
    """主控图 State（对齐架构 §1.2 输入 {task_id, url} 与输出 {status, progress, ...}）。"""

    task_id: str
    url: str
    status: str
    progress: int
    payload: dict[str, Any]
    conclusion: dict[str, Any]
    receipt: dict[str, Any]
    error: dict[str, Any]


def run_acquisition(state: SupervisorState) -> dict[str, Any]:
    """调对外子图并转 RAGing；事件广播路径见 execute_task。"""
    result = default_acq_runner(state.get("url", ""))
    return {"payload": result.get("payload", {}), "status": "RAGing", "progress": 50}


def run_rag(state: SupervisorState) -> dict[str, Any]:
    """调对内子图并推终态 Done；事件广播路径见 execute_task。"""
    result = default_rag_runner(state.get("payload", {}))
    return {
        "conclusion": _dump(result.get("conclusion", {})),
        "receipt": _dump(result.get("receipt", {})),
        "status": "Done",
        "progress": 100,
    }


def build_supervisor_graph():
    """编译 Supervisor 主控图（入口 -> 对外子图 -> 对内子图 -> 终态）。"""
    graph = StateGraph(SupervisorState)
    graph.add_node("acquisition", run_acquisition)
    graph.add_node("internal_rag", run_rag)
    graph.add_edge(START, "acquisition")
    graph.add_edge("acquisition", "internal_rag")
    graph.add_edge("internal_rag", END)
    return graph.compile()
