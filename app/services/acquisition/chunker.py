"""n4 chunk_sections：按 H1/H2 标题语义切分为 512–1024 tokens 的 pre_chunks。

- token 计数为确定性近似估计（CJK 字符 ≈ 1 token，非 CJK 连续段按 4 字符 ≈ 1 token），
  与 Embedding 模型 bge-m3 的真实分词存在口径偏差（task residual_risks ① 已留档）；
  切分与契约断言共用同一估计函数，保证离线可测、结果可复现；
- 语义单元 = 正文块（block），标题块更新 section 栈并作为该 section 的文本开头；
- 打包策略：贪婪装入 ≤ max；超长块先按句边界切片（单句超长按字符硬切兜底）；
  尾部不足 min 的残余向前一 chunk 回挪/借句再平衡，仍凑不齐则并入（≤ max）或丢弃留痕；
- 产出不变式：每条 chunk token_count ∈ [512, 1024] 且 section_path / xpath 非空；
  整页可提取文本不足 512 tokens 时产出空 pre_chunks（走 SPEC FP-3 空 chunks 流转，
  由对内产出「信息不足」结论，不降级多模态——铁律一）。
"""

import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

MIN_TOKENS = 512
MAX_TOKENS = 1024
_FALLBACK_SECTION = "页面正文"  # 首个标题前的正文归属（保证 section_path 非空）
_HEADING_LEVELS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4}
_SENTENCE_SPLIT = re.compile(r"(?<=[。！？；!?;.\n])")
_CJK_PATTERN = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef]"
)


def estimate_tokens(text: str) -> int:
    """确定性 token 近似估计：CJK 字符 1 token，其余连续段每 4 字符 1 token。"""
    if not text:
        return 0
    cjk = len(_CJK_PATTERN.findall(text))
    rest = _CJK_PATTERN.sub(" ", text)
    rest_tokens = sum(max(1, math.ceil(len(run) / 4)) for run in rest.split())
    return cjk + rest_tokens


def _split_sentences(text: str) -> list[str]:
    return [seg for seg in _SENTENCE_SPLIT.split(text) if seg.strip()]


def _hard_cut_head(text: str, budget_tokens: int) -> tuple[str, str]:
    """按字符硬切出 ≤ budget_tokens 的头部（无句边界时的兜底）。"""
    if budget_tokens <= 0 or not text:
        return "", text
    head = text
    while head and estimate_tokens(head) > budget_tokens:
        head = head[: max(1, len(head) * budget_tokens // estimate_tokens(head) - 1)]
    return head, text[len(head):]


def _take_prefix(text: str, budget_tokens: int) -> tuple[str, str]:
    """按句边界取 ≤ budget_tokens 的前缀；单句超预算时硬切兜底。返回 (前缀, 剩余)。"""
    sentences = _split_sentences(text)
    taken: list[str] = []
    used = 0
    for idx, sentence in enumerate(sentences):
        s_tokens = estimate_tokens(sentence)
        if used + s_tokens > budget_tokens:
            if not taken:  # 首句即超预算：硬切该句
                head, tail = _hard_cut_head(sentence, budget_tokens)
                return head, tail + "".join(sentences[idx + 1 :])
            return "".join(taken), "".join(sentences[idx:])
        taken.append(sentence)
        used += s_tokens
    return "".join(taken), ""


def _hard_cut_tail(text: str, budget_tokens: int) -> tuple[str, str]:
    """按字符硬切出 ≤ budget_tokens 的尾部（无句边界时的兜底）。返回 (头部, 尾部)。"""
    if budget_tokens <= 0 or not text:
        return text, ""
    tail = text
    while tail and estimate_tokens(tail) > budget_tokens:
        tail = tail[len(tail) - max(1, len(tail) * budget_tokens // estimate_tokens(tail) - 1) :]
    return text[: len(text) - len(tail)], tail


def _take_suffix(text: str, budget_tokens: int) -> tuple[str, str]:
    """按句边界从尾部取 ≤ budget_tokens 的后缀。返回 (头部, 后缀)。"""
    sentences = _split_sentences(text)
    taken: list[str] = []
    used = 0
    for idx in range(len(sentences) - 1, -1, -1):
        s_tokens = estimate_tokens(sentences[idx])
        if used + s_tokens > budget_tokens:
            if not taken:
                head, tail = _hard_cut_tail(sentences[idx], budget_tokens)
                return "".join(sentences[:idx]) + head, tail
            return "".join(sentences[: idx + 1]), "".join(reversed(taken))
        taken.append(sentences[idx])
        used += s_tokens
    return "", "".join(reversed(taken))


def _split_text_to_fit(text: str, max_tokens: int) -> list[str]:
    """把超长文本切成 ≤ max_tokens 的片段（句边界优先，单句超长硬切）。"""
    pieces: list[str] = []
    rest = text
    while estimate_tokens(rest) > max_tokens:
        head, rest = _take_prefix(rest, max_tokens)
        if not head:  # 理论不可达（_take_prefix 有硬切兜底），防御性退出
            pieces.append(rest)
            return pieces
        pieces.append(head)
    if rest.strip():
        pieces.append(rest)
    return pieces


def _build_units(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把 n3 blocks 组织为带 section 元数据的语义单元（H1/H2 更新标题路径栈）。"""
    units: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    for block in blocks:
        tag = block.get("tag", "")
        text = (block.get("text") or "").strip()
        if not text:
            continue
        level = _HEADING_LEVELS.get(tag)
        if level:
            stack = [(lvl, title) for lvl, title in stack if lvl < level]
            stack.append((level, text))
        section_path = " / ".join(title for _, title in stack) or _FALLBACK_SECTION
        section_title = stack[-1][1] if stack else _FALLBACK_SECTION
        units.append(
            {
                "text": text,
                "xpath": block.get("xpath") or "",
                "section_title": section_title,
                "section_path": section_path,
            }
        )
    return units


def _expand_oversized(units: list[dict[str, Any]], max_tokens: int) -> list[dict[str, Any]]:
    """超长单元预切片（元数据随片段继承，溯源 xpath/section_path 不变）。"""
    expanded: list[dict[str, Any]] = []
    for unit in units:
        if estimate_tokens(unit["text"]) <= max_tokens:
            expanded.append(unit)
            continue
        for piece in _split_text_to_fit(unit["text"], max_tokens):
            expanded.append({**unit, "text": piece})
    return expanded


def _units_tokens(units: list[dict[str, Any]]) -> int:
    return estimate_tokens("\n".join(unit["text"] for unit in units))


def _emit_chunk(units: list[dict[str, Any]]) -> dict[str, Any]:
    """units -> pre_chunk（title/section_path/xpath 锚定首单元，token_count 重算复核）。"""
    text = "\n".join(unit["text"] for unit in units)
    return {
        "title": units[0]["section_title"],
        "text": text,
        "section_path": units[0]["section_path"],
        "xpath": units[0]["xpath"],
        "token_count": estimate_tokens(text),
    }


def _rebalance_tail(
    chunk_units: list[list[dict[str, Any]]], min_tokens: int, max_tokens: int
) -> None:
    """末 chunk 不足 min 时向前借单元/借句再平衡；凑不齐则并入（≤ max）或丢弃留痕。"""
    while len(chunk_units) >= 2 and _units_tokens(chunk_units[-1]) < min_tokens:
        prev, last = chunk_units[-2], chunk_units[-1]
        need = min_tokens - _units_tokens(last)
        prev_total = _units_tokens(prev)
        donor_tokens = estimate_tokens(prev[-1]["text"])
        if len(prev) > 1 and prev_total - donor_tokens >= min_tokens:
            last.insert(0, prev.pop())  # 整单元回挪
            continue
        budget = min(need, prev_total - min_tokens)
        if budget > 0:
            head, tail = _take_suffix(prev[-1]["text"], budget)
            if tail:
                donor = prev[-1]
                prev[-1] = {**donor, "text": head}
                last.insert(0, {**donor, "text": tail})
                continue
        if prev_total + _units_tokens(last) <= max_tokens:
            prev.extend(last)  # 并入前一 chunk
            chunk_units.pop()
            continue
        logger.warning(
            "丢弃尾部 %d tokens 残余（并入将超 %d tokens，见 task 实现备忘）",
            _units_tokens(last),
            max_tokens,
        )
        chunk_units.pop()


def chunk_blocks(
    blocks: list[dict[str, Any]],
    min_tokens: int = MIN_TOKENS,
    max_tokens: int = MAX_TOKENS,
) -> list[dict[str, Any]]:
    """H1/H2 语义切分主入口；保证产出 chunk token_count ∈ [min_tokens, max_tokens]。"""
    units = _expand_oversized(_build_units(blocks), max_tokens)
    chunk_units: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    cur_tokens = 0

    def flush() -> None:
        nonlocal cur, cur_tokens
        if cur:
            chunk_units.append(cur)
            cur, cur_tokens = [], 0

    for unit in units:
        u_tokens = estimate_tokens(unit["text"])
        if cur_tokens + u_tokens <= max_tokens:
            cur.append(unit)
            cur_tokens += u_tokens
            continue
        if cur_tokens >= min_tokens:
            flush()
            cur, cur_tokens = [unit], u_tokens
            continue
        # cur 不足 min 且整体装入会超 max：切下 unit 前缀补足 cur 后先落一块
        prefix, rest = _take_prefix(unit["text"], max_tokens - cur_tokens)
        if prefix:
            cur.append({**unit, "text": prefix})
            flush()
        if rest.strip():
            cur, cur_tokens = [{**unit, "text": rest}], estimate_tokens(rest)

    if cur:
        if cur_tokens >= min_tokens:
            flush()
        elif chunk_units:
            chunk_units.append(cur)
            _rebalance_tail(chunk_units, min_tokens, max_tokens)
        else:
            logger.info(
                "整页可提取文本 %d tokens < %d，产出空 pre_chunks（SPEC FP-3 空流转）",
                cur_tokens,
                min_tokens,
            )

    chunks = [_emit_chunk(units_) for units_ in chunk_units]
    logger.info("chunk 完成 blocks=%d chunks=%d", len(blocks), len(chunks))
    return chunks
