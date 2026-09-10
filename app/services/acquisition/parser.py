"""n3 parse_dom：BeautifulSoup + CSS 语义推断的代码级解析（铁律一唯一内容提取路径）。

- 提取标题 / Meta / 价格 / 正文块，输出对齐架构 §1.3 n3：
  extracted_meta = {title, meta, price, http_status}，blocks = [{tag, text, xpath, bbox}]；
- XPath 由 BS4 节点层级推导（同标签兄弟 1 基索引），与 browser._BBOX_MAP_JS 逐字对齐，
  据此为提取节点绑定 BoundingRect；
- 解析为空时不降级多模态（铁律一）：以空 blocks 继续流转，由对内产出「信息不足」结论。
"""

import logging
import re
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADING_TAGS = {"h1", "h2", "h3", "h4"}
_BLOCK_TAGS = _HEADING_TAGS | {"p", "li", "tr"}
_LEAF_DIV_MIN_CHARS = 10  # 叶子 div 视为正文块的最短文本长度（东财类 div 排版兜底）
_PRICE_SELECTOR = '[class*="price" i], [id*="price" i]'
_PRICE_PATTERN = re.compile(r"[¥￥]\s?\d[\d,]*(?:\.\d{1,2})?")
_PRICE_FALLBACK_PATTERN = re.compile(r"\d+\.\d{2}")
_META_NAME_KEYS = ("description", "keywords", "author")


def element_xpath(el: Any) -> str:
    """由 BS4 节点推导 XPath（/html/body/div[1]/p[2] 形式，与浏览器侧采集规则一致）。"""
    parts: list[str] = []
    node = el
    while node is not None and getattr(node, "name", None):
        name = node.name.lower()
        if name == "[document]":
            break
        index = 1
        sib = node.find_previous_sibling(name)
        while sib is not None:
            index += 1
            sib = sib.find_previous_sibling(name)
        parts.append(f"{name}[{index}]")
        node = node.parent
    return "/" + "/".join(reversed(parts)) if parts else "/"


def _lookup_bbox(xpath: str, bbox_map: dict[str, list[int]]) -> dict[str, int] | None:
    rect = bbox_map.get(xpath)
    if not rect or len(rect) != 4:
        return None
    return {"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]}


def _block_text(el: Any) -> str:
    return " ".join(el.stripped_strings)


def _is_leaf_text_div(el: Any) -> bool:
    """div 兜底：仅当不含任何块级子元素且文本够长时视为正文块（避免嵌套重复）。"""
    if el.name != "div":
        return False
    for child in el.find_all(True):
        if child.name in _BLOCK_TAGS or child.name in {"div", "table", "section", "article"}:
            return False
    return len(_block_text(el)) >= _LEAF_DIV_MIN_CHARS


def _extract_price(soup: BeautifulSoup, title: str = "") -> str:
    """CSS 语义推断价格：class/id 含 price 且文本含数字者优先，其次标题正则，最后正文正则。

    - 选择器命中但文本纯标签（腾讯 gu.qq.com 的 span#price 文本为「分价」标签而非数值）时
      跳过继续找，避免误提取（task_switch_target_gu_qq 最小适配点）；
    - 标题兜底：腾讯页标题带实时价（「五 粮 液 71.16 -0.49(-0.68%)_财经频道_腾讯网」），
      先于正文正则（正文首个两位小数可能是大盘指数而非个股价）。
    """
    for el in soup.select(_PRICE_SELECTOR):
        text = _block_text(el)
        if text and any(ch.isdigit() for ch in text):
            return text[:50]
    for source in (title, soup.get_text(" ", strip=True)):
        if not source:
            continue
        match = _PRICE_PATTERN.search(source) or _PRICE_FALLBACK_PATTERN.search(source)
        if match:
            return match.group(0)
    return ""


def _extract_meta(soup: BeautifulSoup) -> dict[str, str]:
    meta: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").lower()
        content = tag.get("content")
        if content and any(key in name for key in _META_NAME_KEYS):
            meta[name] = content
    return meta


def parse_page(
    raw_dom: str,
    http_status: int = 0,
    bbox_map: dict[str, list[int]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """解析渲染后 DOM。返回 (extracted_meta, blocks)；空正文 -> blocks=[]（不降级多模态）。"""
    bbox_map = bbox_map or {}
    soup = BeautifulSoup(raw_dom or "", "html.parser")
    for noisy in soup(["script", "style", "noscript", "template"]):
        noisy.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        title = _block_text(h1) if h1 else ""

    extracted_meta = {
        "title": title,
        "meta": _extract_meta(soup),
        "price": _extract_price(soup, title),
        "http_status": http_status,
    }

    blocks: list[dict[str, Any]] = []
    prev_text = ""  # 仅去相邻重复（导航/模板噪声），不同小节的相同段落属合法内容
    body = soup.body or soup
    for el in body.find_all(list(_BLOCK_TAGS) + ["div"]):
        if el.name == "div" and not _is_leaf_text_div(el):
            continue
        text = _block_text(el)
        if not text or text == prev_text:
            continue
        prev_text = text
        xpath = element_xpath(el)
        blocks.append(
            {
                "tag": el.name.lower(),
                "text": text,
                "xpath": xpath,
                "bbox": _lookup_bbox(xpath, bbox_map),
            }
        )
    logger.info(
        "parse 完成 title=%r price=%r blocks=%d（空 blocks 走空 chunks 流转，铁律一无降级路径）",
        title,
        extracted_meta["price"],
        len(blocks),
    )
    return extracted_meta, blocks
