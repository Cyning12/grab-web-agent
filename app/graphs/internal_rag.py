"""对内子图骨架（Internal RAG · 瘦内耗）。

链（架构 §1.4 逐字）：receive_validate -> retrieve_topk -> generate_conclusion -> writeback_tool
节点全部 stub：真实实现属下游 task_internal_rag_subgraph（本 task 非范围）。
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class InternalRagState(TypedDict, total=False):
    """对内子图 State（字段名对齐架构 §1.4 各节点三行式输入/输出）。"""

    payload: dict[str, Any]
    payload_validated: dict[str, Any]
    context_chunks: list[dict[str, Any]]
    degraded: bool
    conclusion: dict[str, Any]
    receipt: dict[str, Any]
    error: dict[str, Any]


def receive_validate(state: InternalRagState) -> dict[str, Any]:
    """m1 stub：Payload Schema 校验属 T-RAG 范围，骨架仅透传 payload（禁重算 Embedding）。"""
    return {"payload_validated": state.get("payload", {})}


def retrieve_topk(state: InternalRagState) -> dict[str, Any]:
    """m2 stub：FAISS Top-K 检索属 T-RAG 范围，骨架返回空 context。"""
    return {"context_chunks": [], "degraded": False}


def generate_conclusion(state: InternalRagState) -> dict[str, Any]:
    """m3 stub：with_structured_output 结论生成属 T-RAG 范围，骨架返回占位结论。"""
    return {
        "conclusion": {
            "competitor_price": "",
            "risk_level": "低",
            "suggested_action": "",
            "insufficient_info": True,
            "sources": [],
        }
    }


def writeback_tool(state: InternalRagState) -> dict[str, Any]:
    """m4 stub（Tool Node）：模拟内部系统回填桩属 T-RAG 范围，骨架返回占位回执。"""
    return {"receipt": {"status": "success", "ticket_id": None, "reason": None, "mock": True}}


def build_internal_rag_graph():
    """编译对内子图骨架（四节点链式串联，全部 stub）。"""
    graph = StateGraph(InternalRagState)
    graph.add_node("receive_validate", receive_validate)
    graph.add_node("retrieve_topk", retrieve_topk)
    graph.add_node("generate_conclusion", generate_conclusion)
    graph.add_node("writeback_tool", writeback_tool)
    graph.add_edge(START, "receive_validate")
    graph.add_edge("receive_validate", "retrieve_topk")
    graph.add_edge("retrieve_topk", "generate_conclusion")
    graph.add_edge("generate_conclusion", "writeback_tool")
    graph.add_edge("writeback_tool", END)
    return graph.compile()
