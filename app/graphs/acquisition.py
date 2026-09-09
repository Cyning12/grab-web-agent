"""对外子图骨架（Web Acquisition · 胖采集）。

链（架构 §1.3 逐字）：validate_url -> fetch_page -> parse_dom -> chunk_sections -> embed_chunks -> emit_payload
节点全部 stub：真实实现属下游 task_web_acquisition_subgraph（本 task 非范围）。
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class AcquisitionState(TypedDict, total=False):
    """对外子图 State（字段名对齐架构 §1.3 各节点三行式输入/输出）。"""

    url: str
    url_validated: str
    raw_dom: str
    http_status: int
    screenshot_path: str
    anti_bot_flag: bool
    extracted_meta: dict[str, Any]
    blocks: list[dict[str, Any]]
    pre_chunks: list[dict[str, Any]]
    payload: dict[str, Any]
    error: dict[str, Any]


def validate_url(state: AcquisitionState) -> dict[str, Any]:
    """n1 stub：SSRF 白名单校验属 T-ACQ 范围，骨架仅透传 url。"""
    return {"url_validated": state.get("url", "")}


def fetch_page(state: AcquisitionState) -> dict[str, Any]:
    """n2 stub：Playwright 抓取/截图属 T-ACQ 范围，骨架返回占位字段。"""
    return {"raw_dom": "", "http_status": 200, "screenshot_path": "", "anti_bot_flag": False}


def parse_dom(state: AcquisitionState) -> dict[str, Any]:
    """n3 stub：BS4 解析属 T-ACQ 范围，骨架返回空提取结果。"""
    return {
        "extracted_meta": {
            "title": "",
            "meta": {},
            "price": "",
            "http_status": state.get("http_status", 0),
        },
        "blocks": [],
    }


def chunk_sections(state: AcquisitionState) -> dict[str, Any]:
    """n4 stub：H1/H2 语义切分属 T-ACQ 范围，骨架返回空 pre_chunks。"""
    return {"pre_chunks": []}


def embed_chunks(state: AcquisitionState) -> dict[str, Any]:
    """n5 stub：Embedding 调用属 T-ACQ 范围，骨架不做任何向量化。"""
    return {}


def emit_payload(state: AcquisitionState) -> dict[str, Any]:
    """n6 stub：标准 Payload 组装/Schema 校验属 T-ACQ 范围，骨架返回占位 payload。"""
    return {
        "payload": {
            "url": state.get("url", ""),
            "screenshot_path": state.get("screenshot_path", ""),
            "extracted_meta": state.get("extracted_meta", {}),
            "pre_chunks": state.get("pre_chunks", []),
        }
    }


def build_acquisition_graph():
    """编译对外子图骨架（六节点链式串联，全部 stub）。"""
    graph = StateGraph(AcquisitionState)
    graph.add_node("validate_url", validate_url)
    graph.add_node("fetch_page", fetch_page)
    graph.add_node("parse_dom", parse_dom)
    graph.add_node("chunk_sections", chunk_sections)
    graph.add_node("embed_chunks", embed_chunks)
    graph.add_node("emit_payload", emit_payload)
    graph.add_edge(START, "validate_url")
    graph.add_edge("validate_url", "fetch_page")
    graph.add_edge("fetch_page", "parse_dom")
    graph.add_edge("parse_dom", "chunk_sections")
    graph.add_edge("chunk_sections", "embed_chunks")
    graph.add_edge("embed_chunks", "emit_payload")
    graph.add_edge("emit_payload", END)
    return graph.compile()
