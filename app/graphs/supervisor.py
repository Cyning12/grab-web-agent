"""Supervisor 主控图骨架（架构 §1.2）。

职责：接单 -> 顺序驱动对外子图 -> 对内子图 -> 推终态；本身不做任何 CPU/内存密集计算。
骨架阶段子图调用、注册表落盘、SSE 广播均为 stub（业务实现属下游三 task 范围）。
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.graphs.acquisition import build_acquisition_graph
from app.graphs.internal_rag import build_internal_rag_graph


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
    """stub：调对外子图骨架并转 RAGing；注册表落盘与状态钩子广播属 T-ACQ/T-WEB 范围。"""
    result = build_acquisition_graph().invoke({"url": state.get("url", "")})
    return {"payload": result.get("payload", {}), "status": "RAGing", "progress": 50}


def run_internal_rag(state: SupervisorState) -> dict[str, Any]:
    """stub：调对内子图骨架并推终态 Done；回执落注册表与 SSE 广播属 T-RAG/T-WEB 范围。"""
    result = build_internal_rag_graph().invoke({"payload": state.get("payload", {})})
    return {
        "conclusion": result.get("conclusion", {}),
        "receipt": result.get("receipt", {}),
        "status": "Done",
        "progress": 100,
    }


def build_supervisor_graph():
    """编译 Supervisor 主控图骨架（入口 -> 对外子图 -> 对内子图 -> 终态）。"""
    graph = StateGraph(SupervisorState)
    graph.add_node("acquisition", run_acquisition)
    graph.add_node("internal_rag", run_internal_rag)
    graph.add_edge(START, "acquisition")
    graph.add_edge("acquisition", "internal_rag")
    graph.add_edge("internal_rag", END)
    return graph.compile()
