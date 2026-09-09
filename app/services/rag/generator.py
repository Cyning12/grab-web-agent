"""结论生成（m3）：with_structured_output 等效实现。

仓依赖未引入 langchain-openai，故以 openai 兼容客户端（SiliconFlow · D2/D5）
response_format=json_object + Pydantic 强校验实现 with_structured_output 同等语义：
强制输出符合 Conclusion Schema 的 JSON，校验失败/调用失败按失败路径有限重试
（总尝试 ≤2 次，防重试风暴 · task R3），耗尽抛 GenerateFailedError → error{GENERATE_FAILED}。
空 pre_chunks 不调 LLM，直接产出「信息不足」结论（SPEC FP-3，占位文案仍过同一 Schema）。
"""

from __future__ import annotations

import json
import logging
import re

from typing import Any

from app import config
from app.services.rag.schemas import Conclusion, Payload

_logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2  # 防重试风暴：LLM 调用总尝试 ≤2 次（SPEC A7 操作化 · task R3）


class GenerateFailedError(RuntimeError):
    """LLM 生成失败或结构化输出校验失败（重试耗尽后抛出）。"""


def insufficient_conclusion() -> Conclusion:
    """「信息不足」结论（空 chunks 路径 · SPEC FP-3：三字段占位文案，过同一 Schema）。"""
    return Conclusion(
        competitor_price="信息不足",
        risk_level="低",
        suggested_action="信息不足：页面未提取到有效内容，建议更换目标 URL 或补充内部语料后重新生成",
        insufficient_info=True,
        sources=[],
    )


_SYSTEM_PROMPT = (
    "你是企业内部调研分析助手。基于给定的页面提取信息与内部知识库检索片段，"
    "输出严格的 JSON 结论，字段：competitor_price（字符串，竞品价格，未知填\"未知\"）、"
    "risk_level（枚举：低/中/高）、suggested_action（字符串，建议动作）、"
    "insufficient_info（布尔，信息不足时为 true）、sources（字符串数组，溯源片段来源，可空）。"
    "只输出 JSON，不要输出任何其他文字。"
)


def _ctx_field(chunk: Any, key: str, default: str = "") -> str:
    """context_chunks 元素兼容 dict（图 State 流转）与对象（服务层直调）两种形态。"""
    if isinstance(chunk, dict):
        return str(chunk.get(key, default))
    return str(getattr(chunk, key, default))


def _build_user_prompt(payload: Payload, context_chunks: list[Any]) -> str:
    page_part = "\n".join(f"[{c.section_path}] {c.title}: {c.text}" for c in payload.pre_chunks)
    kb_part = "\n".join(
        f"[{_ctx_field(c, 'source_path')}] {_ctx_field(c, 'text')}" for c in context_chunks
    ) or "（内部知识库无命中）"
    return (
        f"目标页面：{payload.url}\n页面标题：{payload.extracted_meta.title}\n"
        f"提取价格：{payload.extracted_meta.price}\n\n"
        f"=== 页面提取片段 ===\n{page_part}\n\n=== 内部知识库检索片段 ===\n{kb_part}"
    )


def _parse_conclusion(raw: str) -> Conclusion:
    """解析并强校验 LLM 输出（宽容截取首个 JSON 对象，再经 Pydantic Schema 校验）。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise GenerateFailedError(f"LLM 输出非 JSON：{raw[:200]!r}")
        data = json.loads(m.group(0))
    return Conclusion.model_validate(data)


class ConclusionGenerator:
    """结构化结论生成器（client 可注入 · 默认 SiliconFlow openai 兼容端点，惰性构造）。"""

    def __init__(self, client=None, model: str | None = None, max_attempts: int = MAX_ATTEMPTS) -> None:
        self._client = client
        self._model = model or config.LLM_MODEL
        self._max_attempts = max_attempts

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=config.SILICONFLOW_BASE_URL, api_key=config.SILICONFLOW_API_KEY
            )
        return self._client

    def generate(self, context_chunks: list[Any], payload: Payload) -> Conclusion:
        """生成结论。空 pre_chunks → 信息不足（不调 LLM）；否则有限重试（≤2 次总尝试）。"""
        if not payload.pre_chunks:
            _logger.info("pre_chunks 为空：产出「信息不足」结论（SPEC FP-3，不视为错误）")
            return insufficient_conclusion()

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(payload, context_chunks)},
        ]
        last_exc: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                resp = self._get_client().chat.completions.create(
                    model=self._model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                return _parse_conclusion(resp.choices[0].message.content or "")
            except Exception as exc:  # 调用失败 + Schema 校验失败同一失败路径
                last_exc = exc
                _logger.warning("结论生成第 %d/%d 次尝试失败：%s", attempt, self._max_attempts, exc)
        raise GenerateFailedError(f"结论生成重试耗尽（{self._max_attempts} 次）：{last_exc}")
