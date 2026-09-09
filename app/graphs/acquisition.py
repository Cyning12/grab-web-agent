"""对外子图（Web Acquisition · 胖采集）—— 架构 §1.3 六节点实现。

链（架构 §1.3 逐字）：validate_url -> fetch_page -> parse_dom -> chunk_sections -> embed_chunks -> emit_payload

- 每节点三行式输入/输出与 §1.3 逐项对齐；实现细节下沉 app/services/acquisition/，
  本层只做编排、异常归一（error dict + 下游节点短路）与状态钩子广播；
- 铁律一：parse_dom 为唯一内容提取路径，解析为空以空 pre_chunks 流转，
  全图无任何多模态/视觉模型调用；截图仅落盘留痕（SPEC A6）；
- 铁律二：Embedding 在 n5 预计算随 Payload 转交，对内子图禁止重算；
- 可注入性：build_acquisition_graph(fetcher=..., embedder=...) 供测试注入桩，
  默认取 PlaywrightFetcher / ChunkEmbedder（Supervisor 无参调用即真实路径）。
"""

import logging
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.acquisition import (
    AcquisitionError,
    AntiBotDetected,
    ChunkEmbedder,
    FetchResult,
    PlaywrightFetcher,
    assert_payload,
    build_payload,
    chunk_blocks,
    make_error,
    parse_page,
    validate_target_url,
)

logger = logging.getLogger(__name__)

# --- 状态钩子（Supervisor/SSE 消费 · task 范围「状态上报钩子」行） ---
# 事件形态：{"event": "state_transition", "from": ..., "to": ..., "progress"?: int, "error"?: {...}}
StatusHook = Callable[[dict[str, Any]], None]
_STATUS_HOOKS: list[StatusHook] = []


def register_status_hook(hook: StatusHook) -> None:
    """注册状态迁移观察者（Supervisor 层订阅入口；可重复注册，广播为同步调用）。"""
    _STATUS_HOOKS.append(hook)


def clear_status_hooks() -> None:
    """清空观察者（测试隔离用）。"""
    _STATUS_HOOKS.clear()


def _emit_transition(event: dict[str, Any]) -> None:
    for hook in list(_STATUS_HOOKS):
        try:
            hook(event)
        except Exception:  # 观察者异常不得阻断管道
            logger.exception("状态钩子执行异常（已忽略）")


class AcquisitionState(TypedDict, total=False):
    """对外子图 State（字段名对齐架构 §1.3 各节点三行式输入/输出）。"""

    url: str
    url_validated: str
    raw_dom: str
    http_status: int
    screenshot_path: str
    anti_bot_flag: bool
    bbox_map: dict[str, list[int]]  # n2 -> n3：xpath -> BoundingRect（§1.3 n2 坐标绑定来源）
    extracted_meta: dict[str, Any]
    blocks: list[dict[str, Any]]
    pre_chunks: list[dict[str, Any]]
    payload: dict[str, Any]
    warning: dict[str, Any]  # D7：滑块覆盖层降级警告（code=PAGE_CAPTCHA_OVERLAY）
    error: dict[str, Any]


def _has_error(state: AcquisitionState) -> bool:
    return bool(state.get("error"))


def make_nodes(fetcher: Any | None = None, embedder: Any | None = None) -> dict[str, Any]:
    """构造六节点（fetcher/embedder 可注入桩；None 时惰性取真实实现）。"""

    def _get_fetcher() -> Any:
        return fetcher if fetcher is not None else PlaywrightFetcher()

    def _get_embedder() -> Any:
        return embedder if embedder is not None else ChunkEmbedder()

    def validate_url(state: AcquisitionState) -> dict[str, Any]:
        """n1：协议白名单 + 内网段拒绝；违例 error{URL_REJECTED} 终止管道。"""
        try:
            return {"url_validated": validate_target_url(state.get("url", ""))}
        except AcquisitionError as exc:
            logger.warning("n1 拒绝 url=%r code=%s", state.get("url", ""), exc.code)
            _emit_transition({"event": "state_transition", "from": "Pending", "to": "Error"})
            return {"error": make_error(exc, "validate_url")}

    def fetch_page(state: AcquisitionState) -> dict[str, Any]:
        """n2：Playwright 渲染抓取 + CDP Turbo + 反爬检测 + 截图落盘 + bbox 采集。"""
        if _has_error(state):
            return {}
        url = state.get("url_validated", "")
        try:
            result: FetchResult = _get_fetcher().fetch(url)
        except AcquisitionError as exc:
            logger.warning("n2 失败 url=%s code=%s", url, exc.code)
            _emit_transition({"event": "state_transition", "from": "Fetching", "to": "Error"})
            return {"error": make_error(exc, "fetch_page")}
        if result.anti_bot_flag:
            exc = AntiBotDetected(f"目标站点拒绝访问（反爬拦截）：{url}", url=url)
            logger.warning("n2 反爬拦截 url=%s http_status=%d", url, result.http_status)
            _emit_transition({"event": "state_transition", "from": "Fetching", "to": "Error"})
            return {
                "error": make_error(exc, "fetch_page"),
                "screenshot_path": result.screenshot_path,  # 反爬截图留痕（SPEC FP-2）
                "http_status": result.http_status,
            }
        out: dict[str, Any] = {
            "raw_dom": result.raw_dom,
            "http_status": result.http_status,
            "screenshot_path": result.screenshot_path,
            "anti_bot_flag": result.anti_bot_flag,
            "bbox_map": result.bbox_map,
        }
        if getattr(result, "slider_overlay_flag", False):
            # 人决 D7：滑块覆盖层检出但渲染探针通过 -> 警告但继续解析（不主动绕过验证）；
            # warning 随 State 透传 Supervisor，由编排层发第六类 SSE 事件 + 结论标注
            out["warning"] = {
                "code": "PAGE_CAPTCHA_OVERLAY",
                "message": "页面含验证覆盖层，结果已人工可复核",
                "node": "fetch_page",
            }
            logger.warning("n2 验证覆盖层降级警告 url=%s", url)
        return out

    def parse_dom(state: AcquisitionState) -> dict[str, Any]:
        """n3：BS4 + CSS 语义推断；空解析不降级多模态，以空 blocks 继续流转。"""
        if _has_error(state):
            return {}
        extracted_meta, blocks = parse_page(
            state.get("raw_dom", ""),
            http_status=state.get("http_status", 0),
            bbox_map=state.get("bbox_map") or {},
        )
        return {"extracted_meta": extracted_meta, "blocks": blocks}

    def chunk_sections(state: AcquisitionState) -> dict[str, Any]:
        """n4：H1/H2 语义切分，每块 512–1024 tokens；空 blocks -> 空 pre_chunks。"""
        if _has_error(state):
            return {}
        return {"pre_chunks": chunk_blocks(state.get("blocks", []))}

    def embed_chunks(state: AcquisitionState) -> dict[str, Any]:
        """n5：SiliconFlow 批量向量化（就地补 embedding 字段）；失败 error{EMBED_FAILED}。"""
        if _has_error(state):
            return {}
        pre_chunks = state.get("pre_chunks", [])
        if not pre_chunks:
            return {}  # 空 chunks 路径不调 Embedding（SPEC FP-3）
        try:
            vectors = _get_embedder().embed([chunk["text"] for chunk in pre_chunks])
        except AcquisitionError as exc:
            logger.warning("n5 失败 code=%s", exc.code)
            _emit_transition({"event": "state_transition", "from": "Parsing", "to": "Error"})
            return {"error": make_error(exc, "embed_chunks")}
        for chunk, vector in zip(pre_chunks, vectors):
            chunk["embedding"] = vector
        return {"pre_chunks": pre_chunks}

    def emit_payload(state: AcquisitionState) -> dict[str, Any]:
        """n6：组装 PRD §6.2 标准 Payload 并按 §1.5 校验；发 Fetching->Parsing 迁移事件。"""
        if _has_error(state):
            return {}
        try:
            payload = assert_payload(
                build_payload(
                    url=state.get("url_validated") or state.get("url", ""),
                    screenshot_path=state.get("screenshot_path", ""),
                    extracted_meta=state.get("extracted_meta", {}),
                    pre_chunks=state.get("pre_chunks", []),
                )
            )
        except AcquisitionError as exc:
            _emit_transition({"event": "state_transition", "from": "Parsing", "to": "Error"})
            return {"error": make_error(exc, "emit_payload")}
        _emit_transition(
            {"event": "state_transition", "from": "Fetching", "to": "Parsing", "progress": 50}
        )
        return {"payload": payload}

    return {
        "validate_url": validate_url,
        "fetch_page": fetch_page,
        "parse_dom": parse_dom,
        "chunk_sections": chunk_sections,
        "embed_chunks": embed_chunks,
        "emit_payload": emit_payload,
    }


def build_acquisition_graph(fetcher: Any | None = None, embedder: Any | None = None):
    """编译对外子图（六节点链式串联；fetcher/embedder 可注入，默认真实实现）。"""
    nodes = make_nodes(fetcher=fetcher, embedder=embedder)
    graph = StateGraph(AcquisitionState)
    graph.add_node("validate_url", nodes["validate_url"])
    graph.add_node("fetch_page", nodes["fetch_page"])
    graph.add_node("parse_dom", nodes["parse_dom"])
    graph.add_node("chunk_sections", nodes["chunk_sections"])
    graph.add_node("embed_chunks", nodes["embed_chunks"])
    graph.add_node("emit_payload", nodes["emit_payload"])
    graph.add_edge(START, "validate_url")
    graph.add_edge("validate_url", "fetch_page")
    graph.add_edge("fetch_page", "parse_dom")
    graph.add_edge("parse_dom", "chunk_sections")
    graph.add_edge("chunk_sections", "embed_chunks")
    graph.add_edge("embed_chunks", "emit_payload")
    graph.add_edge("emit_payload", END)
    return graph.compile()
