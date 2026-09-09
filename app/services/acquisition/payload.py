"""n6 emit_payload：PRD §6.2 标准 Payload 组装 + 架构 §1.5 Schema 逐字段校验。

字段真值 = 架构 §1.5 ① 逐字段类型表（含 SPEC A2/A3 强制的 http_status /
section_path / token_count 扩展字段）；校验为仓内自实现的最小 JSON Schema
检查器（requirements 无 jsonschema 依赖，禁止改共享 requirements.txt）。
"""

import logging
from typing import Any

from app.services.acquisition.chunker import MAX_TOKENS, MIN_TOKENS
from app.services.acquisition.errors import PayloadInvalid

logger = logging.getLogger(__name__)

# 架构 §1.5 ① 的机读形态（校验规则即契约；消费方对内子图 m1 复用同一张表语义）
PAYLOAD_SCHEMA: dict[str, Any] = {
    "required": ["url", "screenshot_path", "extracted_meta", "pre_chunks"],
    "extracted_meta": {
        "required": ["title", "price", "http_status"],
        "optional": ["meta"],
    },
    "pre_chunks[]": {
        "required": ["title", "text", "embedding", "xpath", "section_path", "token_count"],
        "token_count_range": [MIN_TOKENS, MAX_TOKENS],
        "non_empty": ["xpath", "section_path"],
    },
}


def build_payload(
    url: str,
    screenshot_path: str,
    extracted_meta: dict[str, Any],
    pre_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """按 §1.5 字段表组装标准 Payload（pre_chunks 可空数组 = FP-3 正常流转）。"""
    return {
        "url": url,
        "screenshot_path": screenshot_path,
        "extracted_meta": {
            "title": str(extracted_meta.get("title", "")),
            "price": str(extracted_meta.get("price", "")),
            "meta": dict(extracted_meta.get("meta") or {}),
            "http_status": int(extracted_meta.get("http_status", 0)),
        },
        "pre_chunks": list(pre_chunks),
    }


def validate_payload(payload: dict[str, Any]) -> list[str]:
    """逐字段校验，返回违例列表（空列表 = 通过 §1.5 契约）。"""
    errors: list[str] = []
    url = payload.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        errors.append("url: 缺失或非 http/https 字符串")
    shot = payload.get("screenshot_path")
    if not isinstance(shot, str) or not shot:
        errors.append("screenshot_path: 缺失或非字符串")

    meta = payload.get("extracted_meta")
    if not isinstance(meta, dict):
        errors.append("extracted_meta: 缺失或非 object")
    else:
        if not isinstance(meta.get("title"), str):
            errors.append("extracted_meta.title: 缺失或非字符串")
        if not isinstance(meta.get("price"), str):
            errors.append("extracted_meta.price: 缺失或非字符串")
        if "meta" in meta and not isinstance(meta["meta"], dict):
            errors.append("extracted_meta.meta: 非 object")
        http_status = meta.get("http_status")
        if not isinstance(http_status, int) or isinstance(http_status, bool):
            errors.append("extracted_meta.http_status: 缺失或非 int")

    pre_chunks = payload.get("pre_chunks")
    if not isinstance(pre_chunks, list):
        errors.append("pre_chunks: 缺失或非 array")
    else:
        lo, hi = PAYLOAD_SCHEMA["pre_chunks[]"]["token_count_range"]
        for idx, chunk in enumerate(pre_chunks):
            where = f"pre_chunks[{idx}]"
            if not isinstance(chunk, dict):
                errors.append(f"{where}: 非 object")
                continue
            for field_name in PAYLOAD_SCHEMA["pre_chunks[]"]["required"]:
                if field_name not in chunk:
                    errors.append(f"{where}.{field_name}: 缺失")
            for field_name in ("title", "text"):
                if field_name in chunk and not isinstance(chunk[field_name], str):
                    errors.append(f"{where}.{field_name}: 非字符串")
            for field_name in PAYLOAD_SCHEMA["pre_chunks[]"]["non_empty"]:
                value = chunk.get(field_name)
                if not isinstance(value, str) or not value:
                    errors.append(f"{where}.{field_name}: 须为非空字符串")
            embedding = chunk.get("embedding")
            if not isinstance(embedding, list) or not all(
                isinstance(x, (int, float)) and not isinstance(x, bool) for x in embedding
            ):
                errors.append(f"{where}.embedding: 须为 float 数组（缺失 = 契约违例）")
            token_count = chunk.get("token_count")
            if (
                not isinstance(token_count, int)
                or isinstance(token_count, bool)
                or not lo <= token_count <= hi
            ):
                errors.append(f"{where}.token_count: 须为 int 且 ∈ [{lo}, {hi}]")
    return errors


def assert_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """校验通过原样返回；违例抛 PayloadInvalid（n6 出口兜底，按构造不应触发）。"""
    errors = validate_payload(payload)
    if errors:
        logger.error("payload 契约违例：%s", errors)
        raise PayloadInvalid(f"Payload 未通过 §1.5 Schema 校验：{errors}")
    logger.info(
        "payload 校验通过 chunks=%d screenshot=%s",
        len(payload["pre_chunks"]),
        payload["screenshot_path"],
    )
    return payload
